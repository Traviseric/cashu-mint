/**
 * LND gRPC Lightning backend — production implementation.
 * Authenticates with TLS cert + admin macaroon.
 *
 * Requires:
 * - GRPC_SSL_CIPHER_SUITES='HIGH+ECDSA' env var for TLS compatibility
 * - LND_GRPC_HOST, LND_TLS_CERT_PATH, LND_MACAROON_PATH config
 */

import type {
	Bolt11Invoice,
	DecodedInvoice,
	ILightningBackend,
	InvoiceUpdate,
	PaymentResult,
} from './interface.js';

export interface LndConfig {
	grpcHost: string;
	tlsCertPath: string;
	macaroonPath: string;
}

export class LndBackend implements ILightningBackend {
	constructor(private config: LndConfig) {
		// Set required env var for LND TLS handshake
		process.env.GRPC_SSL_CIPHER_SUITES = 'HIGH+ECDSA';
	}

	async createInvoice(_amount: number, _memo: string): Promise<Bolt11Invoice> {
		throw new Error('LND backend not implemented — Phase 1');
	}

	async *subscribeInvoices(): AsyncIterable<InvoiceUpdate> {
		throw new Error('LND backend not implemented — Phase 1');
	}

	async decodePayReq(_bolt11: string): Promise<DecodedInvoice> {
		throw new Error('LND backend not implemented — Phase 1');
	}

	async estimateFee(_bolt11: string): Promise<number> {
		throw new Error('LND backend not implemented — Phase 1');
	}

	async sendPayment(_bolt11: string, _feeLimit: number): Promise<PaymentResult> {
		throw new Error('LND backend not implemented — Phase 1');
	}
}
