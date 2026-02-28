import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import Fastify, { type FastifyInstance } from 'fastify';
import { registerRoutes } from '../index.js';
import { MintService } from '../../services/mint-service.js';
import { FakeWallet } from '../../lightning/fake-wallet.js';
import type { MintConfig } from '../../utils/config.js';

describe('Health endpoint', () => {
	let fastify: FastifyInstance;

	beforeAll(async () => {
		fastify = Fastify();

		const config: MintConfig = {
			databaseUrl: 'postgresql://test:test@localhost:5432/test',
			mintPrivateKey: '0000000000000000000000000000000000000000000000000000000000000001',
			mintListenPort: 0, // random port
			mintUrl: 'http://localhost:3339',
			lnBackend: 'FakeWallet',
		};

		const lightning = new FakeWallet();
		const mintService = new MintService(config, lightning);
		fastify.decorate('mintService', mintService);

		await registerRoutes(fastify);
		await fastify.ready();
	});

	afterAll(async () => {
		await fastify.close();
	});

	it('GET /health returns 200 with status ok', async () => {
		const response = await fastify.inject({
			method: 'GET',
			url: '/health',
		});

		expect(response.statusCode).toBe(200);
		expect(response.json()).toEqual({ status: 'ok' });
	});
});
