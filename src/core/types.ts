/** Cashu protocol types — NUT-00 through NUT-07 */

/** A single ecash proof (token component) */
export interface Proof {
	amount: number;
	secret: string;
	C: string; // unblinded signature (hex-encoded point)
	id: string; // keyset ID
	witness?: string; // NUT-11 P2PK / NUT-14 HTLC witness data (JSON string)
}

/** Blinded message sent from wallet to mint for signing */
export interface BlindedMessage {
	amount: number;
	id: string; // keyset ID
	B_: string; // blinded secret (hex-encoded point)
}

/** Blinded signature returned from mint to wallet */
export interface BlindSignature {
	amount: number;
	id: string; // keyset ID
	C_: string; // blinded signature (hex-encoded point)
	dleq?: DLEQProof; // NUT-12
}

/** Discrete Log Equality proof (NUT-12) */
export interface DLEQProof {
	e: string;
	s: string;
}

/** Public keys for a single keyset, keyed by denomination */
export type MintKeys = Record<string, string>;

/** Keyset metadata */
export interface MintKeyset {
	id: string;
	unit: string;
	active: boolean;
}

/** Response for GET /v1/keys */
export interface MintKeysResponse {
	keysets: Array<{
		id: string;
		unit: string;
		keys: MintKeys;
	}>;
}

/** Response for GET /v1/keysets */
export interface MintKeysetsResponse {
	keysets: MintKeyset[];
}

/** Quote state machine (NUT-04/05) */
export type QuoteState = 'UNPAID' | 'PAID' | 'PENDING' | 'ISSUED' | 'EXPIRED';

/** POST /v1/swap request */
export interface SwapRequest {
	inputs: Proof[];
	outputs: BlindedMessage[];
}

/** POST /v1/swap response */
export interface SwapResponse {
	signatures: BlindSignature[];
}

/** POST /v1/mint/quote/bolt11 request */
export interface MintQuoteRequest {
	amount: number;
	unit: string;
}

/** POST /v1/mint/quote/bolt11 response */
export interface MintQuoteResponse {
	quote: string;
	request: string; // BOLT11 invoice
	state: QuoteState;
	expiry: number; // Unix timestamp
}

/** POST /v1/mint/bolt11 request */
export interface MintTokensRequest {
	quote: string;
	outputs: BlindedMessage[];
}

/** POST /v1/mint/bolt11 response */
export interface MintTokensResponse {
	signatures: BlindSignature[];
}

/** POST /v1/melt/quote/bolt11 request */
export interface MeltQuoteRequest {
	request: string; // BOLT11 invoice
	unit: string;
}

/** POST /v1/melt/quote/bolt11 response */
export interface MeltQuoteResponse {
	quote: string;
	amount: number;
	fee_reserve: number;
	state: QuoteState;
	expiry: number;
}

/** POST /v1/melt/bolt11 request */
export interface MeltTokensRequest {
	quote: string;
	inputs: Proof[];
	outputs?: BlindedMessage[]; // NUT-08 fee return
}

/** POST /v1/melt/bolt11 response */
export interface MeltTokensResponse {
	state: QuoteState;
	payment_preimage?: string;
	change?: BlindSignature[]; // NUT-08
}

/** POST /v1/checkstate request */
export interface CheckStateRequest {
	Ys: string[]; // Y = hash_to_curve(secret), hex-encoded
}

/** Individual proof state */
export interface ProofState {
	Y: string;
	state: 'UNSPENT' | 'SPENT' | 'PENDING';
	witness?: string;
}

/** POST /v1/checkstate response */
export interface CheckStateResponse {
	states: ProofState[];
}

/** GET /v1/info response */
export interface MintInfo {
	name: string;
	pubkey: string;
	version: string;
	description?: string;
	description_long?: string;
	contact?: Array<{ method: string; info: string }>;
	nuts: Record<string, Record<string, unknown>>;
}
