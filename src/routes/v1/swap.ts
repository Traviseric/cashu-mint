import type { FastifyInstance } from 'fastify';
import { SwapRequestSchema } from '../../utils/schemas.js';
import { ValidationError, CashuError } from '../../core/errors.js';

export async function swapRoutes(fastify: FastifyInstance) {
	const mintService = fastify.mintService;

	/** POST /v1/swap — swap proofs for new blind signatures */
	fastify.post('/swap', async (request, reply) => {
		const parsed = SwapRequestSchema.safeParse(request.body);
		if (!parsed.success) {
			const err = new ValidationError(parsed.error.issues[0]?.message);
			return reply.status(400).send(err.toJSON());
		}

		try {
			const result = await mintService.swap(parsed.data);
			return reply.send(result);
		} catch (err) {
			if (err instanceof CashuError) {
				return reply.status(400).send(err.toJSON());
			}
			throw err;
		}
	});
}
