/**
 * FakeWallet — deterministic Lightning backend for testing.
 * No Docker, no LND, no network calls.
 * Fully implements ILightningBackend with predictable responses.
 */

import { randomBytes } from 'node:crypto';
import type {
	Bolt11Invoice,
	DecodedInvoice,
	ILightningBackend,
	InvoiceUpdate,
	PaymentResult,
} from './interface.js';

export class FakeWallet implements ILightningBackend {
	private invoices = new Map<string, { amount: number; memo: string; settled: boolean }>();
	private bolt11Map = new Map<string, string>(); // bolt11 → paymentHash
	private updateListeners: Array<(update: InvoiceUpdate) => void> = [];
	private _shouldFailPayment = false;

	async createInvoice(amount: number, memo: string): Promise<Bolt11Invoice> {
		const paymentHash = randomBytes(32).toString('hex');
		// Fake BOLT11 with identifiable prefix
		const bolt11 = `lnbc${amount}n1fake${paymentHash.slice(0, 20)}`;

		this.invoices.set(paymentHash, { amount, memo, settled: false });
		this.bolt11Map.set(bolt11, paymentHash);

		return { bolt11, paymentHash, amount };
	}

	async *subscribeInvoices(): AsyncIterable<InvoiceUpdate> {
		// Yield updates as they come in via simulatePayment
		const queue: InvoiceUpdate[] = [];
		let resolve: (() => void) | null = null;

		this.updateListeners.push((update) => {
			queue.push(update);
			resolve?.();
		});

		while (true) {
			if (queue.length > 0) {
				yield queue.shift()!;
			} else {
				await new Promise<void>((r) => {
					resolve = r;
				});
			}
		}
	}

	async decodePayReq(bolt11: string): Promise<DecodedInvoice> {
		// Extract amount from fake bolt11 format
		const amountMatch = bolt11.match(/^lnbc(\d+)n1/);
		const amount = amountMatch ? Number.parseInt(amountMatch[1], 10) : 1000;

		// Use stored bolt11→paymentHash mapping for accuracy; fall back to derived hash
		const paymentHash = this.bolt11Map.get(bolt11) ?? bolt11.slice(-20).padEnd(64, '0');

		return {
			paymentHash,
			amount,
			description: 'Fake invoice',
			expiry: 3600,
			timestamp: Math.floor(Date.now() / 1000),
		};
	}

	async estimateFee(_bolt11: string): Promise<number> {
		// Deterministic: always 1 sat fee
		return 1;
	}

	async sendPayment(_bolt11: string, _feeLimit: number): Promise<PaymentResult> {
		if (this._shouldFailPayment) {
			return { success: false, error: 'Payment failed (test)' };
		}
		const preimage = randomBytes(32).toString('hex');
		return {
			success: true,
			preimage,
			fee: 1,
		};
	}

	/** Test helper — control whether sendPayment returns failure */
	setPaymentShouldFail(fail: boolean): void {
		this._shouldFailPayment = fail;
	}

	/**
	 * Test helper — simulate invoice settlement.
	 * Triggers subscribeInvoices() listeners.
	 */
	simulatePayment(paymentHash: string): void {
		const invoice = this.invoices.get(paymentHash);
		if (invoice) {
			invoice.settled = true;
			const update: InvoiceUpdate = {
				paymentHash,
				settled: true,
				amount: invoice.amount,
			};
			for (const listener of this.updateListeners) {
				listener(update);
			}
		}
	}

	/** Test helper — check if an invoice exists */
	hasInvoice(paymentHash: string): boolean {
		return this.invoices.has(paymentHash);
	}

	/** Test helper — check if an invoice is settled */
	isSettled(paymentHash: string): boolean {
		return this.invoices.get(paymentHash)?.settled ?? false;
	}
}
