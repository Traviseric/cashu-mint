/**
 * MintService — core business logic for the Cashu mint.
 * Orchestrates crypto, database, and Lightning operations.
 * Route handlers call these methods, never DB/Lightning directly.
 */

import type { ILightningBackend } from '../lightning/interface.js';
import type {
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
	SwapRequest,
	SwapResponse,
	BlindedMessage,
} from '../core/types.js';
import type { MintConfig } from '../utils/config.js';

export class MintService {
	constructor(
		private config: MintConfig,
		private lightning: ILightningBackend,
	) {}

	/** GET /v1/keys — return active keyset public keys */
	async getKeys(): Promise<MintKeysResponse> {
		throw new Error('Not implemented — Phase 1');
	}

	/** GET /v1/keys/:keyset_id — return specific keyset public keys */
	async getKeysByKeysetId(_keysetId: string): Promise<MintKeysResponse> {
		throw new Error('Not implemented — Phase 1');
	}

	/** GET /v1/keysets — return all keyset metadata */
	async getKeysets(): Promise<MintKeysetsResponse> {
		throw new Error('Not implemented — Phase 1');
	}

	/** POST /v1/swap — swap proofs for new blind signatures */
	async swap(_request: SwapRequest): Promise<SwapResponse> {
		throw new Error('Not implemented — Phase 1');
	}

	/** POST /v1/mint/quote/bolt11 — create a mint quote (generate Lightning invoice) */
	async createMintQuote(_amount: number, _unit: string): Promise<MintQuoteResponse> {
		throw new Error('Not implemented — Phase 1');
	}

	/** GET /v1/mint/quote/bolt11/:quote_id — check mint quote state */
	async getMintQuote(_quoteId: string): Promise<MintQuoteResponse> {
		throw new Error('Not implemented — Phase 1');
	}

	/** POST /v1/mint/bolt11 — mint tokens (sign blinded messages after quote is paid) */
	async mintTokens(_quoteId: string, _outputs: BlindedMessage[]): Promise<MintTokensResponse> {
		throw new Error('Not implemented — Phase 1');
	}

	/** POST /v1/melt/quote/bolt11 — create a melt quote (estimate LN payment) */
	async createMeltQuote(_request: string, _unit: string): Promise<MeltQuoteResponse> {
		throw new Error('Not implemented — Phase 1');
	}

	/** GET /v1/melt/quote/bolt11/:quote_id — check melt quote state */
	async getMeltQuote(_quoteId: string): Promise<MeltQuoteResponse> {
		throw new Error('Not implemented — Phase 1');
	}

	/** POST /v1/melt/bolt11 — melt tokens (pay Lightning invoice with proofs) */
	async meltTokens(_request: MeltTokensRequest): Promise<MeltTokensResponse> {
		throw new Error('Not implemented — Phase 1');
	}

	/** POST /v1/checkstate — check proof states (NUT-07) */
	async checkProofState(_Ys: string[]): Promise<CheckStateResponse> {
		throw new Error('Not implemented — Phase 1');
	}

	/** GET /v1/info — return mint info (NUT-06) */
	async getMintInfo(): Promise<MintInfo> {
		throw new Error('Not implemented — Phase 1');
	}
}
