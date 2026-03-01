import { describe, it, expect } from 'vitest';
import { secp256k1 } from '@noble/curves/secp256k1';
import { generateKeysFromSeed, deriveKeysetId, serializeKeys } from '../keyset.js';
import { DENOMINATIONS } from '../../constants.js';

const TEST_SEED =
	'aabbccddee0011223344556677889900aabbccddee0011223344556677889900';

describe('Keyset Derivation (NUT-01/02)', () => {
	describe('generateKeysFromSeed', () => {
		it('should generate keys for all 21 denominations', () => {
			const { privateKeys, publicKeys } = generateKeysFromSeed(
				TEST_SEED,
				0,
			);
			expect(Object.keys(privateKeys)).toHaveLength(DENOMINATIONS.length);
			expect(Object.keys(publicKeys)).toHaveLength(DENOMINATIONS.length);

			for (const denom of DENOMINATIONS) {
				expect(privateKeys[String(denom)]).toBeDefined();
				expect(publicKeys[String(denom)]).toBeDefined();
			}
		});

		it('should produce valid compressed public keys', () => {
			const { publicKeys } = generateKeysFromSeed(TEST_SEED, 0);
			for (const denom of DENOMINATIONS) {
				const pubHex = publicKeys[String(denom)];
				expect(pubHex).toHaveLength(66);
				expect(pubHex.startsWith('02') || pubHex.startsWith('03')).toBe(
					true,
				);
				// Validate it's a real point
				const point = secp256k1.ProjectivePoint.fromHex(pubHex);
				point.assertValidity();
			}
		});

		it('should be deterministic (same seed+index → same keys)', () => {
			const result1 = generateKeysFromSeed(TEST_SEED, 0);
			const result2 = generateKeysFromSeed(TEST_SEED, 0);
			expect(result1.privateKeys).toEqual(result2.privateKeys);
			expect(result1.publicKeys).toEqual(result2.publicKeys);
		});

		it('should produce different keys for different index', () => {
			const result0 = generateKeysFromSeed(TEST_SEED, 0);
			const result1 = generateKeysFromSeed(TEST_SEED, 1);
			expect(result0.privateKeys['1']).not.toBe(result1.privateKeys['1']);
			expect(result0.publicKeys['1']).not.toBe(result1.publicKeys['1']);
		});

		it('should produce different keys for different seed', () => {
			const otherSeed =
				'1122334455667788990011223344556677889900112233445566778899001122';
			const result1 = generateKeysFromSeed(TEST_SEED, 0);
			const result2 = generateKeysFromSeed(otherSeed, 0);
			expect(result1.privateKeys['1']).not.toBe(
				result2.privateKeys['1'],
			);
		});

		it('should produce public keys that match private keys', () => {
			const { privateKeys, publicKeys } = generateKeysFromSeed(
				TEST_SEED,
				0,
			);
			for (const denom of DENOMINATIONS) {
				const privHex = privateKeys[String(denom)];
				const expectedPub = secp256k1.ProjectivePoint.BASE.multiply(
					BigInt(`0x${privHex}`),
				);
				expect(publicKeys[String(denom)]).toBe(
					secp256k1.ProjectivePoint.fromHex(
						publicKeys[String(denom)],
					)
						.toHex(true),
				);
				expect(
					secp256k1.ProjectivePoint.fromHex(publicKeys[String(denom)])
						.equals(expectedPub),
				).toBe(true);
			}
		});
	});

	describe('deriveKeysetId', () => {
		it('should return a 16-char hex string starting with "00"', () => {
			const { publicKeys } = generateKeysFromSeed(TEST_SEED, 0);
			const id = deriveKeysetId(publicKeys);
			expect(id).toHaveLength(16);
			expect(id.startsWith('00')).toBe(true);
			// All hex chars
			expect(/^[0-9a-f]{16}$/.test(id)).toBe(true);
		});

		it('should be deterministic', () => {
			const { publicKeys } = generateKeysFromSeed(TEST_SEED, 0);
			const id1 = deriveKeysetId(publicKeys);
			const id2 = deriveKeysetId(publicKeys);
			expect(id1).toBe(id2);
		});

		it('should produce different IDs for different keysets', () => {
			const keys0 = generateKeysFromSeed(TEST_SEED, 0);
			const keys1 = generateKeysFromSeed(TEST_SEED, 1);
			const id0 = deriveKeysetId(keys0.publicKeys);
			const id1 = deriveKeysetId(keys1.publicKeys);
			expect(id0).not.toBe(id1);
		});
	});

	describe('serializeKeys', () => {
		it('should sort keys by denomination numerically', () => {
			const unsorted = { '128': 'pub128', '1': 'pub1', '64': 'pub64' };
			const sorted = serializeKeys(unsorted);
			const keys = Object.keys(sorted);
			expect(keys).toEqual(['1', '64', '128']);
		});
	});
});
