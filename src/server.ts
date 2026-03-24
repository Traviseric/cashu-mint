/**
 * Main entry point — bootstraps Fastify, registers routes, starts listening.
 */

import Fastify, { type FastifyBaseLogger } from 'fastify';
import cors from '@fastify/cors';
import { registerRoutes } from './routes/index.js';
import { MintService } from './services/mint-service.js';
import { createLightningBackend } from './lightning/index.js';
import { loadConfig } from './utils/config.js';
import { MINT_VERSION } from './core/constants.js';
import type { ILightningBackend } from './lightning/interface.js';
import type { MintService as MintServiceType } from './services/mint-service.js';

// Extend Fastify instance with mint service
declare module 'fastify' {
	interface FastifyInstance {
		mintService: MintServiceType;
	}
}

async function main() {
	const config = loadConfig();

	const fastify = Fastify({
		logger: true,
	});

	// CORS — allow all origins (public mint, browser wallets need this)
	await fastify.register(cors, {
		origin: true,
		methods: ['GET', 'POST', 'OPTIONS'],
		allowedHeaders: ['Content-Type', 'Authorization'],
		credentials: false,
	});

	// Create Lightning backend
	const lightning = createLightningBackend(
		config.lnBackend,
		config.lnBackend === 'LND'
			? {
					grpcHost: config.lndGrpcHost!,
					tlsCertPath: config.lndTlsCertPath!,
					macaroonPath: config.lndMacaroonPath!,
				}
			: undefined,
	);

	// Create mint service and decorate Fastify instance
	const mintService = new MintService(config, lightning);
	fastify.decorate('mintService', mintService);

	// Initialize mint (derive keysets, upsert in DB)
	await mintService.init();

	// Start background invoice settlement detection loop (non-blocking)
	startInvoiceSubscriptionLoop(mintService, lightning, fastify.log);

	// Register routes
	await registerRoutes(fastify);

	// Graceful shutdown
	const shutdown = async (signal: string) => {
		fastify.log.info(`Received ${signal}, shutting down...`);
		await fastify.close();
		process.exit(0);
	};

	process.on('SIGINT', () => shutdown('SIGINT'));
	process.on('SIGTERM', () => shutdown('SIGTERM'));

	// Start server
	try {
		await fastify.listen({ port: config.mintListenPort, host: '0.0.0.0' });
		fastify.log.info(`Cashu mint (${MINT_VERSION}) listening on port ${config.mintListenPort}`);
		fastify.log.info(`Lightning backend: ${config.lnBackend}`);
	} catch (err) {
		fastify.log.error(err);
		process.exit(1);
	}
}

main();

/**
 * Background loop: subscribes to Lightning invoice updates and marks mint quotes PAID.
 * Automatically restarts on connection errors with exponential backoff.
 */
function startInvoiceSubscriptionLoop(
	mintService: MintServiceType,
	lightning: ILightningBackend,
	logger: FastifyBaseLogger,
): void {
	const BASE_DELAY_MS = 1000;
	const MAX_DELAY_MS = 60000;
	let attempt = 0;

	const loop = async () => {
		try {
			attempt = 0; // Reset on successful connection
			for await (const update of lightning.subscribeInvoices()) {
				if (update.settled && update.paymentHash) {
					await mintService.handleInvoiceSettled(update.paymentHash);
				}
			}
			// Stream ended cleanly — reconnect at base delay
			logger.info('Invoice subscription stream ended cleanly — reconnecting');
			setTimeout(loop, BASE_DELAY_MS);
		} catch (err) {
			const delay = Math.min(BASE_DELAY_MS * 2 ** attempt, MAX_DELAY_MS);
			logger.error({ err, attempt, retryInMs: delay }, 'Invoice subscription lost — retrying');
			attempt++;
			setTimeout(loop, delay);
		}
	};

	// Fire-and-forget: runs in background without blocking server startup
	loop().catch((err) => {
		logger.error({ err }, 'Invoice subscription loop failed to start');
	});
}
