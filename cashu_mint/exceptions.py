"""Cashu error codes and exception class (NUT-00 error table)."""


class CashuError(Exception):
    """A mint-level error with a NUT error code.

    Usage::

        raise CashuError(10001, "Token is already spent")

    Attributes:
        code:    NUT error code (int)
        detail:  Human-readable message (str)
    """

    def __init__(self, code: int, detail: str = "") -> None:
        self.code = code
        self.detail = detail or _DEFAULT_MESSAGES.get(code, "Unknown error")
        super().__init__(self.detail)

    def __repr__(self) -> str:
        return f"CashuError(code={self.code}, detail={self.detail!r})"


# NUT-00 error codes -------------------------------------------------------
_DEFAULT_MESSAGES: dict[int, str] = {
    10000: "Unknown error",
    10001: "Token is already spent",
    10002: "Token is not verified",
    10003: "Input too large",
    10004: "Output amount too large",
    10005: "Transaction unbalanced",
    10006: "Unit not supported",
    10007: "Keyset not found",
    10008: "Keyset inactive",
    11001: "Lightning payment failed",
    11002: "Quote not paid",
    11003: "Invoice already paid",
    11004: "Quote expired",
    11005: "Quote pending",
    12001: "Spending conditions not met",
}

# Re-export codes as constants for convenience
ERR_UNKNOWN = 10000
ERR_ALREADY_SPENT = 10001
ERR_NOT_VERIFIED = 10002
ERR_INPUT_TOO_LARGE = 10003
ERR_OUTPUT_TOO_LARGE = 10004
ERR_UNBALANCED = 10005
ERR_UNIT_NOT_SUPPORTED = 10006
ERR_KEYSET_NOT_FOUND = 10007
ERR_KEYSET_INACTIVE = 10008
ERR_LN_PAYMENT_FAILED = 11001
ERR_QUOTE_NOT_PAID = 11002
ERR_INVOICE_ALREADY_PAID = 11003
ERR_QUOTE_EXPIRED = 11004
ERR_QUOTE_PENDING = 11005
ERR_SPENDING_CONDITIONS = 12001
