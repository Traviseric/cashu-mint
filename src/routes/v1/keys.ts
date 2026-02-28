import type { FastifyInstance } from 'fastify';
import type { MintService } from '../../services/mint-service.js';

export async function keysRoutes(fastify: FastifyInstance) {
	const mintService = fastify.mintService;

	/** GET /v1/keys — all active keyset public keys */
	fastify.get('/keys', async (_request, reply) => {
		const keys = await mintService.getKeys();
		return reply.send(keys);
	});

	/** GET /v1/keys/:keyset_id — public keys for a specific keyset */
	fastify.get<{ Params: { keyset_id: string } }>('/keys/:keyset_id', async (request, reply) => {
		const keys = await mintService.getKeysByKeysetId(request.params.keyset_id);
		return reply.send(keys);
	});
}
