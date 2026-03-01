/**
 * Keyset derivation and management — NUT-01/02
 *
 * Private keys derived deterministically from master seed via BIP-32 path convention.
 * Keyset ID derived from hash of concatenated public keys.
 */

import { HDKey } from '@scure/bip32';
import { secp256k1 } from '@noble/curves/secp256k1';
import { sha256 } from '@noble/hashes/sha256';
import { bytesToHex, hexToBytes } from '@noble/hashes/utils';
import { DENOMINATIONS } from '../constants.js';
import type { MintKeys } from '../types.js';

/**
 * Derives a keyset ID from a set of public keys.
 * ID = first 14 characters of hex(SHA-256(concat(sorted_pubkeys))), prefixed with "00".
 *
 * @param keys - Public keys by denomination
 * @returns 16-character hex keyset ID (e.g., "009a1f293253e41e")
 */
export function deriveKeysetId(keys: MintKeys): string {
	const sortedAmounts = Object.keys(keys).sort(
		(a, b) => Number(a) - Number(b),
	);
	const pubkeyBuffers = sortedAmounts.map((amt) => hexToBytes(keys[amt]));
	let concat = new Uint8Array(0);
	for (const buf of pubkeyBuffers) {
		const merged = new Uint8Array(concat.length + buf.length);
		merged.set(concat);
		merged.set(buf, concat.length);
		concat = merged;
	}
	const hash = sha256(concat);
	const hashHex = bytesToHex(hash);
	return `00${hashHex.slice(0, 14)}`;
}

/**
 * Generates denomination-keyed private/public key pairs from a seed.
 * Uses BIP-32-style derivation with the keyset index.
 * Path: m/0'/{index}'/0'/{i} where i is the denomination index.
 *
 * @param seed - Master seed (hex string)
 * @param index - Keyset derivation index
 * @returns Object with `privateKeys` (denomination → hex scalar) and `publicKeys` (denomination → hex point)
 */
export function generateKeysFromSeed(
	seed: string,
	index: number,
): { privateKeys: Record<string, string>; publicKeys: MintKeys } {
	const master = HDKey.fromMasterSeed(hexToBytes(seed));
	const privateKeys: Record<string, string> = {};
	const publicKeys: MintKeys = {};

	for (let i = 0; i < DENOMINATIONS.length; i++) {
		const amount = DENOMINATIONS[i];
		const child = master.derive(`m/0'/${index}'/0'/${i}`);
		if (!child.privateKey) {
			throw new Error(`Failed to derive key for denomination ${amount}`);
		}
		const privHex = bytesToHex(child.privateKey);
		const pubPoint = secp256k1.ProjectivePoint.BASE.multiply(
			BigInt(`0x${privHex}`),
		);
		const pubHex = bytesToHex(pubPoint.toRawBytes(true));

		privateKeys[String(amount)] = privHex;
		publicKeys[String(amount)] = pubHex;
	}

	return { privateKeys, publicKeys };
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
