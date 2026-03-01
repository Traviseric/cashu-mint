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

/** Get all keysets (active + inactive), ordered by derivation index */
export async function getAllKeysets() {
	return prisma.keyset.findMany({ orderBy: { derivationIndex: 'asc' } });
}

/** Get keyset by ID */
export async function getKeysetById(id: string) {
	return prisma.keyset.findUnique({ where: { id } });
}

/** Create a keyset record */
export async function createKeyset(params: {
	id: string;
	unit: string;
	active: boolean;
	derivationIndex?: number;
}) {
	return prisma.keyset.upsert({
		where: { id: params.id },
		update: { active: params.active },
		create: {
			id: params.id,
			unit: params.unit,
			active: params.active,
			derivationIndex: params.derivationIndex ?? 0,
		},
	});
}

/** Deactivate a keyset (rotation — old keyset stays redeemable but not issuable) */
export async function deactivateKeyset(id: string) {
	return prisma.keyset.update({
		where: { id },
		data: { active: false },
	});
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
	proofs: Array<{
		secret: string;
		y: string;
		amount: number;
		keysetId: string;
		c: string;
		witness?: unknown;
	}>,
	signatures: Array<{
		amount: number;
		c_: string;
		keysetId: string;
		quoteId?: string;
		b_?: string;
	}>,
) {
	return prisma.$transaction(
		async (tx) => {
			// Insert spent proofs (will fail on duplicate secret = double-spend protection)
			await tx.spentProof.createMany({
				data: proofs.map((p) => ({
					secret: p.secret,
					y: p.y,
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
					b_: s.b_ ?? null,
				})),
			});
		},
		{
			isolationLevel: 'Serializable',
		},
	);
}

/** Store blind signatures without spending proofs (for mint tokens) */
export async function storeBlindSignatures(
	signatures: Array<{
		amount: number;
		c_: string;
		keysetId: string;
		quoteId?: string;
		b_?: string;
	}>,
) {
	return prisma.blindSignature.createMany({
		data: signatures.map((s) => ({
			amount: s.amount,
			c_: s.c_,
			keysetId: s.keysetId,
			quoteId: s.quoteId ?? null,
			b_: s.b_ ?? null,
		})),
	});
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
	feeReserve?: number;
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

/** Get blind signatures by quote ID (saga recovery for mint) */
export async function getBlindSignaturesByQuoteId(quoteId: string) {
	return prisma.blindSignature.findMany({ where: { quoteId } });
}

/** Get blind signatures by B_ values (saga recovery for swap) */
export async function getBlindSignaturesByB_(bPrimes: string[]) {
	return prisma.blindSignature.findMany({
		where: { b_: { in: bPrimes } },
	});
}

/** Get proof states by Y values for NUT-07 checkstate */
export async function getProofStatesByY(
	ys: string[],
): Promise<Map<string, 'SPENT'>> {
	const spent = await prisma.spentProof.findMany({
		where: { y: { in: ys } },
		select: { y: true },
	});

	const stateMap = new Map<string, 'SPENT'>();
	for (const s of spent) {
		stateMap.set(s.y, 'SPENT');
	}
	return stateMap;
}

/** Get proof states for checkstate (NUT-07) — by secret */
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
