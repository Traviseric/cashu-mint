# cashu-mint

A [Cashu](https://cashu.space) ecash protocol mint implementation in Python using FastAPI.

Cashu is a privacy-preserving ecash protocol backed by Bitcoin Lightning. The mint issues and redeems Chaumian blinded ecash tokens.

## Implemented NUTs

| NUT | Name | Status |
|-----|------|--------|
| NUT-00 | Cryptography and Models (BDHKE) | 🔄 In progress |
| NUT-01 | Mint Public Keys | 🔄 In progress |
| NUT-02 | Keysets and Fees | 🔄 In progress |
| NUT-03 | Swapping Tokens | ⏳ Pending |
| NUT-04 | Minting Tokens | ⏳ Pending |
| NUT-05 | Melting Tokens | ⏳ Pending |
| NUT-06 | Mint Info | ⏳ Pending |

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Copy and configure environment
cp .env.example .env

# Run the mint
cashu-mint
# or
uvicorn cashu_mint.main:app --reload
```

## Development

```bash
# Run tests
pytest

# Lint
ruff check .

# Format
ruff format .

# Type check
mypy cashu_mint/
```

## References

- [Cashu Protocol Specs (NUTs)](https://cashubtc.github.io/nuts/)
- [Nutshell reference implementation](https://github.com/cashubtc/nutshell)
