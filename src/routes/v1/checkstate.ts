import type { FastifyInstance } from 'fastify';
import { CheckStateRequestSchema } from '../../utils/schemas.js';
import { ValidationError, CashuError } from '../../core/errors.js';

export async function checkstateRoutes(fastify: FastifyInstance) {
	const mintService = fastify.mintService;

	/** POST /v1/checkstate — check proof states (NUT-07) */
	fastify.post('/checkstate', async (request, reply) => {
		const parsed = CheckStateRequestSchema.safeParse(request.body);
		if (!parsed.success) {
			const err = new ValidationError(parsed.error.issues[0]?.message);
			return reply.status(400).send(err.toJSON());
		}

		try {
			const states = await mintService.checkProofState(parsed.data.Ys);
			return reply.send(states);
		} catch (err) {
			if (err instanceof CashuError) {
				return reply.status(400).send(err.toJSON());
			}
			throw err;
		}
	});
}
