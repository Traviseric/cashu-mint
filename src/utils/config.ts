/** Environment config loader with Zod validation — fails fast on missing vars */

import { z } from 'zod';

const ConfigSchema = z.object({
	databaseUrl: z.string().url(),
	mintPrivateKey: z.string().min(64).max(64),
	mintListenPort: z.coerce.number().int().default(3338),
	mintUrl: z.string().url().default('http://localhost:3338'),
	lnBackend: z.enum(['FakeWallet', 'LND']).default('FakeWallet'),
	lndGrpcHost: z.string().optional(),
	lndTlsCertPath: z.string().optional(),
	lndMacaroonPath: z.string().optional(),
});

export type MintConfig = z.infer<typeof ConfigSchema>;

/** Load and validate config from environment variables */
export function loadConfig(): MintConfig {
	const result = ConfigSchema.safeParse({
		databaseUrl: process.env.DATABASE_URL,
		mintPrivateKey: process.env.MINT_PRIVATE_KEY,
		mintListenPort: process.env.MINT_LISTEN_PORT,
		mintUrl: process.env.MINT_URL,
		lnBackend: process.env.LN_BACKEND,
		lndGrpcHost: process.env.LND_GRPC_HOST,
		lndTlsCertPath: process.env.LND_TLS_CERT_PATH,
		lndMacaroonPath: process.env.LND_MACAROON_PATH,
	});

	if (!result.success) {
		const errors = result.error.issues
			.map((i) => `  ${i.path.join('.')}: ${i.message}`)
			.join('\n');
		throw new Error(`Invalid configuration:\n${errors}`);
	}

	const config = result.data;

	// Validate LND config when LND backend is selected
	if (config.lnBackend === 'LND') {
		if (!config.lndGrpcHost || !config.lndTlsCertPath || !config.lndMacaroonPath) {
			throw new Error('LND backend requires LND_GRPC_HOST, LND_TLS_CERT_PATH, and LND_MACAROON_PATH');
		}
	}

	return config;
}
