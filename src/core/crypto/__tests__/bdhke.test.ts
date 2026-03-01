import { describe, it, expect } from 'vitest';
import { secp256k1 } from '@noble/curves/secp256k1';
import { bytesToHex, hexToBytes } from '@noble/hashes/utils';
import {
	hashToCurve,
	hashToCurveString,
	blindMessage,
	signBlindedMessage,
	verifyProof,
	generateDLEQ,
} from '../bdhke.js';

describe('BDHKE (NUT-00)', () => {
	describe('hashToCurve', () => {
		it('should map 32 zero bytes to known test vector', () => {
			// NUT-00 test vector: input is 32 zero bytes (raw)
			const secret = hexToBytes(
				'0000000000000000000000000000000000000000000000000000000000000000',
			);
			const Y = hashToCurve(secret);
			expect(Y).toBe(
				'024cce997d3b518f739663b757deaec95bcd9473c30a14ac2fd04023a739d1a725',
			);
		});

		it('should map 0x00...01 to known test vector', () => {
			// NUT-00 test vector
			const secret = hexToBytes(
				'0000000000000000000000000000000000000000000000000000000000000001',
			);
			const Y = hashToCurve(secret);
			expect(Y).toBe(
				'022e7158e11c9506f1aa4248bf531298daa7febd6194f003edcd9b93ade6253acf',
			);
		});

		it('should return a valid compressed point (33 bytes hex)', () => {
			const Y = hashToCurveString('test_secret');
			expect(Y).toHaveLength(66);
			expect(Y.startsWith('02') || Y.startsWith('03')).toBe(true);
			const point = secp256k1.ProjectivePoint.fromHex(Y);
			point.assertValidity();
		});

		it('should produce different points for different secrets', () => {
			const Y1 = hashToCurveString('secret_a');
			const Y2 = hashToCurveString('secret_b');
			expect(Y1).not.toBe(Y2);
		});

		it('hashToCurveString should UTF-8 encode the string', () => {
			// hashToCurveString("abc") should produce same result as
			// hashToCurve(TextEncoder.encode("abc"))
			const fromString = hashToCurveString('abc');
			const fromBytes = hashToCurve(new TextEncoder().encode('abc'));
			expect(fromString).toBe(fromBytes);
		});
	});

	describe('blindMessage', () => {
		it('should produce a valid blinded point B_ = Y + r*G', () => {
			const Y = hashToCurveString('test_secret');
			const r = bytesToHex(secp256k1.utils.randomPrivateKey());
			const B_ = blindMessage(Y, r);

			expect(B_).toHaveLength(66);
			expect(B_.startsWith('02') || B_.startsWith('03')).toBe(true);
			const point = secp256k1.ProjectivePoint.fromHex(B_);
			point.assertValidity();
		});

		it('should produce different B_ for different blinding factors', () => {
			const Y = hashToCurveString('test_secret');
			const r1 = bytesToHex(secp256k1.utils.randomPrivateKey());
			const r2 = bytesToHex(secp256k1.utils.randomPrivateKey());
			const B_1 = blindMessage(Y, r1);
			const B_2 = blindMessage(Y, r2);
			expect(B_1).not.toBe(B_2);
		});
	});

	describe('signBlindedMessage', () => {
		it('should sign a blinded message and return a valid point', () => {
			const Y = hashToCurveString('test_secret');
			const r = bytesToHex(secp256k1.utils.randomPrivateKey());
			const B_ = blindMessage(Y, r);
			const k = bytesToHex(secp256k1.utils.randomPrivateKey());
			const C_ = signBlindedMessage(B_, k);

			expect(C_).toHaveLength(66);
			expect(C_.startsWith('02') || C_.startsWith('03')).toBe(true);
			const point = secp256k1.ProjectivePoint.fromHex(C_);
			point.assertValidity();
		});

		it('should reject invalid B_ point', () => {
			const invalidPoint = '04' + '00'.repeat(32);
			const k = bytesToHex(secp256k1.utils.randomPrivateKey());
			expect(() => signBlindedMessage(invalidPoint, k)).toThrow();
		});
	});

	describe('verifyProof', () => {
		it('should verify a valid proof (full BDHKE round-trip)', () => {
			const secret = 'test_proof_secret';
			const k = bytesToHex(secp256k1.utils.randomPrivateKey());
			const r = bytesToHex(secp256k1.utils.randomPrivateKey());

			// Y = hashToCurve(secret) — string version
			const Y = hashToCurveString(secret);

			// B_ = Y + r*G
			const B_ = blindMessage(Y, r);

			// C_ = k * B_ (mint signs)
			const C_ = signBlindedMessage(B_, k);

			// Wallet unblinds: C = C_ - r*K
			const K = secp256k1.ProjectivePoint.BASE.multiply(BigInt(`0x${k}`));
			const rK = K.multiply(BigInt(`0x${r}`));
			const pointC_ = secp256k1.ProjectivePoint.fromHex(C_);
			const C = pointC_.subtract(rK);
			const cHex = bytesToHex(C.toRawBytes(true));

			// Mint verifies: C == k * Y
			expect(verifyProof(secret, cHex, k)).toBe(true);
		});

		it('should return false for wrong key', () => {
			const secret = 'test_proof_secret';
			const k = bytesToHex(secp256k1.utils.randomPrivateKey());
			const r = bytesToHex(secp256k1.utils.randomPrivateKey());
			const wrongK = bytesToHex(secp256k1.utils.randomPrivateKey());

			const Y = hashToCurveString(secret);
			const B_ = blindMessage(Y, r);
			const C_ = signBlindedMessage(B_, k);

			const K = secp256k1.ProjectivePoint.BASE.multiply(BigInt(`0x${k}`));
			const rK = K.multiply(BigInt(`0x${r}`));
			const pointC_ = secp256k1.ProjectivePoint.fromHex(C_);
			const C = pointC_.subtract(rK);
			const cHex = bytesToHex(C.toRawBytes(true));

			expect(verifyProof(secret, cHex, wrongK)).toBe(false);
		});

		it('should return false for wrong secret', () => {
			const secret = 'correct_secret';
			const k = bytesToHex(secp256k1.utils.randomPrivateKey());
			const r = bytesToHex(secp256k1.utils.randomPrivateKey());

			const Y = hashToCurveString(secret);
			const B_ = blindMessage(Y, r);
			const C_ = signBlindedMessage(B_, k);

			const K = secp256k1.ProjectivePoint.BASE.multiply(BigInt(`0x${k}`));
			const rK = K.multiply(BigInt(`0x${r}`));
			const pointC_ = secp256k1.ProjectivePoint.fromHex(C_);
			const C = pointC_.subtract(rK);
			const cHex = bytesToHex(C.toRawBytes(true));

			expect(verifyProof('wrong_secret', cHex, k)).toBe(false);
		});
	});

	describe('generateDLEQ', () => {
		it('should throw Phase 2 not implemented', () => {
			const k = bytesToHex(secp256k1.utils.randomPrivateKey());
			const Y = hashToCurveString('test');
			const B_ = blindMessage(Y, k);
			expect(() => generateDLEQ(k, B_)).toThrow('Phase 2');
		});
	});
});
