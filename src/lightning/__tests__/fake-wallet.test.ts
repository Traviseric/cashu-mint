import { describe, it, expect, beforeEach } from 'vitest';
import { FakeWallet } from '../fake-wallet.js';

describe('FakeWallet', () => {
	let wallet: FakeWallet;

	beforeEach(() => {
		wallet = new FakeWallet();
	});

	describe('createInvoice', () => {
		it('should create an invoice with correct amount', async () => {
			const invoice = await wallet.createInvoice(1000, 'test payment');
			expect(invoice.amount).toBe(1000);
			expect(invoice.bolt11).toMatch(/^lnbc1000n1fake/);
			expect(invoice.paymentHash).toHaveLength(64);
		});

		it('should create unique invoices', async () => {
			const inv1 = await wallet.createInvoice(100, 'first');
			const inv2 = await wallet.createInvoice(100, 'second');
			expect(inv1.paymentHash).not.toBe(inv2.paymentHash);
			expect(inv1.bolt11).not.toBe(inv2.bolt11);
		});

		it('should track created invoices', async () => {
			const invoice = await wallet.createInvoice(500, 'test');
			expect(wallet.hasInvoice(invoice.paymentHash)).toBe(true);
			expect(wallet.isSettled(invoice.paymentHash)).toBe(false);
		});
	});

	describe('decodePayReq', () => {
		it('should decode a fake bolt11 string', async () => {
			const invoice = await wallet.createInvoice(2000, 'decode test');
			const decoded = await wallet.decodePayReq(invoice.bolt11);
			expect(decoded.amount).toBe(2000);
			expect(decoded.description).toBe('Fake invoice');
			expect(decoded.expiry).toBe(3600);
		});
	});

	describe('estimateFee', () => {
		it('should return deterministic fee of 1 sat', async () => {
			const fee = await wallet.estimateFee('lnbc1000n1fakeinvoice');
			expect(fee).toBe(1);
		});
	});

	describe('sendPayment', () => {
		it('should return a successful payment result', async () => {
			const result = await wallet.sendPayment('lnbc1000n1fakeinvoice', 10);
			expect(result.success).toBe(true);
			expect(result.preimage).toHaveLength(64);
			expect(result.fee).toBe(1);
		});
	});

	describe('simulatePayment', () => {
		it('should settle an invoice', async () => {
			const invoice = await wallet.createInvoice(1000, 'settle test');
			expect(wallet.isSettled(invoice.paymentHash)).toBe(false);

			wallet.simulatePayment(invoice.paymentHash);
			expect(wallet.isSettled(invoice.paymentHash)).toBe(true);
		});

		it('should be a no-op for unknown payment hash', () => {
			expect(() => wallet.simulatePayment('unknown_hash')).not.toThrow();
		});
	});
});
