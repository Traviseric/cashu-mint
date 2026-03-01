/** Zod schemas for request validation at the route edge */

import { z } from 'zod';

/** Compressed secp256k1 curve point: 02/03 prefix + 32 bytes = 66 hex chars */
const hexPoint = z
	.string()
	.regex(
		/^(02|03)[0-9a-fA-F]{64}$/,
		'Must be a compressed secp256k1 point (66 hex chars, 02/03 prefix)',
	);

/** Single proof (token component) */
export const ProofSchema = z.object({
	amount: z.number().int().positive(),
	secret: z.string().min(1).max(1024),
	C: hexPoint,
	id: z.string().min(1),
	witness: z.string().optional(),
});

/** Blinded message for signing */
export const BlindedMessageSchema = z.object({
	amount: z.number().int().positive(),
	id: z.string().min(1),
	B_: hexPoint,
});

/** POST /v1/swap */
export const SwapRequestSchema = z.object({
	inputs: z.array(ProofSchema).min(1).max(1000),
	outputs: z.array(BlindedMessageSchema).min(1).max(1000),
});

/** POST /v1/mint/quote/bolt11 */
export const MintQuoteRequestSchema = z.object({
	amount: z.number().int().positive(),
	unit: z.string().default('sat'),
});

/** POST /v1/mint/bolt11 */
export const MintTokensRequestSchema = z.object({
	quote: z.string().min(1),
	outputs: z.array(BlindedMessageSchema).min(1).max(1000),
});

/** POST /v1/melt/quote/bolt11 */
export const MeltQuoteRequestSchema = z.object({
	request: z.string().min(1),
	unit: z.string().default('sat'),
});

/** POST /v1/melt/bolt11 */
export const MeltTokensRequestSchema = z.object({
	quote: z.string().min(1),
	inputs: z.array(ProofSchema).min(1).max(1000),
	outputs: z.array(BlindedMessageSchema).optional(),
});

/** POST /v1/checkstate */
export const CheckStateRequestSchema = z.object({
	Ys: z.array(z.string().min(1)).min(1).max(1000),
});
