/**
 * Database repository — all Prisma queries centralized here.
 * Services call these functions, never Prisma directly.
 */

import type { QuoteState as PrismaQuoteState, QuoteType } from '@prisma/client';
import { prisma } from './client.js';

/** Get all active keysets */
export async function getActiveKeysets() {
	return prisma.keyset.findMany({ where: { active: true } });
}

/** Get all keysets (active + inactive) */
export async function getAllKeysets() {
	return prisma.keyset.findMany();
}

/** Get keyset by ID */
export async function getKeysetById(id: string) {
	return prisma.keyset.findUnique({ where: { id } });
}

/** Check if a secret has already been spent */
export async function isSecretSpent(secret: string): Promise<boolean> {
	const proof = await prisma.spentProof.findUnique({ where: { secret } });
	return proof !== null;
}

/** Check which secrets from a list are already spent */
export async function getSpentSecrets(secrets: string[]): Promise<Set<string>> {
	const spent = await prisma.spentProof.findMany({
		where: { secret: { in: secrets } },
		select: { secret: true },
	});
	return new Set(spent.map((s) => s.secret));
}

/**
 * Atomically spend proofs and store blind signatures.
 * Uses SERIALIZABLE isolation to prevent double-spend races.
 * This is the core atomic operation for swap/mint/melt.
 */
export async function spendProofsAndSignAtomically(
	proofs: Array<{ secret: string; amount: number; keysetId: string; c: string; witness?: unknown }>,
	signatures: Array<{ amount: number; c_: string; keysetId: string; quoteId?: string }>,
) {
	return prisma.$transaction(
		async (tx) => {
			// Insert spent proofs (will fail on duplicate secret = double-spend protection)
			await tx.spentProof.createMany({
				data: proofs.map((p) => ({
					secret: p.secret,
					amount: p.amount,
					keysetId: p.keysetId,
					c: p.c,
					witness: p.witness ?? undefined,
				})),
			});

			// Store blind signatures (saga recovery)
			await tx.blindSignature.createMany({
				data: signatures.map((s) => ({
					amount: s.amount,
					c_: s.c_,
					keysetId: s.keysetId,
					quoteId: s.quoteId ?? null,
				})),
			});
		},
		{
			isolationLevel: 'Serializable',
		},
	);
}

/** Create a mint quote (NUT-04) */
export async function createMintQuote(params: {
	id: string;
	request: string;
	amount: number;
	unit: string;
	expiry: Date;
}) {
	return prisma.pendingQuote.create({
		data: {
			id: params.id,
			request: params.request,
			state: 'UNPAID',
			type: 'MINT',
			amount: params.amount,
			unit: params.unit,
			expiry: params.expiry,
		},
	});
}

/** Create a melt quote (NUT-05) */
export async function createMeltQuote(params: {
	id: string;
	request: string;
	amount: number;
	unit: string;
	expiry: Date;
}) {
	return prisma.pendingQuote.create({
		data: {
			id: params.id,
			request: params.request,
			state: 'UNPAID',
			type: 'MELT',
			amount: params.amount,
			unit: params.unit,
			expiry: params.expiry,
		},
	});
}

/** Get a quote by ID */
export async function getQuoteById(id: string) {
	return prisma.pendingQuote.findUnique({ where: { id } });
}

/** Update quote state */
export async function updateQuoteState(id: string, state: PrismaQuoteState) {
	return prisma.pendingQuote.update({
		where: { id },
		data: { state },
	});
}

/** Get blind signatures by quote ID (saga recovery) */
export async function getBlindSignaturesByQuoteId(quoteId: string) {
	return prisma.blindSignature.findMany({ where: { quoteId } });
}

/** Get proof states for checkstate (NUT-07) */
export async function getProofStates(secrets: string[]): Promise<Map<string, 'SPENT' | 'PENDING'>> {
	const spent = await prisma.spentProof.findMany({
		where: { secret: { in: secrets } },
		select: { secret: true },
	});

	const stateMap = new Map<string, 'SPENT' | 'PENDING'>();
	for (const s of spent) {
		stateMap.set(s.secret, 'SPENT');
	}
	return stateMap;
}
