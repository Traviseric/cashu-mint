/**
 * MintService integration tests.
 * These tests require PostgreSQL (docker compose up -d && npx prisma db push).
 * Run with: npm test -- --testPathPattern=mint-service
 *
 * For unit tests that don't need DB, see the crypto tests.
 */

import { describe, it, expect, beforeAll, beforeEach } from 'vitest';
import { MintService } from '../mint-service.js';
import { FakeWallet } from '../../lightning/fake-wallet.js';
import {
	generateKeysFromSeed,
	deriveKeysetId,
} from '../../core/crypto/keyset.js';
import {
	createTestProof,
	createTestBlindedMessage,
} from '../../core/crypto/__tests__/test-helpers.js';
import type { MintConfig } from '../../utils/config.js';

const TEST_SEED =
	'aabbccddee0011223344556677889900aabbccddee0011223344556677889900';

function createTestConfig(): MintConfig {
	return {
		databaseUrl: process.env.DATABASE_URL ?? 'postgresql://localhost/cashu_test',
		mintPrivateKey: TEST_SEED,
		mintListenPort: 3338,
		mintUrl: 'http://localhost:3338',
		lnBackend: 'FakeWallet',
	};
}

/**
 * These integration tests need a running PostgreSQL.
 * They are skipped if DATABASE_URL is not set.
 */
const itDb = process.env.DATABASE_URL ? it : it.skip;

describe('MintService', () => {
	let service: MintService;
	let wallet: FakeWallet;
	let keysetId: string;
	let privateKeys: Record<string, string>;
	let publicKeys: Record<string, string>;

	beforeAll(() => {
		// Pre-compute keyset for test helpers
		const keys = generateKeysFromSeed(TEST_SEED, 0);
		keysetId = deriveKeysetId(keys.publicKeys);
		privateKeys = keys.privateKeys;
		publicKeys = keys.publicKeys;
	});

	beforeEach(() => {
		wallet = new FakeWallet();
		service = new MintService(createTestConfig(), wallet);
	});

	describe('Unit tests (no DB)', () => {
		it('should return mint info', async () => {
			// getMintInfo doesn't need init() — it uses config directly
			const info = await service.getMintInfo();
			expect(info.name).toBe('te-btc Cashu Mint');
			expect(info.version).toContain('cashu-mint');
			expect(info.pubkey).toHaveLength(66);
			expect(info.nuts).toBeDefined();
			expect(info.nuts['7']).toEqual({ supported: true });
		});
	});

	describe('Integration tests (need DB)', () => {
		beforeEach(async () => {
			if (!process.env.DATABASE_URL) return;
			await service.init();
		});

		itDb('should initialize with active keyset', async () => {
			const keys = await service.getKeys();
			expect(keys.keysets).toHaveLength(1);
			expect(keys.keysets[0].id).toBe(keysetId);
			expect(keys.keysets[0].unit).toBe('sat');
			expect(Object.keys(keys.keysets[0].keys)).toHaveLength(21);
		});

		itDb('should return keyset metadata', async () => {
			const keysets = await service.getKeysets();
			expect(keysets.keysets).toHaveLength(1);
			expect(keysets.keysets[0].active).toBe(true);
		});

		itDb('should return keys by keyset ID', async () => {
			const keys = await service.getKeysByKeysetId(keysetId);
			expect(keys.keysets[0].id).toBe(keysetId);
		});

		itDb('should throw on unknown keyset ID', async () => {
			await expect(
				service.getKeysByKeysetId('00xxxxxxxxxxxxxx'),
			).rejects.toThrow('not found');
		});

		itDb('should create a mint quote', async () => {
			const quote = await service.createMintQuote(100, 'sat');
			expect(quote.quote).toBeDefined();
			expect(quote.request).toContain('lnbc');
			expect(quote.state).toBe('UNPAID');
			expect(quote.expiry).toBeGreaterThan(Math.floor(Date.now() / 1000));
		});

		itDb('full mint flow: quote → pay → mint tokens', async () => {
			// 1. Create quote
			const quote = await service.createMintQuote(8, 'sat');

			// 2. Simulate LN payment
			const paymentHash = quote.request.slice(-20).padEnd(64, '0');
			wallet.simulatePayment(paymentHash);

			// 3. Check quote is now PAID
			const updated = await service.getMintQuote(quote.quote);
			expect(updated.state).toBe('PAID');

			// 4. Create blinded messages for 8 sats (one 8-sat output)
			const { blindedMessage } = createTestBlindedMessage(
				'mint_secret_1',
				8,
				keysetId,
			);

			// 5. Mint tokens
			const result = await service.mintTokens(quote.quote, [
				blindedMessage,
			]);
			expect(result.signatures).toHaveLength(1);
			expect(result.signatures[0].amount).toBe(8);
			expect(result.signatures[0].id).toBe(keysetId);
			expect(result.signatures[0].C_).toHaveLength(66);
		});

		itDb('mint saga recovery: re-mint returns stored sigs', async () => {
			const quote = await service.createMintQuote(4, 'sat');
			const paymentHash = quote.request.slice(-20).padEnd(64, '0');
			wallet.simulatePayment(paymentHash);

			const { blindedMessage } = createTestBlindedMessage(
				'saga_mint_secret',
				4,
				keysetId,
			);

			const result1 = await service.mintTokens(quote.quote, [
				blindedMessage,
			]);

			// Re-submit — should return same sigs (saga recovery)
			const result2 = await service.mintTokens(quote.quote, [
				blindedMessage,
			]);
			expect(result2.signatures).toHaveLength(1);
			expect(result2.signatures[0].C_).toBe(result1.signatures[0].C_);
		});

		itDb('full swap flow: mint → swap', async () => {
			// First mint some tokens
			const quote = await service.createMintQuote(4, 'sat');
			const paymentHash = quote.request.slice(-20).padEnd(64, '0');
			wallet.simulatePayment(paymentHash);

			const { blindedMessage: mintOutput, r: mintR } =
				createTestBlindedMessage('swap_in_secret', 4, keysetId);
			const mintResult = await service.mintTokens(quote.quote, [
				mintOutput,
			]);

			// Unblind the minted token to get a valid proof
			const { secp256k1: secp } = await import(
				'@noble/curves/secp256k1'
			);
			const { bytesToHex: toHex } = await import(
				'@noble/hashes/utils'
			);
			const K = secp.ProjectivePoint.fromHex(publicKeys['4']);
			const rK = K.multiply(BigInt(`0x${mintR}`));
			const C_ = secp.ProjectivePoint.fromHex(
				mintResult.signatures[0].C_,
			);
			const C = C_.subtract(rK);
			const proof = {
				amount: 4,
				secret: 'swap_in_secret',
				C: toHex(C.toRawBytes(true)),
				id: keysetId,
			};

			// Now swap: 4 → 2+2
			const out1 = createTestBlindedMessage(
				'swap_out_secret_1',
				2,
				keysetId,
			);
			const out2 = createTestBlindedMessage(
				'swap_out_secret_2',
				2,
				keysetId,
			);

			const swapResult = await service.swap({
				inputs: [proof],
				outputs: [out1.blindedMessage, out2.blindedMessage],
			});
			expect(swapResult.signatures).toHaveLength(2);
			expect(swapResult.signatures[0].amount).toBe(2);
			expect(swapResult.signatures[1].amount).toBe(2);
		});

		itDb('swap should reject unbalanced amounts', async () => {
			const proof = createTestProof(
				'unbalanced_secret',
				4,
				keysetId,
				privateKeys['4'],
				publicKeys['4'],
			);
			const { blindedMessage } = createTestBlindedMessage(
				'unbalanced_out',
				8,
				keysetId,
			);

			await expect(
				service.swap({
					inputs: [proof.proof],
					outputs: [blindedMessage],
				}),
			).rejects.toThrow('not balanced');
		});

		itDb('swap should reject invalid proof signature', async () => {
			// Create proof with wrong key
			const wrongKeysetKeys = generateKeysFromSeed(
				'1111111111111111111111111111111111111111111111111111111111111111',
				0,
			);
			const proof = createTestProof(
				'wrong_key_secret',
				4,
				keysetId, // claim it's for our keyset
				wrongKeysetKeys.privateKeys['4'], // but use wrong key
				wrongKeysetKeys.publicKeys['4'],
			);
			const { blindedMessage } = createTestBlindedMessage(
				'wrong_key_out',
				4,
				keysetId,
			);

			await expect(
				service.swap({
					inputs: [proof.proof],
					outputs: [blindedMessage],
				}),
			).rejects.toThrow('invalid');
		});

		itDb('checkProofState: unspent before spend', async () => {
			const { hashToCurveString: h2c } = await import(
				'../../core/crypto/bdhke.js'
			);
			const Y = h2c('unspent_check_secret');
			const result = await service.checkProofState([Y]);
			expect(result.states).toHaveLength(1);
			expect(result.states[0].state).toBe('UNSPENT');
		});

		itDb('full melt flow: mint → melt', async () => {
			// 1. Mint tokens
			const mintQuote = await service.createMintQuote(16, 'sat');
			const paymentHash = mintQuote.request.slice(-20).padEnd(64, '0');
			wallet.simulatePayment(paymentHash);

			const { blindedMessage: mintOutput, r: mintR } =
				createTestBlindedMessage('melt_in_secret', 16, keysetId);
			const mintResult = await service.mintTokens(mintQuote.quote, [
				mintOutput,
			]);

			// Unblind
			const { secp256k1: secp } = await import(
				'@noble/curves/secp256k1'
			);
			const { bytesToHex: toHex } = await import(
				'@noble/hashes/utils'
			);
			const K = secp.ProjectivePoint.fromHex(publicKeys['16']);
			const rK = K.multiply(BigInt(`0x${mintR}`));
			const C_ = secp.ProjectivePoint.fromHex(
				mintResult.signatures[0].C_,
			);
			const C = C_.subtract(rK);
			const proof = {
				amount: 16,
				secret: 'melt_in_secret',
				C: toHex(C.toRawBytes(true)),
				id: keysetId,
			};

			// 2. Create melt quote (pay some external invoice)
			const externalInvoice = `lnbc10n1fakeexternal0000000000`;
			const meltQuote = await service.createMeltQuote(
				externalInvoice,
				'sat',
			);
			expect(meltQuote.amount).toBe(10);
			expect(meltQuote.fee_reserve).toBe(1);

			// 3. Create change output (16 - 10 - 1 fee = 5 sats change)
			const { blindedMessage: changeOutput } = createTestBlindedMessage(
				'melt_change_secret',
				5,
				keysetId,
			);

			// 4. Melt
			const meltResult = await service.meltTokens({
				quote: meltQuote.quote,
				inputs: [proof],
				outputs: [changeOutput],
			});

			expect(meltResult.state).toBe('PAID');
			expect(meltResult.payment_preimage).toBeDefined();
			expect(meltResult.change).toHaveLength(1);
			expect(meltResult.change![0].amount).toBe(5);
		});
	});
});
