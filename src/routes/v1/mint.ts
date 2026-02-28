import type { FastifyInstance } from 'fastify';
import { MintQuoteRequestSchema, MintTokensRequestSchema } from '../../utils/schemas.js';
import { ValidationError, CashuError } from '../../core/errors.js';

export async function mintRoutes(fastify: FastifyInstance) {
	const mintService = fastify.mintService;

	/** POST /v1/mint/quote/bolt11 — create a mint quote */
	fastify.post('/mint/quote/bolt11', async (request, reply) => {
		const parsed = MintQuoteRequestSchema.safeParse(request.body);
		if (!parsed.success) {
			const err = new ValidationError(parsed.error.issues[0]?.message);
			return reply.status(400).send(err.toJSON());
		}

		try {
			const quote = await mintService.createMintQuote(parsed.data.amount, parsed.data.unit);
			return reply.send(quote);
		} catch (err) {
			if (err instanceof CashuError) {
				return reply.status(400).send(err.toJSON());
			}
			throw err;
		}
	});

	/** GET /v1/mint/quote/bolt11/:quote_id — check mint quote state */
	fastify.get<{ Params: { quote_id: string } }>('/mint/quote/bolt11/:quote_id', async (request, reply) => {
		try {
			const quote = await mintService.getMintQuote(request.params.quote_id);
			return reply.send(quote);
		} catch (err) {
			if (err instanceof CashuError) {
				return reply.status(400).send(err.toJSON());
			}
			throw err;
		}
	});

	/** POST /v1/mint/bolt11 — mint tokens */
	fastify.post('/mint/bolt11', async (request, reply) => {
		const parsed = MintTokensRequestSchema.safeParse(request.body);
		if (!parsed.success) {
			const err = new ValidationError(parsed.error.issues[0]?.message);
			return reply.status(400).send(err.toJSON());
		}

		try {
			const tokens = await mintService.mintTokens(parsed.data.quote, parsed.data.outputs);
			return reply.send(tokens);
		} catch (err) {
			if (err instanceof CashuError) {
				return reply.status(400).send(err.toJSON());
			}
			throw err;
		}
	});
}
