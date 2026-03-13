import type { FastifyInstance } from 'fastify';

/**
 * Admin routes — keyset management, internal operations.
 * These endpoints are NOT part of the Cashu protocol (NUT-06 etc.).
 * In production, place behind authentication middleware or firewall rules.
 */
export async function adminRoutes(fastify: FastifyInstance) {
	const mintService = fastify.mintService;

	/**
	 * POST /admin/rotate-keyset
	 *
	 * Deactivates the current active keyset and derives a new one.
	 * Old keyset remains in memory for proof redemptions (spend-only).
	 * Clients should fetch /v1/keys after rotation to use the new keyset.
	 */
	fastify.post('/admin/rotate-keyset', async (_request, reply) => {
		const result = await mintService.rotateKeyset();
		return reply.send({ newKeysetId: result.newKeysetId });
	});
}
