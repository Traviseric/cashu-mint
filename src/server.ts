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
 * Automatically restarts on connection errors with a 5s backoff.
 */
function startInvoiceSubscriptionLoop(
	mintService: MintServiceType,
	lightning: ILightningBackend,
	logger: FastifyBaseLogger,
): void {
	const loop = async () => {
		try {
			for await (const update of lightning.subscribeInvoices()) {
				if (update.settled && update.paymentHash) {
					await mintService.handleInvoiceSettled(update.paymentHash);
				}
			}
		} catch (err) {
			logger.error({ err }, 'Invoice subscription lost — restarting in 5s');
			setTimeout(loop, 5000);
		}
	};

	// Fire-and-forget: runs in background without blocking server startup
	loop().catch((err) => {
		logger.error({ err }, 'Invoice subscription loop failed to start');
	});
}
