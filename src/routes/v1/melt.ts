import type { FastifyInstance } from 'fastify';
import { MeltQuoteRequestSchema, MeltTokensRequestSchema } from '../../utils/schemas.js';
import { ValidationError, CashuError } from '../../core/errors.js';

export async function meltRoutes(fastify: FastifyInstance) {
	const mintService = fastify.mintService;

	/** POST /v1/melt/quote/bolt11 — create a melt quote */
	fastify.post('/melt/quote/bolt11', async (request, reply) => {
		const parsed = MeltQuoteRequestSchema.safeParse(request.body);
		if (!parsed.success) {
			const err = new ValidationError(parsed.error.issues[0]?.message);
			return reply.status(400).send(err.toJSON());
		}

		try {
			const quote = await mintService.createMeltQuote(parsed.data.request, parsed.data.unit);
			return reply.send(quote);
		} catch (err) {
			if (err instanceof CashuError) {
				return reply.status(400).send(err.toJSON());
			}
			throw err;
		}
	});

	/** GET /v1/melt/quote/bolt11/:quote_id — check melt quote state */
	fastify.get<{ Params: { quote_id: string } }>('/melt/quote/bolt11/:quote_id', async (request, reply) => {
		try {
			const quote = await mintService.getMeltQuote(request.params.quote_id);
			return reply.send(quote);
		} catch (err) {
			if (err instanceof CashuError) {
				return reply.status(400).send(err.toJSON());
			}
			throw err;
		}
	});

	/** POST /v1/melt/bolt11 — melt tokens */
	fastify.post('/melt/bolt11', async (request, reply) => {
		const parsed = MeltTokensRequestSchema.safeParse(request.body);
		if (!parsed.success) {
			const err = new ValidationError(parsed.error.issues[0]?.message);
			return reply.status(400).send(err.toJSON());
		}

		try {
			const result = await mintService.meltTokens(parsed.data);
			return reply.send(result);
		} catch (err) {
			if (err instanceof CashuError) {
				return reply.status(400).send(err.toJSON());
			}
			throw err;
		}
	});
}
