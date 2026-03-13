import type { FastifyInstance } from 'fastify';
import { v1Routes } from './v1/index.js';
import { adminRoutes } from './admin.js';

/** Register all routes — v1 protocol + health check + admin */
export async function registerRoutes(fastify: FastifyInstance) {
	/** GET /health — basic health check */
	fastify.get('/health', async (_request, reply) => {
		return reply.send({ status: 'ok' });
	});

	/** Cashu protocol routes under /v1 */
	await fastify.register(v1Routes, { prefix: '/v1' });

	/** Admin routes (keyset rotation, internal ops) */
	await fastify.register(adminRoutes);
}
