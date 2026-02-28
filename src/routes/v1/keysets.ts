import type { FastifyInstance } from 'fastify';

export async function keysetsRoutes(fastify: FastifyInstance) {
	const mintService = fastify.mintService;

	/** GET /v1/keysets — all keyset metadata */
	fastify.get('/keysets', async (_request, reply) => {
		const keysets = await mintService.getKeysets();
		return reply.send(keysets);
	});
}
