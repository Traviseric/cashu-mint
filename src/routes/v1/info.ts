import type { FastifyInstance } from 'fastify';

export async function infoRoutes(fastify: FastifyInstance) {
	const mintService = fastify.mintService;

	/** GET /v1/info — mint information (NUT-06) */
	fastify.get('/info', async (_request, reply) => {
		const info = await mintService.getMintInfo();
		return reply.send(info);
	});
}
