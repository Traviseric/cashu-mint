/**
 * Main entry point — bootstraps Fastify, registers routes, starts listening.
 */

import Fastify from 'fastify';
import { registerRoutes } from './routes/index.js';
import { MintService } from './services/mint-service.js';
import { createLightningBackend } from './lightning/index.js';
import { loadConfig } from './utils/config.js';
import { MINT_VERSION, SUPPORTED_NUTS } from './core/constants.js';
import type { MintConfig } from './utils/config.js';
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
