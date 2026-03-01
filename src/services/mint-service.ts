/**
 * MintService — core business logic for the Cashu mint.
 * Orchestrates crypto, database, and Lightning operations.
 * Route handlers call these methods, never DB/Lightning directly.
 */

import { randomBytes } from 'node:crypto';
import { secp256k1 } from '@noble/curves/secp256k1';
import { bytesToHex } from '@noble/hashes/utils';
import type { ILightningBackend } from '../lightning/interface.js';
import {
	hashToCurveString,
	signBlindedMessage,
	verifyProof,
} from '../core/crypto/bdhke.js';
import {
	generateKeysFromSeed,
	deriveKeysetId,
	serializeKeys,
} from '../core/crypto/keyset.js';
import {
	DEFAULT_QUOTE_TTL,
	MINT_VERSION,
	SUPPORTED_NUTS,
} from '../core/constants.js';
import {
	ProofInvalidError,
	TokenAlreadySpentError,
	TransactionNotBalancedError,
	KeysetNotFoundError,
	KeysetInactiveError,
	AmountNotSupportedError,
	QuoteNotPaidError,
	QuoteExpiredError,
	QuoteNotFoundError,
	TokensAlreadyIssuedError,
	LightningBackendError,
} from '../core/errors.js';
import * as repo from '../db/repository.js';
import type {
	BlindedMessage,
	BlindSignature,
	CheckStateResponse,
	MeltQuoteResponse,
	MeltTokensRequest,
	MeltTokensResponse,
	MintInfo,
	MintKeysResponse,
	MintKeysetsResponse,
	MintQuoteResponse,
	MintTokensResponse,
	Proof,
	SwapRequest,
	SwapResponse,
} from '../core/types.js';
import type { MintConfig } from '../utils/config.js';

/** In-memory keyset state */
interface KeysetState {
	id: string;
	unit: string;
	active: boolean;
	derivationIndex: number;
	privateKeys: Record<string, string>;
	publicKeys: Record<string, string>;
}

export class MintService {
	private keysets = new Map<string, KeysetState>();
	private activeKeysetId = '';
	private currentDerivationIndex = 0;

	constructor(
		private config: MintConfig,
		private lightning: ILightningBackend,
	) {}

	/** Initialize mint: load all historical keysets from DB, create first one if none exist */
	async init(): Promise<void> {
		// Load all existing keysets (active + inactive) from DB into memory
		const allKeysets = await repo.getAllKeysets();

		for (const ks of allKeysets) {
			const { privateKeys, publicKeys } = generateKeysFromSeed(
				this.config.mintPrivateKey,
				ks.derivationIndex,
			);
			this.keysets.set(ks.id, {
				id: ks.id,
				unit: ks.unit,
				active: ks.active,
				derivationIndex: ks.derivationIndex,
				privateKeys,
				publicKeys,
			});
		}

		// Find the active keyset with the highest derivation index for 'sat' unit
		const activeKeysets = allKeysets.filter((k) => k.active && k.unit === 'sat');
		if (activeKeysets.length > 0) {
			const latest = activeKeysets.reduce((best, k) =>
				k.derivationIndex > best.derivationIndex ? k : best,
			);
			this.activeKeysetId = latest.id;
			this.currentDerivationIndex = latest.derivationIndex;
		} else {
			// No keyset in DB — derive and create the first one
			await this._createNewKeyset(0);
		}
	}

	/**
	 * Rotate the active keyset — deactivates current, derives next.
	 * Old keyset stays in memory and remains spendable (redeem-only).
	 * Returns the new active keyset ID.
	 */
	async rotateKeyset(): Promise<{ newKeysetId: string }> {
		// Deactivate current active keyset in DB and memory
		await repo.deactivateKeyset(this.activeKeysetId);
		const current = this.keysets.get(this.activeKeysetId);
		if (current) {
			current.active = false;
		}

		// Derive new keyset at next index
		const nextIndex = this.currentDerivationIndex + 1;
		const newState = await this._createNewKeyset(nextIndex);

		return { newKeysetId: newState.id };
	}

	/** GET /v1/keys — return active keyset public keys */
	async getKeys(): Promise<MintKeysResponse> {
		const active = this.getActiveKeyset();
		return {
			keysets: [
				{
					id: active.id,
					unit: active.unit,
					keys: serializeKeys(active.publicKeys),
				},
			],
		};
	}

	/** GET /v1/keys/:keyset_id — return specific keyset public keys */
	async getKeysByKeysetId(keysetId: string): Promise<MintKeysResponse> {
		const ks = this.keysets.get(keysetId);
		if (!ks) {
			throw new KeysetNotFoundError(`Keyset ${keysetId} not found`);
		}
		return {
			keysets: [
				{
					id: ks.id,
					unit: ks.unit,
					keys: serializeKeys(ks.publicKeys),
				},
			],
		};
	}

	/** GET /v1/keysets — return all keyset metadata */
	async getKeysets(): Promise<MintKeysetsResponse> {
		const keysets = Array.from(this.keysets.values()).map((ks) => ({
			id: ks.id,
			unit: ks.unit,
			active: ks.active,
		}));
		return { keysets };
	}

	/** POST /v1/swap — swap proofs for new blind signatures */
	async swap(request: SwapRequest): Promise<SwapResponse> {
		const { inputs, outputs } = request;

		// 1. Validate amounts balance
		const inputSum = inputs.reduce((s, p) => s + p.amount, 0);
		const outputSum = outputs.reduce((s, o) => s + o.amount, 0);
		if (inputSum !== outputSum) {
			throw new TransactionNotBalancedError(
				`Input sum ${inputSum} != output sum ${outputSum}`,
			);
		}

		// 2. Verify all input proof signatures
		for (const proof of inputs) {
			this.verifyProofSignature(proof);
		}

		// 3. Validate output keysets and amounts
		for (const output of outputs) {
			this.validateOutput(output);
		}

		// 4. Sign all blinded messages
		const signatures = this.signOutputs(outputs);

		// 5. Atomic spend + store
		try {
			await repo.spendProofsAndSignAtomically(
				inputs.map((p) => ({
					secret: p.secret,
					y: hashToCurveString(p.secret),
					amount: p.amount,
					keysetId: p.id,
					c: p.C,
					witness: p.witness,
				})),
				signatures.map((s, i) => ({
					amount: s.amount,
					c_: s.C_,
					keysetId: s.id,
					b_: outputs[i].B_,
				})),
			);
		} catch (err: unknown) {
			// Unique constraint = double-spend → attempt saga recovery
			if (isPrismaUniqueConstraintError(err)) {
				return this.recoverSwapSaga(inputs, outputs);
			}
			throw err;
		}

		return { signatures };
	}

	/** POST /v1/mint/quote/bolt11 — create a mint quote */
	async createMintQuote(
		amount: number,
		unit: string,
	): Promise<MintQuoteResponse> {
		const invoice = await this.lightning.createInvoice(
			amount,
			`Mint ${amount} ${unit}`,
		);
		const quoteId = randomBytes(16).toString('hex');
		const expiry = new Date(Date.now() + DEFAULT_QUOTE_TTL * 1000);

		await repo.createMintQuote({
			id: quoteId,
			request: invoice.bolt11,
			amount,
			unit,
			expiry,
			paymentHash: invoice.paymentHash,
		});

		return {
			quote: quoteId,
			request: invoice.bolt11,
			state: 'UNPAID',
			expiry: Math.floor(expiry.getTime() / 1000),
		};
	}

	/** GET /v1/mint/quote/bolt11/:quote_id — check mint quote state */
	async getMintQuote(quoteId: string): Promise<MintQuoteResponse> {
		const quote = await repo.getQuoteById(quoteId);
		if (!quote || quote.type !== 'MINT') {
			throw new QuoteNotFoundError();
		}

		// Transition expired quotes — state is otherwise authoritative from DB
		if (quote.state === 'UNPAID' && new Date() > quote.expiry) {
			await repo.updateQuoteState(quoteId, 'EXPIRED');
			return {
				quote: quote.id,
				request: quote.request,
				state: 'EXPIRED',
				expiry: Math.floor(quote.expiry.getTime() / 1000),
			};
		}

		return {
			quote: quote.id,
			request: quote.request,
			state: quote.state as MintQuoteResponse['state'],
			expiry: Math.floor(quote.expiry.getTime() / 1000),
		};
	}

	/**
	 * Called by the invoice subscription loop when a Lightning invoice is settled.
	 * Transitions the corresponding mint quote from UNPAID → PAID in the DB.
	 */
	async handleInvoiceSettled(paymentHash: string): Promise<void> {
		const quote = await repo.getMintQuoteByPaymentHash(paymentHash);
		if (!quote || quote.state !== 'UNPAID') return;
		await repo.updateQuoteState(quote.id, 'PAID');
	}

	/** POST /v1/mint/bolt11 — mint tokens */
	async mintTokens(
		quoteId: string,
		outputs: BlindedMessage[],
	): Promise<MintTokensResponse> {
		const quote = await repo.getQuoteById(quoteId);
		if (!quote || quote.type !== 'MINT') {
			throw new QuoteNotFoundError();
		}

		// Check expiry
		if (new Date() > quote.expiry) {
			await repo.updateQuoteState(quoteId, 'EXPIRED');
			throw new QuoteExpiredError();
		}

		// Saga: if already ISSUED, return stored signatures
		if (quote.state === 'ISSUED') {
			return this.recoverMintSaga(quoteId);
		}

		if (quote.state !== 'PAID') {
			throw new QuoteNotPaidError();
		}

		// Validate output amounts match quote amount
		const outputSum = outputs.reduce((s, o) => s + o.amount, 0);
		if (outputSum !== quote.amount) {
			throw new TransactionNotBalancedError(
				`Output sum ${outputSum} != quote amount ${quote.amount}`,
			);
		}

		// Validate outputs
		for (const output of outputs) {
			this.validateOutput(output);
		}

		// Sign
		const signatures = this.signOutputs(outputs);

		// Store signatures and update quote to ISSUED
		await repo.storeBlindSignatures(
			signatures.map((s, i) => ({
				amount: s.amount,
				c_: s.C_,
				keysetId: s.id,
				quoteId,
				b_: outputs[i].B_,
			})),
		);
		await repo.updateQuoteState(quoteId, 'ISSUED');

		return { signatures };
	}

	/** POST /v1/melt/quote/bolt11 — create a melt quote */
	async createMeltQuote(
		bolt11: string,
		unit: string,
	): Promise<MeltQuoteResponse> {
		const decoded = await this.lightning.decodePayReq(bolt11);
		const fee = await this.lightning.estimateFee(bolt11);
		const quoteId = randomBytes(16).toString('hex');
		const expiry = new Date(Date.now() + DEFAULT_QUOTE_TTL * 1000);

		await repo.createMeltQuote({
			id: quoteId,
			request: bolt11,
			amount: decoded.amount,
			unit,
			expiry,
			feeReserve: fee,
		});

		return {
			quote: quoteId,
			amount: decoded.amount,
			fee_reserve: fee,
			state: 'UNPAID',
			expiry: Math.floor(expiry.getTime() / 1000),
		};
	}

	/** GET /v1/melt/quote/bolt11/:quote_id — check melt quote state */
	async getMeltQuote(quoteId: string): Promise<MeltQuoteResponse> {
		const quote = await repo.getQuoteById(quoteId);
		if (!quote || quote.type !== 'MELT') {
			throw new QuoteNotFoundError();
		}

		// Transition expired UNPAID quotes — mirrors getMintQuote behavior
		if (quote.state === 'UNPAID' && new Date() > quote.expiry) {
			await repo.updateQuoteState(quoteId, 'EXPIRED');
			return {
				quote: quote.id,
				amount: quote.amount,
				fee_reserve: quote.feeReserve,
				state: 'EXPIRED',
				expiry: Math.floor(quote.expiry.getTime() / 1000),
			};
		}

		return {
			quote: quote.id,
			amount: quote.amount,
			fee_reserve: quote.feeReserve,
			state: quote.state as MeltQuoteResponse['state'],
			expiry: Math.floor(quote.expiry.getTime() / 1000),
		};
	}

	/** POST /v1/melt/bolt11 — melt tokens */
	async meltTokens(request: MeltTokensRequest): Promise<MeltTokensResponse> {
		const quote = await repo.getQuoteById(request.quote);
		if (!quote || quote.type !== 'MELT') {
			throw new QuoteNotFoundError();
		}

		if (quote.state === 'PAID') {
			return { state: 'PAID' };
		}

		if (new Date() > quote.expiry) {
			await repo.updateQuoteState(request.quote, 'EXPIRED');
			throw new QuoteExpiredError();
		}

		const { inputs, outputs } = request;
		const fee = await this.lightning.estimateFee(quote.request);

		// Verify input amount covers quote amount + fee
		const inputSum = inputs.reduce((s, p) => s + p.amount, 0);
		const required = quote.amount + fee;
		if (inputSum < required) {
			throw new TransactionNotBalancedError(
				`Input sum ${inputSum} < required ${required} (amount ${quote.amount} + fee ${fee})`,
			);
		}

		// Verify all input proof signatures
		for (const proof of inputs) {
			this.verifyProofSignature(proof);
		}

		// Sign change outputs if provided
		let changeSignatures: BlindSignature[] | undefined;
		if (outputs && outputs.length > 0) {
			const changeAmount = inputSum - required;
			const changeOutputSum = outputs.reduce((s, o) => s + o.amount, 0);
			if (changeOutputSum !== changeAmount) {
				throw new TransactionNotBalancedError(
					`Change output sum ${changeOutputSum} != expected change ${changeAmount}`,
				);
			}
			for (const output of outputs) {
				this.validateOutput(output);
			}
			changeSignatures = this.signOutputs(outputs);
		}

		// Phase 1: lock proofs as PENDING (two-phase commit)
		try {
			await repo.lockProofsAsPending(
				inputs.map((p) => ({
					secret: p.secret,
					y: hashToCurveString(p.secret),
					amount: p.amount,
					keysetId: p.id,
					c: p.C,
					witness: p.witness,
				})),
				quote.id,
			);
		} catch (err: unknown) {
			if (isPrismaUniqueConstraintError(err)) {
				throw new TokenAlreadySpentError();
			}
			throw err;
		}

		// Phase 2: attempt Lightning payment
		let payResult: Awaited<ReturnType<typeof this.lightning.sendPayment>>;
		try {
			payResult = await this.lightning.sendPayment(quote.request, fee);
		} catch (err) {
			// Payment threw — release the pending lock so proofs are spendable again
			await repo.releasePendingProofs(quote.id);
			await repo.updateQuoteState(request.quote, 'UNPAID');
			throw new LightningBackendError(
				err instanceof Error ? err.message : 'Payment failed',
			);
		}

		if (!payResult.success) {
			// Payment returned failure — release the lock so proofs are spendable again
			await repo.releasePendingProofs(quote.id);
			await repo.updateQuoteState(request.quote, 'UNPAID');
			throw new LightningBackendError(payResult.error ?? 'Payment failed');
		}

		// Payment succeeded — burn proofs permanently and store change signatures
		await repo.burnPendingProofs(
			quote.id,
			changeSignatures
				? changeSignatures.map((s, i) => ({
						amount: s.amount,
						c_: s.C_,
						keysetId: s.id,
						quoteId: request.quote,
						b_: outputs![i].B_,
					}))
				: undefined,
		);
		await repo.updateQuoteState(request.quote, 'PAID');

		return {
			state: 'PAID',
			payment_preimage: payResult.preimage,
			change: changeSignatures,
		};
	}

	/** POST /v1/checkstate — check proof states (NUT-07) */
	async checkProofState(Ys: string[]): Promise<CheckStateResponse> {
		const stateMap = await repo.getProofStatesByY(Ys);

		const states = Ys.map((Y) => ({
			Y,
			state: (stateMap.get(Y) ?? 'UNSPENT') as 'SPENT' | 'UNSPENT' | 'PENDING',
		}));

		return { states };
	}

	/** GET /v1/info — return mint info (NUT-06) */
	async getMintInfo(): Promise<MintInfo> {
		const pubkey = bytesToHex(
			secp256k1.ProjectivePoint.BASE.multiply(
				BigInt(`0x${this.config.mintPrivateKey}`),
			).toRawBytes(true),
		);

		return {
			name: 'te-btc Cashu Mint',
			pubkey,
			version: MINT_VERSION,
			description: 'A Cashu mint powered by te-btc',
			nuts: SUPPORTED_NUTS,
		};
	}

	// ─── Private Helpers ───────────────────────────────────────────────

	/** Derive a new keyset at the given index, persist to DB, and load into memory */
	private async _createNewKeyset(index: number): Promise<KeysetState> {
		const { privateKeys, publicKeys } = generateKeysFromSeed(
			this.config.mintPrivateKey,
			index,
		);
		const keysetId = deriveKeysetId(publicKeys);

		await repo.createKeyset({ id: keysetId, unit: 'sat', active: true, derivationIndex: index });

		const state: KeysetState = {
			id: keysetId,
			unit: 'sat',
			active: true,
			derivationIndex: index,
			privateKeys,
			publicKeys,
		};
		this.keysets.set(keysetId, state);
		this.activeKeysetId = keysetId;
		this.currentDerivationIndex = index;
		return state;
	}

	private getActiveKeyset(): KeysetState {
		const ks = this.keysets.get(this.activeKeysetId);
		if (!ks) {
			throw new KeysetNotFoundError('No active keyset — call init() first');
		}
		return ks;
	}

	private getKeysetForProof(keysetId: string): KeysetState {
		const ks = this.keysets.get(keysetId);
		if (!ks) {
			throw new KeysetNotFoundError(`Keyset ${keysetId} not found`);
		}
		return ks;
	}

	private getPrivateKeyForAmount(
		keyset: KeysetState,
		amount: number,
	): string {
		const key = keyset.privateKeys[String(amount)];
		if (!key) {
			throw new AmountNotSupportedError(
				`Amount ${amount} not supported in keyset ${keyset.id}`,
			);
		}
		return key;
	}

	/** Verify a proof's signature against the keyset's private key */
	private verifyProofSignature(proof: Proof): void {
		const keyset = this.getKeysetForProof(proof.id);
		const privKey = this.getPrivateKeyForAmount(keyset, proof.amount);
		if (!verifyProof(proof.secret, proof.C, privKey)) {
			throw new ProofInvalidError(
				`Proof signature invalid for secret ${proof.secret.slice(0, 16)}...`,
			);
		}
	}

	/** Validate an output blinded message: keyset active + amount supported */
	private validateOutput(output: BlindedMessage): void {
		const keyset = this.keysets.get(output.id);
		if (!keyset) {
			throw new KeysetNotFoundError(
				`Keyset ${output.id} not found`,
			);
		}
		if (!keyset.active) {
			throw new KeysetInactiveError(
				`Keyset ${output.id} is not active`,
			);
		}
		if (!keyset.privateKeys[String(output.amount)]) {
			throw new AmountNotSupportedError(
				`Amount ${output.amount} not supported`,
			);
		}
	}

	/** Sign an array of blinded messages, return BlindSignature[] */
	private signOutputs(outputs: BlindedMessage[]): BlindSignature[] {
		return outputs.map((output) => {
			const keyset = this.keysets.get(output.id);
			if (!keyset) {
				throw new KeysetNotFoundError(`Keyset ${output.id} not found`);
			}
			const privKey = keyset.privateKeys[String(output.amount)];
			const C_ = signBlindedMessage(output.B_, privKey);
			return {
				amount: output.amount,
				id: output.id,
				C_,
			};
		});
	}

	/** Saga recovery for swap: all secrets already spent, return stored sigs */
	private async recoverSwapSaga(
		inputs: Proof[],
		outputs: BlindedMessage[],
	): Promise<SwapResponse> {
		// Verify ALL inputs are spent (otherwise it's a genuine double-spend attack)
		const secrets = inputs.map((p) => p.secret);
		const spentSecrets = await repo.getSpentSecrets(secrets);
		if (spentSecrets.size !== secrets.length) {
			throw new TokenAlreadySpentError(
				'Some proofs already spent (not a replay)',
			);
		}

		// Look up stored signatures by B_ values
		const bPrimes = outputs.map((o) => o.B_);
		const storedSigs = await repo.getBlindSignaturesByB_(bPrimes);

		if (storedSigs.length !== outputs.length) {
			throw new TokenAlreadySpentError(
				'Cannot recover swap — B_ mismatch',
			);
		}

		// Map stored sigs back to outputs order
		const sigMap = new Map(storedSigs.map((s) => [s.b_, s]));
		const signatures: BlindSignature[] = outputs.map((o) => {
			const stored = sigMap.get(o.B_);
			if (!stored) {
				throw new TokenAlreadySpentError('Swap saga recovery failed');
			}
			return {
				amount: stored.amount,
				id: stored.keysetId,
				C_: stored.c_,
			};
		});

		return { signatures };
	}

	/** Saga recovery for mint: quote already ISSUED, return stored sigs */
	private async recoverMintSaga(
		quoteId: string,
	): Promise<MintTokensResponse> {
		const storedSigs = await repo.getBlindSignaturesByQuoteId(quoteId);
		if (storedSigs.length === 0) {
			throw new TokensAlreadyIssuedError();
		}

		const signatures: BlindSignature[] = storedSigs.map((s) => ({
			amount: s.amount,
			id: s.keysetId,
			C_: s.c_,
		}));

		return { signatures };
	}

}

/** Check if a Prisma error is a unique constraint violation (P2002) */
function isPrismaUniqueConstraintError(err: unknown): boolean {
	return (
		typeof err === 'object' &&
		err !== null &&
		'code' in err &&
		(err as { code: string }).code === 'P2002'
	);
}
