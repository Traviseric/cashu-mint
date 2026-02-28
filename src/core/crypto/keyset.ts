/**
 * Keyset derivation and management — NUT-01/02
 *
 * Private keys derived deterministically from master seed via BIP-32 path convention.
 * Keyset ID derived from hash of concatenated public keys.
 */

import type { MintKeys } from '../types.js';

/**
 * Derives a keyset ID from a set of public keys.
 * ID = first 14 characters of hex(SHA-256(concat(sorted_pubkeys))), prefixed with "00".
 *
 * @param keys - Public keys by denomination
 * @returns 16-character hex keyset ID (e.g., "009a1f293253e41e")
 */
export function deriveKeysetId(_keys: MintKeys): string {
	throw new Error('Not implemented — Phase 1');
}

/**
 * Generates denomination-keyed private/public key pairs from a seed.
 * Uses BIP-32-style derivation with the keyset index.
 *
 * @param seed - Master seed (hex string)
 * @param index - Keyset derivation index
 * @returns Object with `privateKeys` (denomination → hex scalar) and `publicKeys` (denomination → hex point)
 */
export function generateKeysFromSeed(
	_seed: string,
	_index: number,
): { privateKeys: Record<string, string>; publicKeys: MintKeys } {
	throw new Error('Not implemented — Phase 1');
}

/**
 * Serializes a MintKeys object for transport (sorted by denomination).
 *
 * @param keys - Public keys by denomination
 * @returns Sorted MintKeys object
 */
export function serializeKeys(keys: MintKeys): MintKeys {
	const sorted: MintKeys = {};
	for (const k of Object.keys(keys).sort((a, b) => Number(a) - Number(b))) {
		sorted[k] = keys[k];
	}
	return sorted;
}
