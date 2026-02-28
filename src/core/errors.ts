/** Base error class for all Cashu mint errors */
export class CashuError extends Error {
	constructor(
		message: string,
		public readonly code: number,
		public readonly detail?: string,
	) {
		super(message);
		this.name = 'CashuError';
	}

	toJSON() {
		return {
			detail: this.detail ?? this.message,
			code: this.code,
		};
	}
}

/** Proof signature verification failed */
export class ProofInvalidError extends CashuError {
	constructor(detail?: string) {
		super('Proof is invalid', 10000, detail);
		this.name = 'ProofInvalidError';
	}
}

/** Token has already been spent (double-spend attempt) */
export class TokenAlreadySpentError extends CashuError {
	constructor(detail?: string) {
		super('Token already spent', 11000, detail);
		this.name = 'TokenAlreadySpentError';
	}
}

/** Input and output amounts do not balance */
export class TransactionNotBalancedError extends CashuError {
	constructor(detail?: string) {
		super('Transaction is not balanced', 11001, detail);
		this.name = 'TransactionNotBalancedError';
	}
}

/** Requested keyset not found */
export class KeysetNotFoundError extends CashuError {
	constructor(detail?: string) {
		super('Keyset not found', 12001, detail);
		this.name = 'KeysetNotFoundError';
	}
}

/** Keyset is inactive (cannot issue new tokens) */
export class KeysetInactiveError extends CashuError {
	constructor(detail?: string) {
		super('Keyset is not active', 12002, detail);
		this.name = 'KeysetInactiveError';
	}
}

/** Denomination not supported in keyset */
export class AmountNotSupportedError extends CashuError {
	constructor(detail?: string) {
		super('Amount not supported', 12003, detail);
		this.name = 'AmountNotSupportedError';
	}
}

/** Quote has not been paid */
export class QuoteNotPaidError extends CashuError {
	constructor(detail?: string) {
		super('Quote not paid', 20001, detail);
		this.name = 'QuoteNotPaidError';
	}
}

/** Quote has expired */
export class QuoteExpiredError extends CashuError {
	constructor(detail?: string) {
		super('Quote expired', 20002, detail);
		this.name = 'QuoteExpiredError';
	}
}

/** Quote not found */
export class QuoteNotFoundError extends CashuError {
	constructor(detail?: string) {
		super('Quote not found', 20003, detail);
		this.name = 'QuoteNotFoundError';
	}
}

/** Tokens already issued for this quote */
export class TokensAlreadyIssuedError extends CashuError {
	constructor(detail?: string) {
		super('Tokens already issued', 20004, detail);
		this.name = 'TokensAlreadyIssuedError';
	}
}

/** Lightning backend error */
export class LightningBackendError extends CashuError {
	constructor(detail?: string) {
		super('Lightning backend error', 30000, detail);
		this.name = 'LightningBackendError';
	}
}

/** Request validation error */
export class ValidationError extends CashuError {
	constructor(detail?: string) {
		super('Validation error', 10001, detail);
		this.name = 'ValidationError';
	}
}
