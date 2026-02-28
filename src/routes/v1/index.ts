import type { FastifyInstance } from 'fastify';
import { keysRoutes } from './keys.js';
import { keysetsRoutes } from './keysets.js';
import { swapRoutes } from './swap.js';
import { mintRoutes } from './mint.js';
import { meltRoutes } from './melt.js';
import { infoRoutes } from './info.js';
import { checkstateRoutes } from './checkstate.js';

/** Register all v1 Cashu protocol routes under /v1 prefix */
export async function v1Routes(fastify: FastifyInstance) {
	await fastify.register(keysRoutes);
	await fastify.register(keysetsRoutes);
	await fastify.register(swapRoutes);
	await fastify.register(mintRoutes);
	await fastify.register(meltRoutes);
	await fastify.register(infoRoutes);
	await fastify.register(checkstateRoutes);
}
