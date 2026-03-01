/**
 * Blind Diffie-Hellman Key Exchange (BDHKE) — NUT-00
 *
 * Core cryptographic operations for Cashu blind signatures.
 * Uses @noble/curves secp256k1 and @noble/hashes SHA-256.
 *
 * Flow:
 * 1. Mint publishes K = k * G for each denomination
 * 2. Wallet sends B_ = Y + r*G (blinded secret)
 * 3. Mint returns C_ = k * B_ (blinded signature)
 * 4. Wallet unblinds: C = C_ - r*K = k*Y
 * 5. Mint verifies: C == k * hash_to_curve(secret)
 */

import { secp256k1 } from '@noble/curves/secp256k1';
import { sha256 } from '@noble/hashes/sha256';
import { bytesToHex, hexToBytes, concatBytes } from '@noble/hashes/utils';

const DOMAIN_SEPARATOR = hexToBytes(
	'536563703235366b315f48617368546f43757276655f43617368755f',
);

const encoder = new TextEncoder();

/**
 * Maps a message to a point on the secp256k1 curve.
 * Uses domain separator 'Secp256k1_HashToCurve_Cashu_' with incrementing
 * uint32 counter in little-endian byte order until a valid x-coordinate is found.
 *
 * @param secretBytes - Raw secret bytes (Uint8Array)
 * @returns Hex-encoded compressed point (33 bytes)
 */
export function hashToCurve(secretBytes: Uint8Array): string {
	const msgHash = sha256(concatBytes(DOMAIN_SEPARATOR, secretBytes));
	const counter = new Uint32Array(1);

	for (let i = 0; i < 65536; i++) {
		const counterBytes = new Uint8Array(counter.buffer);
		const hash = sha256(concatBytes(msgHash, counterBytes));
		const compressed = concatBytes(new Uint8Array([0x02]), hash);
		try {
			const point = secp256k1.ProjectivePoint.fromHex(compressed);
			point.assertValidity();
			return bytesToHex(compressed);
		} catch {
			counter[0]++;
		}
	}
	throw new Error('hashToCurve: could not find valid point');
}

/**
 * Convenience: hash a string secret to a curve point.
 * Encodes the string as UTF-8 bytes first, matching cashu-ts wallet behavior.
 *
 * @param secret - The proof secret string
 * @returns Hex-encoded compressed point (33 bytes)
 */
export function hashToCurveString(secret: string): string {
	return hashToCurve(encoder.encode(secret));
}

/**
 * Blinds a message point with a random blinding factor.
 *
 * B_ = Y + r * G
 *
 * @param Y - Point on curve from hashToCurve(secret)
 * @param r - Random blinding factor (hex scalar)
 * @returns B_ as hex-encoded compressed point
 */
export function blindMessage(Y: string, r: string): string {
	const pointY = secp256k1.ProjectivePoint.fromHex(Y);
	const rG = secp256k1.ProjectivePoint.BASE.multiply(BigInt(`0x${r}`));
	const B_ = pointY.add(rG);
	return bytesToHex(B_.toRawBytes(true));
}

/**
 * Signs a blinded message with the mint's private key.
 *
 * C_ = k * B_
 *
 * @param B_ - Blinded message (hex-encoded compressed point)
 * @param k - Mint's private key for this denomination (hex scalar)
 * @returns C_ as hex-encoded compressed point
 */
export function signBlindedMessage(B_: string, k: string): string {
	const pointB_ = secp256k1.ProjectivePoint.fromHex(B_);
	pointB_.assertValidity();
	const C_ = pointB_.multiply(BigInt(`0x${k}`));
	return bytesToHex(C_.toRawBytes(true));
}

/**
 * Verifies an unblinded proof against the mint's private key.
 *
 * Checks: C == k * hash_to_curve(secret)
 *
 * @param secret - The proof secret string (will be UTF-8 encoded)
 * @param C - The unblinded signature (hex-encoded point)
 * @param k - Mint's private key for this denomination (hex scalar)
 * @returns true if the proof is valid
 */
export function verifyProof(secret: string, C: string, k: string): boolean {
	try {
		const Y = hashToCurveString(secret);
		const pointY = secp256k1.ProjectivePoint.fromHex(Y);
		const expected = pointY.multiply(BigInt(`0x${k}`));
		const pointC = secp256k1.ProjectivePoint.fromHex(C);
		return expected.equals(pointC);
	} catch {
		return false;
	}
}

/**
 * Generates a DLEQ proof (NUT-12) proving the mint used the advertised key.
 *
 * Proves: log_G(K) == log_{B_}(C_) without revealing k
 *
 * @param k - Mint's private key (hex scalar)
 * @param B_ - Blinded message (hex-encoded compressed point)
 * @returns DLEQ proof { e, s } as hex strings
 */
export function generateDLEQ(_k: string, _B_: string): { e: string; s: string } {
	throw new Error('Not implemented — Phase 2');
}
