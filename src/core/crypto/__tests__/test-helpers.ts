/**
 * Test helpers for creating valid Cashu proofs.
 * Used by integration tests to mint proper tokens.
 */

import { secp256k1 } from '@noble/curves/secp256k1';
import { bytesToHex } from '@noble/hashes/utils';
import {
	hashToCurveString,
	blindMessage,
	signBlindedMessage,
} from '../bdhke.js';
import type { Proof, BlindedMessage } from '../../types.js';

/**
 * Create a valid proof that a mint will accept.
 * Simulates the wallet-side blinding/unblinding.
 *
 * @param secret - The proof secret string
 * @param amount - Denomination amount
 * @param keysetId - Keyset ID
 * @param privateKey - The mint's private key for this denomination
 * @param publicKey - The mint's public key for this denomination
 * @returns Proof, blinding factor r, and blinded message B_
 */
export function createTestProof(
	secret: string,
	amount: number,
	keysetId: string,
	privateKey: string,
	publicKey: string,
): { proof: Proof; r: string; B_: string } {
	// Y = hashToCurveString(secret)
	const Y = hashToCurveString(secret);

	// r = random blinding factor
	const r = bytesToHex(secp256k1.utils.randomPrivateKey());

	// B_ = Y + r*G (blinded message)
	const B_ = blindMessage(Y, r);

	// C_ = k * B_ (mint signs)
	const C_ = signBlindedMessage(B_, privateKey);

	// Wallet unblinds: C = C_ - r*K
	const K = secp256k1.ProjectivePoint.fromHex(publicKey);
	const rK = K.multiply(BigInt(`0x${r}`));
	const pointC_ = secp256k1.ProjectivePoint.fromHex(C_);
	const C = pointC_.subtract(rK);
	const cHex = bytesToHex(C.toRawBytes(true));

	return {
		proof: {
			amount,
			secret,
			C: cHex,
			id: keysetId,
		},
		r,
		B_,
	};
}

/**
 * Create a blinded message for use in mint/swap requests.
 *
 * @param secret - The proof secret string
 * @param amount - Denomination amount
 * @param keysetId - Keyset ID
 * @returns BlindedMessage and blinding factor r
 */
export function createTestBlindedMessage(
	secret: string,
	amount: number,
	keysetId: string,
): { blindedMessage: BlindedMessage; r: string } {
	const Y = hashToCurveString(secret);
	const r = bytesToHex(secp256k1.utils.randomPrivateKey());
	const B_ = blindMessage(Y, r);

	return {
		blindedMessage: {
			amount,
			id: keysetId,
			B_,
		},
		r,
	};
}
