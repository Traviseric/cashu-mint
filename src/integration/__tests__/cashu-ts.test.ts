/**
 * cashu-ts wallet integration tests.
 *
 * Spins up a real Fastify server using FakeWallet and MintService, then drives
 * it through a real cashu-ts Wallet/Mint client. Verifies end-to-end protocol
 * compatibility: mint quote → pay → mint tokens → swap → NUT-07 checkstate.
 *
 * Requires PostgreSQL: `docker compose up -d && npx prisma db push`
 * Run: DATABASE_URL=... npm test
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import Fastify, { type FastifyInstance } from 'fastify';
import { Mint, Wallet, MintQuoteState, MeltQuoteState, CheckStateEnum } from '@cashu/cashu-ts';
import { MintService } from '../../services/mint-service.js';
import { FakeWallet } from '../../lightning/fake-wallet.js';
import { registerRoutes } from '../../routes/index.js';
import { hashToCurveString } from '../../core/crypto/bdhke.js';
import type { MintConfig } from '../../utils/config.js';

const TEST_SEED = 'aabbccddee0011223344556677889900aabbccddee0011223344556677889900';
const TEST_PORT = 13340;
const BASE_URL = `http://localhost:${TEST_PORT}`;

/** Build and start a test Fastify server backed by FakeWallet */
async function buildTestServer(): Promise<{
	fastify: FastifyInstance;
	fakeWallet: FakeWallet;
	mintService: MintService;
}> {
	const config: MintConfig = {
		databaseUrl: process.env.DATABASE_URL ?? 'postgresql://localhost/cashu_test',
		mintPrivateKey: TEST_SEED,
		mintListenPort: TEST_PORT,
		mintUrl: BASE_URL,
		lnBackend: 'FakeWallet',
	};

	const fakeWallet = new FakeWallet();
	const mintService = new MintService(config, fakeWallet);

	const fastify = Fastify({ logger: false });

	fastify.decorate('mintService', mintService);
	await mintService.init();
	await registerRoutes(fastify);

	return { fastify, fakeWallet, mintService };
}

/**
 * Simulate a Lightning invoice being paid via FakeWallet.
 * Decodes the bolt11 to extract the payment hash, triggers the FakeWallet
 * listener, then calls handleInvoiceSettled to update the DB state.
 */
async function simulateInvoicePaid(
	fakeWallet: FakeWallet,
	mintService: MintService,
	bolt11: string,
): Promise<void> {
	const decoded = await fakeWallet.decodePayReq(bolt11);
	fakeWallet.simulatePayment(decoded.paymentHash);
	await mintService.handleInvoiceSettled(decoded.paymentHash);
}

describe.skipIf(!process.env.DATABASE_URL)('cashu-ts wallet integration', () => {
	let fastify: FastifyInstance;
	let fakeWallet: FakeWallet;
	let mintService: MintService;
	let mint: Mint;
	let wallet: Wallet;

	beforeAll(async () => {
		({ fastify, fakeWallet, mintService } = await buildTestServer());
		await fastify.listen({ port: TEST_PORT, host: '127.0.0.1' });

		mint = new Mint(BASE_URL);
		wallet = new Wallet(mint, { unit: 'sat' });
		await wallet.loadMint();
	});

	afterAll(async () => {
		await fastify.close();
	});

	it('should get mint info', async () => {
		const info = await mint.getInfo();
		expect(info.name).toBe('te-btc Cashu Mint');
		expect(info.nuts).toBeDefined();
		expect(info.pubkey).toHaveLength(66);
	});

	it('should get mint keys with correct denominations', async () => {
		const keysResponse = await mint.getKeys();
		expect(keysResponse.keysets).toHaveLength(1);
		const keyset = keysResponse.keysets[0];
		expect(keyset.unit).toBe('sat');
		// 21 power-of-2 denominations: 1, 2, 4, 8, ... 2^20
		expect(Object.keys(keyset.keys)).toHaveLength(21);
	});

	it('should complete a mint flow: request quote → simulate payment → mint tokens', async () => {
		const quote = await wallet.createMintQuoteBolt11(32);
		expect(quote.quote).toBeDefined();
		expect(quote.request).toContain('lnbc');
		expect(quote.state).toBe(MintQuoteState.UNPAID);

		// Simulate LN payment via FakeWallet (no real Lightning needed)
		await simulateInvoicePaid(fakeWallet, mintService, quote.request);

		// Quote should now be PAID
		const updated = await wallet.checkMintQuoteBolt11(quote.quote);
		expect(updated.state).toBe(MintQuoteState.PAID);

		// Mint the tokens — cashu-ts handles blind/unblind internally
		const proofs = await wallet.mintProofsBolt11(32, quote.quote);
		expect(proofs.length).toBeGreaterThan(0);
		expect(proofs.reduce((sum, p) => sum + p.amount, 0)).toBe(32);
	});

	it('should complete a swap (send splits proofs via swap endpoint)', async () => {
		// Mint 16 sats of tokens
		const quote = await wallet.createMintQuoteBolt11(16);
		await simulateInvoicePaid(fakeWallet, mintService, quote.request);
		const proofs = await wallet.mintProofsBolt11(16, quote.quote);

		// Send 8 sats — wallet performs swap: 16-sat inputs → 8 send + 8 keep
		const { send, keep } = await wallet.send(8, proofs);
		expect(send.reduce((sum, p) => sum + p.amount, 0)).toBe(8);
		expect(keep.reduce((sum, p) => sum + p.amount, 0)).toBe(8);
	});

	it('should check proof states via NUT-07', async () => {
		// Mint 8 sats of tokens
		const quote = await wallet.createMintQuoteBolt11(8);
		await simulateInvoicePaid(fakeWallet, mintService, quote.request);
		const proofs = await wallet.mintProofsBolt11(8, quote.quote);

		// Compute Y = hashToCurve(secret) for each proof
		const Ys = proofs.map((p) => hashToCurveString(p.secret));

		const response = await mint.check({ Ys });
		expect(response.states).toHaveLength(proofs.length);
		expect(response.states.every((s) => s.state === 'UNSPENT')).toBe(true);
	});

	it('should mark proof as SPENT after swap', async () => {
		// Mint 4 sats
		const quote = await wallet.createMintQuoteBolt11(4);
		await simulateInvoicePaid(fakeWallet, mintService, quote.request);
		const proofs = await wallet.mintProofsBolt11(4, quote.quote);

		// Record the Y points of the original proofs before swap
		const originalYs = proofs.map((p) => hashToCurveString(p.secret));

		// Swap (send 2, keep 2) — original proofs are spent
		await wallet.send(2, proofs);

		// Original proofs should now be SPENT
		const stateResponse = await mint.check({ Ys: originalYs });
		expect(stateResponse.states.every((s) => s.state === 'SPENT')).toBe(true);
	});

	it('should complete a full melt flow: mint tokens → melt to Lightning', async () => {
		// Step 1: Mint 32 sats of tokens
		const mintQuote = await wallet.createMintQuoteBolt11(32);
		await simulateInvoicePaid(fakeWallet, mintService, mintQuote.request);
		const proofs = await wallet.mintProofsBolt11(32, mintQuote.quote);
		expect(proofs.reduce((sum, p) => sum + p.amount, 0)).toBe(32);

		// Step 2: Create a fake bolt11 to melt into (31 sats).
		// FakeWallet.estimateFee always returns 1 sat, so fee_reserve = 1.
		// 31 (amount) + 1 (fee_reserve) = 32 = exactly our proof balance.
		const meltInvoice = await fakeWallet.createInvoice(31, 'melt integration test');

		// Step 3: Get a melt quote from the mint
		const meltQuote = await wallet.createMeltQuoteBolt11(meltInvoice.bolt11);
		expect(meltQuote.amount).toBe(31);
		expect(meltQuote.fee_reserve).toBe(1);
		expect(meltQuote.state).toBe(MeltQuoteState.UNPAID);

		// Step 4: Execute melt — FakeWallet.sendPayment always succeeds
		const meltResult = await wallet.meltProofsBolt11(meltQuote, proofs);
		expect(meltResult.quote.state).toBe(MeltQuoteState.PAID);

		// Step 5: Verify all input proofs are marked SPENT via NUT-07
		const states = await wallet.checkProofsStates(proofs);
		expect(states).toHaveLength(proofs.length);
		expect(states.every((s) => s.state === CheckStateEnum.SPENT)).toBe(true);
	});
});
