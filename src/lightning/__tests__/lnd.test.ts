/**
 * LndBackend unit tests — all gRPC calls mocked, no real LND required.
 *
 * Uses vi.hoisted + vi.mock to intercept grpc-js, proto-loader, and fs
 * before any module is imported, injecting a mock LndClient into LndBackend.
 */

import { vi, describe, it, expect, beforeEach } from 'vitest';
import { LightningBackendError } from '../../core/errors.js';

// ── Mock setup (hoisted so factories can reference mockClient) ────────────────

const { mockClient } = vi.hoisted(() => {
	const mockClient = {
		AddInvoice: vi.fn(),
		DecodePayReq: vi.fn(),
		EstimateRouteFee: vi.fn(),
		SendPaymentSync: vi.fn(),
		SubscribeInvoices: vi.fn(),
	};
	return { mockClient };
});

vi.mock('node:fs', () => ({
	readFileSync: vi.fn(() => Buffer.from('fake-data')),
}));

vi.mock('@grpc/proto-loader', () => ({
	loadSync: vi.fn(() => ({})),
}));

vi.mock('@grpc/grpc-js', () => ({
	loadPackageDefinition: vi.fn(() => ({
		lnrpc: { Lightning: vi.fn(() => mockClient) },
	})),
	credentials: {
		createSsl: vi.fn(() => ({})),
		createFromMetadataGenerator: vi.fn((_fn: unknown) => ({})),
		combineChannelCredentials: vi.fn(() => ({})),
	},
	Metadata: vi.fn(() => ({ add: vi.fn() })),
}));

// Import after mocks are registered
import { LndBackend } from '../lnd.js';

// ── Helpers ───────────────────────────────────────────────────────────────────

const TEST_CONFIG = {
	grpcHost: 'localhost:10009',
	tlsCertPath: '/fake/tls.cert',
	macaroonPath: '/fake/admin.macaroon',
};

/** Build a DecodePayReq response for a given amount and destination hex */
function decodePayReqResponse(
	amountSats: number,
	destination = 'deadbeef',
): {
	destination: string;
	payment_hash: string;
	num_satoshis: string;
	description: string;
	expiry: string;
	timestamp: string;
} {
	return {
		destination,
		payment_hash: 'aaaa'.repeat(16),
		num_satoshis: String(amountSats),
		description: 'test invoice',
		expiry: '3600',
		timestamp: '1700000000',
	};
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('LndBackend', () => {
	let backend: LndBackend;

	beforeEach(() => {
		vi.clearAllMocks();
		backend = new LndBackend(TEST_CONFIG);
	});

	// ── estimateFee ────────────────────────────────────────────────────────────

	describe('estimateFee', () => {
		it('should return ceiling of routing_fee_msat / 1000 on success', async () => {
			mockClient.DecodePayReq.mockImplementation(
				(_req: unknown, cb: (err: null, res: ReturnType<typeof decodePayReqResponse>) => void) => {
					cb(null, decodePayReqResponse(1000));
				},
			);
			mockClient.EstimateRouteFee.mockImplementation(
				(_req: unknown, cb: (err: null, res: { routing_fee_msat: string }) => void) => {
					cb(null, { routing_fee_msat: '10000' }); // 10 sats
				},
			);

			const fee = await backend.estimateFee('lnbcfakeinvoice');
			expect(fee).toBe(10); // ceil(10000 / 1000)
		});

		it('should round up fractional sats (ceil)', async () => {
			mockClient.DecodePayReq.mockImplementation(
				(_req: unknown, cb: (err: null, res: ReturnType<typeof decodePayReqResponse>) => void) => {
					cb(null, decodePayReqResponse(500));
				},
			);
			mockClient.EstimateRouteFee.mockImplementation(
				(_req: unknown, cb: (err: null, res: { routing_fee_msat: string }) => void) => {
					cb(null, { routing_fee_msat: '1500' }); // 1.5 sats → ceil = 2
				},
			);

			const fee = await backend.estimateFee('lnbcfakeinvoice');
			expect(fee).toBe(2);
		});

		it('should fall back to 1% + 1 sat when EstimateRouteFee fails', async () => {
			mockClient.DecodePayReq.mockImplementation(
				(_req: unknown, cb: (err: null, res: ReturnType<typeof decodePayReqResponse>) => void) => {
					cb(null, decodePayReqResponse(1000));
				},
			);
			mockClient.EstimateRouteFee.mockImplementation(
				(_req: unknown, cb: (err: Error, res: null) => void) => {
					cb(new Error('no route'), null);
				},
			);

			const fee = await backend.estimateFee('lnbcfakeinvoice');
			// fallback: Math.max(Math.ceil(1000 * 0.01), 1) = 10
			expect(fee).toBe(10);
		});

		it('should return minimum 1 sat when 1% rounds to zero', async () => {
			mockClient.DecodePayReq.mockImplementation(
				(_req: unknown, cb: (err: null, res: ReturnType<typeof decodePayReqResponse>) => void) => {
					cb(null, decodePayReqResponse(50)); // 1% of 50 = 0.5, ceil = 1
				},
			);
			mockClient.EstimateRouteFee.mockImplementation(
				(_req: unknown, cb: (err: Error, res: null) => void) => {
					cb(new Error('rpc unavailable'), null);
				},
			);

			const fee = await backend.estimateFee('lnbcfakeinvoice');
			// Math.max(Math.ceil(50 * 0.01), 1) = Math.max(1, 1) = 1
			expect(fee).toBe(1);
		});

		it('should reject with LightningBackendError when DecodePayReq fails', async () => {
			mockClient.DecodePayReq.mockImplementation(
				(_req: unknown, cb: (err: Error, res: null) => void) => {
					cb(new Error('connection refused'), null);
				},
			);

			await expect(backend.estimateFee('lnbcfakeinvoice')).rejects.toThrow(
				LightningBackendError,
			);
		});
	});

	// ── sendPayment ────────────────────────────────────────────────────────────

	describe('sendPayment', () => {
		it('should return success with fee extracted from payment_route', async () => {
			const fakePreimage = Buffer.from('preimage_bytes_here_32b!!!!!!!!', 'utf8');
			mockClient.SendPaymentSync.mockImplementation(
				(
					_req: unknown,
					cb: (
						err: null,
						res: {
							payment_error: string;
							payment_preimage: Buffer;
							payment_route: { total_fees_msat: string };
						},
					) => void,
				) => {
					cb(null, {
						payment_error: '',
						payment_preimage: fakePreimage,
						payment_route: { total_fees_msat: '5000' }, // 5 sats
					});
				},
			);

			const result = await backend.sendPayment('lnbcfakeinvoice', 10);
			expect(result.success).toBe(true);
			expect(result.fee).toBe(5); // ceil(5000 / 1000)
			expect(result.preimage).toBe(fakePreimage.toString('hex'));
		});

		it('should return success with fee=0 when payment_route is absent', async () => {
			const fakePreimage = Buffer.alloc(32, 0xab);
			mockClient.SendPaymentSync.mockImplementation(
				(
					_req: unknown,
					cb: (
						err: null,
						res: { payment_error: string; payment_preimage: Buffer; payment_route?: undefined },
					) => void,
				) => {
					cb(null, {
						payment_error: '',
						payment_preimage: fakePreimage,
					});
				},
			);

			const result = await backend.sendPayment('lnbcfakeinvoice', 10);
			expect(result.success).toBe(true);
			expect(result.fee).toBe(0);
		});

		it('should return failure when payment_error is non-empty', async () => {
			mockClient.SendPaymentSync.mockImplementation(
				(
					_req: unknown,
					cb: (
						err: null,
						res: { payment_error: string; payment_preimage: Buffer },
					) => void,
				) => {
					cb(null, {
						payment_error: 'no_route',
						payment_preimage: Buffer.alloc(0),
					});
				},
			);

			const result = await backend.sendPayment('lnbcfakeinvoice', 10);
			expect(result.success).toBe(false);
			expect(result.error).toBe('no_route');
		});

		it('should reject with LightningBackendError on gRPC error', async () => {
			mockClient.SendPaymentSync.mockImplementation(
				(_req: unknown, cb: (err: Error, res: null) => void) => {
					cb(new Error('stream closed'), null);
				},
			);

			await expect(backend.sendPayment('lnbcfakeinvoice', 10)).rejects.toThrow(
				LightningBackendError,
			);
		});
	});

	// ── createInvoice ──────────────────────────────────────────────────────────

	describe('createInvoice', () => {
		it('should resolve with bolt11 and payment hash', async () => {
			const fakeHash = Buffer.from('fakehashbytes12345678901234567890', 'utf8').slice(0, 32);
			mockClient.AddInvoice.mockImplementation(
				(
					_req: unknown,
					cb: (
						err: null,
						res: { r_hash: Buffer; payment_request: string },
					) => void,
				) => {
					cb(null, {
						r_hash: fakeHash,
						payment_request: 'lnbc1000n1realinvoice',
					});
				},
			);

			const invoice = await backend.createInvoice(1000, 'test memo');
			expect(invoice.bolt11).toBe('lnbc1000n1realinvoice');
			expect(invoice.amount).toBe(1000);
			expect(invoice.paymentHash).toBe(fakeHash.toString('hex'));
		});

		it('should reject with LightningBackendError on gRPC error', async () => {
			mockClient.AddInvoice.mockImplementation(
				(_req: unknown, cb: (err: Error, res: null) => void) => {
					cb(new Error('wallet locked'), null);
				},
			);

			await expect(backend.createInvoice(500, 'memo')).rejects.toThrow(LightningBackendError);
		});
	});

	// ── decodePayReq ───────────────────────────────────────────────────────────

	describe('decodePayReq', () => {
		it('should resolve with decoded invoice fields', async () => {
			mockClient.DecodePayReq.mockImplementation(
				(_req: unknown, cb: (err: null, res: ReturnType<typeof decodePayReqResponse>) => void) => {
					cb(null, decodePayReqResponse(2000));
				},
			);

			const decoded = await backend.decodePayReq('lnbcfakeinvoice');
			expect(decoded.amount).toBe(2000);
			expect(decoded.paymentHash).toBe('aaaa'.repeat(16));
			expect(decoded.description).toBe('test invoice');
			expect(decoded.expiry).toBe(3600);
			expect(decoded.timestamp).toBe(1700000000);
		});

		it('should reject with LightningBackendError on gRPC error', async () => {
			mockClient.DecodePayReq.mockImplementation(
				(_req: unknown, cb: (err: Error, res: null) => void) => {
					cb(new Error('invalid invoice'), null);
				},
			);

			await expect(backend.decodePayReq('badinvoice')).rejects.toThrow(LightningBackendError);
		});
	});
});
