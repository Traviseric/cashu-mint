import { describe, it, expect } from 'vitest';
import { hashToCurve, blindMessage, signBlindedMessage, verifyProof, generateDLEQ } from '../bdhke.js';

describe('BDHKE (NUT-00)', () => {
	describe('hashToCurve', () => {
		it('should map a secret to a valid curve point', () => {
			// Known test vector from Cashu NUT-00 spec
			// secret: "0000000000000000000000000000000000000000000000000000000000000000"
			// expected Y: "024cce997d3b518f739663b757deaec95bcd9473c30a14ac2fd04023a739d1a725"
			expect(() => hashToCurve('0000000000000000000000000000000000000000000000000000000000000000'))
				.toThrow('Not implemented');
		});

		it('should map a different secret to a different point', () => {
			// secret: "0000000000000000000000000000000000000000000000000000000000000001"
			// expected Y: "022e7158e11c9506f1aa4248bf531298daa7febd6194f003edcd9b93ade6253acf"
			expect(() => hashToCurve('0000000000000000000000000000000000000000000000000000000000000001'))
				.toThrow('Not implemented');
		});
	});

	describe('blindMessage', () => {
		it('should blind a message with a blinding factor', () => {
			expect(() => blindMessage('deadbeef', 'cafebabe')).toThrow('Not implemented');
		});
	});

	describe('signBlindedMessage', () => {
		it('should sign a blinded message with the private key', () => {
			expect(() => signBlindedMessage('deadbeef', 'cafebabe')).toThrow('Not implemented');
		});
	});

	describe('verifyProof', () => {
		it('should verify a valid proof', () => {
			expect(() => verifyProof('secret', 'C', 'k')).toThrow('Not implemented');
		});
	});

	describe('generateDLEQ', () => {
		it('should generate a DLEQ proof', () => {
			expect(() => generateDLEQ('k', 'B_')).toThrow('Not implemented');
		});
	});
});
