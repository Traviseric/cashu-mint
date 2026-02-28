export type { ILightningBackend, Bolt11Invoice, DecodedInvoice, InvoiceUpdate, PaymentResult } from './interface.js';
export { FakeWallet } from './fake-wallet.js';
export { LndBackend } from './lnd.js';
export type { LndConfig } from './lnd.js';

import type { ILightningBackend } from './interface.js';
import { FakeWallet } from './fake-wallet.js';
import { LndBackend } from './lnd.js';

/** Factory for creating Lightning backend from config */
export function createLightningBackend(
	type: string,
	config?: { grpcHost: string; tlsCertPath: string; macaroonPath: string },
): ILightningBackend {
	switch (type) {
		case 'FakeWallet':
			return new FakeWallet();
		case 'LND': {
			if (!config) throw new Error('LND config required');
			return new LndBackend(config);
		}
		default:
			throw new Error(`Unknown Lightning backend: ${type}`);
	}
}
