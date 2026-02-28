/** Lightning backend provider interface — abstracts LND, CLN, FakeWallet */

export interface Bolt11Invoice {
	bolt11: string;
	paymentHash: string;
	amount: number; // satoshis
}

export interface DecodedInvoice {
	paymentHash: string;
	amount: number; // satoshis
	description: string;
	expiry: number; // seconds
	timestamp: number; // Unix
}

export interface InvoiceUpdate {
	paymentHash: string;
	settled: boolean;
	amount: number;
}

export interface PaymentResult {
	success: boolean;
	preimage?: string;
	fee?: number; // actual routing fee in sats
	error?: string;
}

/**
 * All Lightning operations go through this interface.
 * Operators can swap implementations (LND, CLN, FakeWallet)
 * without touching core mint logic.
 */
export interface ILightningBackend {
	/** Create a new Lightning invoice */
	createInvoice(amount: number, memo: string): Promise<Bolt11Invoice>;

	/** Subscribe to invoice settlement events */
	subscribeInvoices(): AsyncIterable<InvoiceUpdate>;

	/** Decode a BOLT11 payment request */
	decodePayReq(bolt11: string): Promise<DecodedInvoice>;

	/** Estimate routing fee for a payment */
	estimateFee(bolt11: string): Promise<number>;

	/** Send a Lightning payment */
	sendPayment(bolt11: string, feeLimit: number): Promise<PaymentResult>;
}
