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

/**
 * Maps a secret string to a point on the secp256k1 curve.
 * Uses domain separator 'Secp256k1_HashToCurve_Cashu_' with incrementing
 * uint32 counter in little-endian byte order until a valid x-coordinate is found.
 *
 * @param secret - The proof secret string
 * @returns Hex-encoded compressed point (33 bytes)
 */
export function hashToCurve(_secret: string): string {
	throw new Error('Not implemented — Phase 1');
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
export function blindMessage(_Y: string, _r: string): string {
	throw new Error('Not implemented — Phase 1');
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
export function signBlindedMessage(_B_: string, _k: string): string {
	throw new Error('Not implemented — Phase 1');
}

/**
 * Verifies an unblinded proof against the mint's private key.
 *
 * Checks: C == k * hash_to_curve(secret)
 *
 * @param secret - The proof secret
 * @param C - The unblinded signature (hex-encoded compressed point)
 * @param k - Mint's private key for this denomination (hex scalar)
 * @returns true if the proof is valid
 */
export function verifyProof(_secret: string, _C: string, _k: string): boolean {
	throw new Error('Not implemented — Phase 1');
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
	throw new Error('Not implemented — Phase 1');
}
