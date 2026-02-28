/** Standard Cashu denominations (powers of 2) in satoshis */
export const DENOMINATIONS = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576] as const;

/** Domain separator for hash_to_curve (NUT-00) */
export const HASH_TO_CURVE_DOMAIN = 'Secp256k1_HashToCurve_Cashu_';

/** Maximum allowed length for proof secrets */
export const MAX_PROOF_SECRET_LENGTH = 1024;

/** Default quote TTL in seconds (15 minutes) */
export const DEFAULT_QUOTE_TTL = 900;

/** NUTs supported by this mint */
export const SUPPORTED_NUTS: Record<string, object> = {
	'1': { methods: [{ method: 'bolt11', unit: 'sat' }], disabled: false },
	'2': { methods: [{ method: 'bolt11', unit: 'sat' }], disabled: false },
	'3': { methods: [{ method: 'bolt11', unit: 'sat' }] },
	'4': { methods: [{ method: 'bolt11', unit: 'sat', min_amount: 1, max_amount: 1_000_000 }], disabled: false },
	'5': { methods: [{ method: 'bolt11', unit: 'sat', min_amount: 1, max_amount: 1_000_000 }], disabled: false },
	'6': {},
	'7': { supported: true },
};

/** Maximum number of input proofs per swap/melt request */
export const MAX_INPUTS = 1000;

/** Maximum number of output blinded messages per request */
export const MAX_OUTPUTS = 1000;

/** Mint version string */
export const MINT_VERSION = 'te-btc/cashu-mint-0.1.0';
