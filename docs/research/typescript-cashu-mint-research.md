# **Architectural Specification and Ecosystem Analysis: Engineering a Native TypeScript Cashu Mint**

## **Executive Summary**

The proliferation of Chaumian ecash protocols on the Bitcoin network has established Cashu as a dominant standard for privacy-preserving, scalable, and interoperable transactions. The Cashu ecosystem currently relies heavily on Python and Rust implementations for its core minting infrastructure. The absence of a production-grade, standalone TypeScript/Node.js Cashu mint represents a critical infrastructure gap, particularly for web-native platforms operating in Next.js, Node.js microservices, or serverless environments.

This comprehensive analysis provides an exhaustive architectural blueprint for constructing a native TypeScript Cashu mint. The research evaluates the precise operational state of existing mint implementations, provides a meticulous breakdown of mandatory and optional Cashu Notation, Usage, and Terminology (NUT) specifications, and outlines rigorous cryptographic implementation requirements. Furthermore, it details advanced double-spend prevention architectures using distributed database patterns, strategies for Lightning Network backend integration via gRPC, and security paradigms necessary for deploying financial infrastructure. By synthesizing these elements, the following document serves as the definitive technical specification for engineering a secure, high-performance TypeScript mint designed to anchor Bitcoin circular economies.

## ---

**1\. The Cashu Implementation Ecosystem in 2026**

The ecosystem of Cashu mints has matured significantly, transitioning from experimental cryptographic prototypes into robust, high-liquidity financial infrastructure. Understanding the exact maturity, feature set, and architectural paradigms of existing implementations is essential for successfully positioning a new TypeScript mint within the broader open-source landscape.

### **Analysis of Existing Mint Implementations**

The current environment is dominated by two primary implementations, with a third serving a specific monolithic niche, alongside a few emerging experimental projects.

| Implementation | Primary Language | Version (Feb 2026\) | Architecture & Maturity | Strategic Niche & Limitations |
| :---- | :---- | :---- | :---- | :---- |
| **Nutshell** (cashubtc/nutshell) | Python | v0.19.2 | Highly mature reference implementation utilizing FastAPI and asyncio.1 | Serves as the primary testing ground for new NUT specifications. While feature-complete (supporting P2PK, DLEQ, and WebSockets), Python's Global Interpreter Lock (GIL) and dynamic typing present theoretical upper bounds on absolute concurrent throughput in massive-scale deployments.2 |
| **CDK Mint** (cdk-mintd) | Rust | v0.15.0 | Production-ready, highly modular crate structure utilizing Axum and Tokio.3 | Unmatched in performance due to Rust's memory safety and fearless concurrency. Version 0.15.0 introduced the "Saga Pattern" for robust crash recovery.4 Supports SQLite, PostgreSQL, and Redb.5 |
| **Moksha** (ngutech21/moksha) | Rust | Active | Monolithic binary containing both wallet and mint functionalities.6 | Actively maintained but appeals to users desiring an all-in-one executable rather than a highly decoupled cloud-native microservice. It often lags slightly behind Nutshell in adopting experimental edge-case NUTs.6 |
| **Unit Mint** (DUCAT-UNIT) | TypeScript | Experimental | Early-stage implementation utilizing Bitcoin Runes.7 | A specialized, experimental mint designed specifically for collateralized debt position (CDP) stablecoins backed by Bitcoin Runes, rather than a generalized Lightning-backed Cashu mint.7 |

### **The TypeScript and Node.js Gap**

While TypeScript completely dominates the Cashu wallet landscape, there remains zero generalized, production-ready TypeScript mint implementation for the Lightning Network.

* **Wallet Libraries (cashu-ts and coco):** The cashu-ts package (currently at v3.4.1) is an exceptionally mature, widely-used TypeScript library.8 However, it is strictly client-side, designed for parsing tokens, managing wallet events, and constructing network requests.9 It contains no server-side lifecycle logic, database schema management, or secret validation protocols. The coco toolkit builds upon cashu-ts to provide unified wallet state management across React Native and web, but again, remains strictly client-focused.10  
* **Cryptographic Primitives (@cashu/crypto):** The cashu-crypto-ts package (v0.3.4), maintained by core developers including robwoodgate, gandlaf21, callebtc, and egge21m, provides basic crypto operations.12 While it contains the underlying math for the Blind Diffie-Hellman Key Exchange (BDHKE), it functions as a low-level primitive wrapper rather than a comprehensive server framework capable of handling HTTP requests or database transactions.12  
* **Custodial Bridges (npubcash-server):** This is a Node.js/TypeScript application acting as a specialized LNURL service.13 It is a custodial bridge that receives Lightning payments and generates Cashu tokens on behalf of offline users via existing mints; it is a client to a mint, not a mint itself.13  
* **Current Web Integrations (orchard):** Management dashboards like orchard (which monitors mints) achieve integration by wrapping the Python-based nutshell or Rust-based cdk within Docker containers and communicating via Inter-Process Communication (IPC) or network requests.14

The strategic opportunity is massive. A native TypeScript mint enables seamless, in-process embedding within Next.js applications, Express/Fastify microservices, or Edge environments. This eliminates complex Docker orchestration, reduces infrastructure overhead, and unifies the tech stack for JavaScript-heavy development teams building Bitcoin circular economies.

## ---

**2\. NUT Specification Deep Dive**

To construct a conformant mint, the architecture must strictly adhere to the Cashu Notation, Usage, and Terminology (NUT) specifications. The protocol is defined by mandatory specifications that guarantee baseline interoperability, and optional specifications that provide advanced cryptographic and user-experience enhancements.15

### **Mandatory Specifications (NUT-00 to NUT-06)**

These core operations dictate the fundamental lifecycle of ecash creation, transaction, and destruction.

* **NUT-00 (Cryptography and Models):** Defines the core entities (Mint, User) and the BDHKE blind signature scheme. The mint is responsible for maintaining scalar private keys, deriving public keys on the secp256k1 curve, receiving blinded messages (![][image1]), and returning blinded signatures (![][image2]).17  
* **NUT-01 (Mint Public Keys):** Dictates the /v1/keys endpoint. The mint must publish its active public keys associated with specific denominations.16 This requires a robust key rotation strategy; when a keyset is rotated, the mint must gracefully transition older keys to an "inactive" state, allowing users to spend old tokens while restricting the issuance of new tokens to the active keyset.2  
* **NUT-02 (Keysets and Fees):** Groups public keys into versioned "keysets," mathematically derived using a hash of the public keys. Keyset IDs allow wallets to identify which mint and which epoch a token belongs to. The mint must maintain a relational mapping of all historical keysets.2  
* **NUT-03 (Swapping Tokens):** The central ecash operation exposed at /v1/swap. The mint receives unblinded signatures (spent proofs) from the user. It must verify the signatures, check the database to ensure the proofs have not been previously spent, and if valid, atomically mark them as spent and return new blinded signatures.16  
* **NUT-04 (Minting Tokens):** The external value ingress mechanism (/v1/mint/quote/bolt11). The mint generates a Lightning invoice, tracks its state through a state machine (pending, paid, expired), and upon detecting payment settlement, signs the user's provided blinded messages to issue new ecash.16  
* **NUT-05 (Melting Tokens):** The external value egress mechanism (/v1/melt/quote/bolt11). The user provides a Lightning invoice to be paid by the mint. The mint estimates network routing fees, holds the user's ecash proofs in a pending/reserved state, attempts the Lightning payment, and permanently destructs the ecash upon success, or un-reserves it upon failure.2  
* **NUT-06 (Mint Info):** Exposes metadata at /v1/info, returning a JSON payload detailing supported NUTs, mint versioning, contact information, and the mint operator's public keys.16

### **High-Priority Optional Specifications**

For a modern 2026 production deployment, several "optional" NUTs are practically mandated by user expectations for security and performance.

| NUT | Feature | Architectural Implication for the Mint |
| :---- | :---- | :---- |
| **07** | Token State Check | Allows wallets to poll the /v1/check endpoint to verify if specific proofs remain unspent. This is vital for multi-device wallet synchronization and backup restoration.15 |
| **08** | Lightning Fee Return | During a melt (NUT-05), the mint reserves a maximum estimated routing fee. If the actual Lightning fee is lower, the mint must sign blank blinded messages provided by the user to return the exact "change" in ecash.15 |
| **10 & 11** | Spending Conditions (P2PK) | Allows tokens to be locked to a specific Schnorr public key. During redemption, the mint must parse a complex JSON secret, extract the public key, and verify a cryptographic Schnorr signature provided in the witness payload.19 |
| **12** | DLEQ Proofs | Discrete Log Equality proofs allow a user to verify the mint did not use a unique, tracking key for a specific token. The mint must compute and attach this mathematical proof to every returned signature.20 |
| **14** | HTLCs | Hashed Timelock Contracts enable atomic cross-mint swaps. The mint must validate that the user has provided the correct preimage to a hash lock before allowing the token to be spent.15 |
| **17** | WebSocket Subscriptions | Replaces inefficient HTTP polling. The mint must maintain stateful WebSocket connections, pushing real-time updates when an invoice transitions to a paid state or when a token state changes.15 |
| **21 & 22** | Authentication | Clear and Blind authentication. Allows the mint to restrict access to authenticated users via OpenID Connect (e.g., Keycloak), creating closed-loop or compliance-focused circular economies.1 |

### **Conformance and Testing**

There is no standalone, automated CI conformance tool strictly for mints. Instead, implementation correctness is verified by running the mint backend against the exhaustive test suites within the cashu-ts repository, and by establishing interoperability with the Nutshell client CLI. Furthermore, testing against testnut.cashu.space (a known-good reference environment) validates edge-case handling.22

## ---

**3\. Cryptographic Implementation Guide**

The Cashu protocol's security guarantees rest entirely on the secp256k1 elliptic curve. A TypeScript mint requires highly optimized, strictly audited cryptographic primitives to execute the BDHKE accurately.

### **The BDHKE Mathematical Flow**

The mint executes a variant of David Wagner's blind signature scheme. The mathematical flow requires absolute precision to prevent token forgery.17

1. **Mint Setup:** The mint generates a private scalar ![][image3] for each denomination in a keyset. It publishes the corresponding public key ![][image4], where ![][image5] is the generator point of the secp256k1 curve.17  
2. **User Blinding:** The user generates a high-entropy random secret ![][image6] and maps it deterministically to the curve to create point ![][image7]. This mapping uses the function ![][image8]. The user then generates a random scalar blinding factor ![][image9] and computes the blinded message: ![][image10]. This ![][image1] is sent to the mint.17  
3. **Mint Signing:** The mint receives ![][image1]. Because of the blinding factor, the mint cannot derive ![][image7] or ![][image6]. The mint multiplies ![][image1] by its private key ![][image3] to create the blinded signature: ![][image11]. The mint returns ![][image2].17  
4. **User Unblinding:** The user receives ![][image2] and removes the blinding factor by subtracting ![][image12]: ![][image13].  
   * *Proof:* Since ![][image14], and ![][image15], the operation ![][image16] isolates ![][image17]. Therefore, ![][image18].17  
5. **Mint Verification:** During a swap or melt, the user presents the plaintext secret ![][image6] and the unblinded signature ![][image19]. The mint computes ![][image8] and verifies that ![][image20]. If the equation holds, the token is mathematically proven to have been signed by the mint.17

### **Discrete Log Equality (DLEQ) Proofs (NUT-12)**

To prevent "secret tagging"—where a malicious mint uses a unique ![][image3] for a specific user to track their transactions—the mint must prove it used the publicly advertised key ![][image21] to generate ![][image2].

The mint generates a random nonce ![][image9]. It computes two curve points: ![][image22] and ![][image23]. It then generates a deterministic challenge scalar $e \= \\text{SHA256}(R\_1 |

| R\_2 | | K | | C\_)$. Finally, it calculates the response scalar ![][image24]. The mint returns the tuple ![][image25] alongside ![][image2], allowing the user to verify the proof locally.20

### **TypeScript Library Dependencies and Pitfalls**

Native Node.js crypto modules are insufficient as they do not expose the raw elliptic curve point addition and scalar multiplication required for BDHKE.

* **@noble/curves (v1.x+):** This is the gold standard for audited, pure-TypeScript elliptic curve operations.9 It provides the secp256k1 objects, ProjectivePoint math (essential for the ![][image1] and ![][image2] calculations), and the Schnorr signature verification required for NUT-11 P2PK spending conditions.19  
* **@noble/hashes:** Required for SHA-256 operations, specifically for the hash\_to\_curve domain separator derivations.  
* **@cashu/crypto:** While this package implements basic BDHKE logic, relying entirely on it for the mint backend may introduce performance bottlenecks. A high-throughput production mint should ideally interface directly with @noble/curves to optimize memory allocation and enable batch signature parallelization.12

**Implementation Gotchas:**

1. **Endianness and Serialization:** Secp256k1 points must be serialized into compressed 33-byte hex strings. Mixing native JavaScript Number types with BigInt during scalar arithmetic will result in precision loss and invalid signatures. Strict typing of scalars as bigint is mandatory.  
2. **hash\_to\_curve Constraints:** The Cashu specification mandates a specific domain separator (Secp256k1\_HashToCurve\_Cashu\_). Furthermore, it requires appending an incrementing uint32 counter (formatted in little-endian byte order) to the hash payload until a valid ![][image6]\-coordinate on the curve is discovered.17 Failing to format this counter exactly will result in incompatible tokens.  
3. **Key Derivation:** Mint private keys must be generated deterministically from a master seed. The standard BIP-32 path convention for deriving keyset keys involves using the keyset ID as an index, ensuring that recovering the master seed recovers all historical denominations across all epochs.

## ---

**4\. Double-Spend Prevention and Database Architecture**

The paramount correctness requirement of a Cashu mint is ensuring a secret ![][image6] is never redeemed twice. A compromised database or an unhandled race condition leads to infinite, unbacked inflation of ecash.

### **Atomicity and Concurrency Risks**

Node.js operates on an asynchronous event loop. In a high-throughput environment, concurrent HTTP requests could attempt to swap the exact same Proof simultaneously. If the database lacks strict transactional boundaries, both requests might query the database, find the token unspent, and simultaneously issue new tokens, effectively duplicating the bearer asset.

To mitigate this, the database must enforce ACID properties, specifically prioritizing the SERIALIZABLE isolation level, or rely on strict UNIQUE constraints that trigger rollback on duplicate insertions.25

### **Database Selection: PostgreSQL vs. SQLite**

For a native TypeScript mint handling production loads, **PostgreSQL is strictly required**.1

* **SQLite** is heavily utilized in local testing or desktop wallets (like cdk-cli), but its concurrent write model locks the entire database file (even in WAL mode), creating massive bottlenecks during simultaneous swaps.26  
* **PostgreSQL** handles high-concurrency row-level locking elegantly. Utilizing a type-safe ORM like Prisma or Drizzle alongside Postgres allows for robust, atomic transaction typing.

### **Proposed Database Schema**

The database must track the state of proofs, the metadata of keysets, and the lifecycle of Lightning quotes. Drawing from cdk-mintd and nutshell paradigms 1, the core tables include:

1. **Keyset Table:**  
   * id (String, Primary Key) \- The derived Base64 ID.  
   * active (Boolean) \- Indicates if it can sign new tokens.  
   * unit (String) \- Represents the asset type (e.g., sat, msat, usd).  
2. **SpentProof Table (The Core Ledger):**  
   * secret (String, Primary Key) \- The plaintext secret ![][image6]. Must possess a UNIQUE index to enforce double-spend prevention at the database engine level.  
   * amount (Integer)  
   * keyset\_id (String, Foreign Key)  
   * witness (JSON) \- Stores P2PK signatures or HTLC preimages.19  
3. **PendingQuote Table:**  
   * id (String, Primary Key)  
   * request (String) \- The BOLT11 invoice.  
   * state (Enum) \- Maps to UNPAID, PAID, PENDING, or EXPIRED.  
   * type (Enum) \- MINT or MELT.  
4. **BlindSignature Table (Optional but recommended):**  
   * Tracks all issued ![][image2] values. This is critical for generating Merkle Sum Sparse Merkle Trees (MSSMT), allowing the mint to cryptographically prove its liabilities to users for auditing purposes.27

### **The Saga Pattern and Crash Recovery**

A critical architectural leap introduced in cdk-mintd v0.15.0 is the implementation of "Wallet Sagas" for all operations.4 A TypeScript mint must replicate this pattern to achieve crash resilience.

Consider a scenario where the Node.js process crashes immediately after writing the SpentProof to the database, but before the HTTP response delivers the newly generated blinded signatures. The user's tokens are burned, but they received nothing in return.

**Resolution:** The database transaction must atomically write the SpentProof alongside a corresponding IssuedPromise record detailing the generated ![][image2] values. If a client connection drops, the client can query the /v1/swap/state endpoint, or idempotently resubmit the exact same blinded messages (![][image1]). The mint observes that the secret is already spent, retrieves the exact ![][image1] payloads from the request, matches them against the stored IssuedPromise, and returns the already-generated ![][image2] values rather than throwing a double-spend error.

### **Sizing and Pruning Strategies**

Tokens are tiny (\~65 bytes) 28, but a high-volume mint processing millions of microtransactions will experience linear growth in the SpentProof table. To manage this, mints utilize Keyset rotation (NUT-02).2 Once an older keyset is entirely deprecated and users are forced to migrate their funds to a newly active keyset, the mint can archive and prune SpentProof records belonging to the defunct keyset, ensuring long-term query performance.

## ---

**5\. Lightning Backend Integration**

A Cashu mint functions as an abstracted custodian of Lightning Network liquidity. The seamless interaction between the TypeScript mint logic and the Lightning node is facilitated by backend providers.

### **Integrating LND via gRPC**

LND remains the most prevalent Lightning implementation. A native TypeScript mint interacts with LND optimally via gRPC using the @grpc/grpc-js and @grpc/proto-loader packages.29

**Connection Mechanics:** Authenticating with an LND node requires passing its TLS certificate and an administrative Macaroon. In Node.js, the Macaroon must be read from the filesystem, converted to a hexadecimal string, and injected as gRPC Call Metadata.29 The connection logic must combine the SSL credentials with the metadata generator:

JavaScript

let metadata \= new grpc.Metadata();  
metadata.add('macaroon', macaroonHex);  
let macaroonCreds \= grpc.credentials.createFromMetadataGenerator((args, callback) \=\> {  
    callback(null, metadata);  
});  
let credentials \= grpc.credentials.combineChannelCredentials(sslCreds, macaroonCreds);

Crucially, the environment variable GRPC\_SSL\_CIPHER\_SUITES='HIGH+ECDSA' must be explicitly set to ensure TLS handshake compatibility with newer LND versions.30

**Required LND RPCs:**

* **Minting (NUT-04):** The mint calls AddInvoice to generate a BOLT11 string. Instead of polling, the mint maintains a persistent SubscribeInvoices stream to detect state changes instantly, triggering WebSocket updates to the client.30  
* **Melting (NUT-05):** The mint calls DecodePayReq to validate the user's requested invoice. It calls EstimateFee to calculate the maximum routing fee, reserving those ecash proofs. Finally, it executes SendPaymentV2 to route the payment, definitively burning the proofs upon a successful preimage return.16  
* **Hold Invoices:** For advanced atomic workflows—such as interacting with external L402 proxies like Aperture—the mint issues a hold invoice. The mint only releases the cryptographic preimage when the corresponding ecash state is irrevocably finalized.

### **REST vs. gRPC Tradeoffs**

While LND offers a REST API, gRPC is strictly recommended for a production mint. gRPC supports persistent bidirectional streaming, which is essential for pushing instant WebSocket notifications (NUT-17) to the client when an invoice is settled.30 Relying on REST would necessitate inefficient, resource-heavy short-polling algorithms.

### **Abstracting the Backend Provider**

To maintain parity with the flexibility of Nutshell and CDK, the TypeScript mint should utilize a Provider Interface pattern (e.g., ILightningBackend).5 This abstraction ensures that operators can easily swap LND for Core Lightning (CLN) via clightning-client, LDK Node, or even cloud-hosted infrastructure like LNbits or Strike without rewriting the core minting state machines.5

## ---

**6\. Architecture Recommendations**

Constructing a greenfield TypeScript Cashu mint offers the opportunity to employ modern architectural patterns that bypass the legacy monolithic constraints of older projects.

### **Framework: Standalone Service vs. Embedded Next.js**

While the associated project, ArxMint, is a Next.js 15 application 14, embedding the core mint processing engine directly into Next.js API routes (e.g., /api/v1/swap) is **not recommended** for a production deployment.

**Limitations of Next.js for Minting:**

1. **Lifecycle Volatility:** Next.js (especially in serverless environments like Vercel) aggressively terminates long-lived connections. Cashu requires persistent gRPC streams to LND and persistent WebSockets for NUT-17.30  
2. **Event Loop Blocking:** Intensive secp256k1 scalar cryptography blocks the Node.js event loop. In high-traffic scenarios, this processing should ideally be offloaded to worker threads, a pattern that is cumbersome to manage within standard Next.js routing paradigms.

**Recommendation: Standalone Microservice**

The mint should be built as a standalone Node.js service using **Fastify** or **Hono**. Fastify offers the highest routing throughput in the Node ecosystem, excellent schema validation via JSON Schema (vital for rejecting malformed blinded messages), and native, highly optimized WebSocket support. The Next.js frontend can communicate with this Fastify microservice over standard HTTP.

### **Project Structure**

A Domain-Driven Design (DDD) approach is optimal, loosely mirroring the modular crate structure of the CDK 3:

* src/core/: Protocol constants, error codes, and the BDHKE math wrappers interacting with @noble/curves.  
* src/db/: Prisma or Drizzle schemas, migrations, and repository patterns.  
* src/lightning/: The backend provider interfaces (LND, CLN, FakeWallet).  
* src/routes/: Fastify controllers mapping strictly to the Cashu REST endpoint definitions (/v1/keys, /v1/swap, etc.).  
* src/services/: The core business logic, executing the Saga patterns and managing state transitions for quotes.  
* src/utils/: Parsers, validators, and DLEQ generators.

### **OpenAPI and Type Safety**

The Cashu developer community maintains standard API specifications. Implementing an OpenAPI (Swagger) layer using fastify-swagger ensures that the TypeScript mint rigidly conforms to the JSON payloads expected by external wallets (such as Minibits, Macadamia, or Cashu.me). The internal state must rely on Zod or TypeBox validators at the network edge to reject invalid BOLT11 strings or improper curve coordinates immediately.

## ---

**7\. Open Source Landscape, Funding, and Interoperability**

Entering the Cashu ecosystem requires aligning with the existing open-source momentum and development culture.

### **Community Dynamics**

The Cashu community is heavily decentralized, coordinating primarily through the cashubtc GitHub organization, Nostr, and Telegram developer channels. The ethos is strongly rooted in sovereign computing and privacy. Core maintainers like callebtc (Nutshell) and thesimplekid (CDK) govern the protocol's evolution through the NUT specification process.2

### **Funding Mechanisms**

The ecosystem is heavily subsidized by philanthropic Bitcoin grants. **OpenSats** is the primary driver, frequently providing funds to Cashu infrastructure projects.11 The 16th Wave of OpenSats grants (February 2026\) provided direct funding to the CDK for cloud-native Kubernetes operability, and to cashu-ts for TypeScript wallet toolkit development.11 A well-executed, production-grade TypeScript mint would be a prime candidate for future OpenSats infrastructure grants, as it fills a massive architectural gap.

### **Interoperability and Fedimint**

Cashu is distinct from Fedimint, though both utilize blind signatures. Cashu prioritizes extreme simplicity, single-operator setups, and rapid deployment.34 Conversely, Fedimint focuses on multi-signature federated consensus, requiring a quorum of operators. Interoperability between the two currently relies on the Lightning Network itself acting as the universal bridge; a token melted from a Cashu mint can seamlessly pay a Lightning invoice generated by a Fedimint gateway.35

## ---

**8\. Threat Modeling and Security Considerations**

A Cashu mint is a custodial honeypot. It holds live Bitcoin liquidity and issues bearer assets. The security architecture must anticipate and neutralize highly sophisticated attacks.

### **Known Attack Vectors**

1. **Token Forgery (Invalid Curve Attacks):** A malicious actor might submit ![][image1] coordinates that do not sit on the secp256k1 curve. If the mint attempts scalar multiplication without validating the point, it could leak data or crash. The mint's BDHKE wrapper must explicitly call Point.assertValidity() before any operation.  
2. **Preimage Exhaustion (CVE-2025-65548):** Legacy mints suffered vulnerabilities where unbounded preimages in NUT-14 HTLCs allowed attackers to fill the database and disk with arbitrary data.36 The TypeScript mint must enforce strict payload size limits (e.g., \< 1024 bytes) on all secret fields.  
3. **Lightning Routing Manipulation:** A malicious user might request a melt to their own node, intentionally manipulating routing hints to siphon the routing fees reserved by the mint. The mint must place a strict upper bound on fee reserves (e.g., 1-2% of the total payment) and automatically fail routing attempts that exceed this threshold.  
4. **Proof Flooding (Denial of Service):** Attackers can spam the /swap endpoint with thousands of valid but zero-value blinded messages to exhaust CPU resources, as elliptic curve scalar multiplication is computationally expensive. **Rate limiting** at the IP level, or at the Nostr Pubkey level (if using NUT-21 authentication), via Redis is mandatory.  
5. **Double-Spend Races:** As detailed in Section 4, this is addressed via SERIALIZABLE database isolation and row-level locking.25

### **Key Compromise and Rotation**

If a mint's active private keys (![][image3]) are extracted from memory, the attacker can silently issue infinite, mathematically valid ecash.

**Mitigation:**

* Private keys should never be stored in plain text. They should be derived dynamically from a highly secure BIP-39 master seed phrase loaded via restricted environment variables or a secure enclave (e.g., AWS KMS, HashiCorp Vault).26  
* **NUT-01 Keyset Rotation:** The mint must expose secure admin APIs to force keyset rotation. If a compromise is suspected, the operator must mark the compromised keyset as "inactive," permanently halting the issuance of new tokens from those keys, while actively monitoring the swap endpoints for unusual volume.2

## ---

**9\. Publishability and Ecosystem Positioning**

By executing this architecture, the resulting project will own the highest strategic gap in the market: the definitive native TypeScript Cashu Mint.

### **Licensing and Package Nomenclature**

To maximize community adoption and ensure compatibility with the broader ecosystem, the project should be open-sourced under the **MIT License**, mirroring the licenses of Nutshell, CDK, and cashu-ts.3

For NPM distribution, establishing a standalone package structure is highly recommended over burying the logic deep within the ArxMint monorepo. Naming conventions such as:

* @cashu-ts/mint  
* @arx/cashu-mint

Releasing it as a standalone package allows developers to initialize a mint with a simple const mint \= new CashuMint(config) inside any Node application, perfectly mirroring the highly successful developer experience established by the cashu-ts wallet library.

### **Differentiation Strategy**

To stand out as a fundamental infrastructure primitive rather than "yet another side project," the TypeScript mint must emphasize:

1. **Cloud-Native and Serverless Readiness:** Unlike CLI-heavy tools, a Node.js mint intrinsically appeals to developers operating in Vercel, AWS Lambda, or Cloudflare worker environments. Emphasizing ease of deployment in these ecosystems is a massive value proposition.  
2. **Extensibility via Middleware:** Node.js developers rely heavily on middleware. Designing the mint so that operators can inject custom Express/Fastify middleware to gate minting based on external Web3 or Nostr interactions (e.g., requiring a valid L402 token via Aperture before allowing a quote) will drive extensive adoption.  
3. **Built-in Management:** Providing an integrated REST or GraphQL administration API that links seamlessly to existing management UIs like orchard 14 will dramatically lower the barrier to entry for new node operators.

## **Conclusion**

The construction of a production-grade, native TypeScript Cashu mint is highly feasible and strategically vital for the maturation of the ecosystem. By leveraging the @noble/curves library for rigorous cryptographic precision, employing a robust PostgreSQL schema featuring Saga-pattern crash recovery, and executing Lightning integrations via @grpc/grpc-js, this infrastructure will entirely bypass the IPC bottlenecks and deployment friction associated with current Python-in-Docker setups. By operating as a modular Fastify microservice, this architecture will not only stabilize web-native platforms but establish an authoritative, open-source standard for the entire JavaScript Bitcoin economy in 2026\.

#### **Works cited**

1. cashubtc/nutshell: Chaumian ecash wallet and mint for Bitcoin \- GitHub, accessed February 28, 2026, [https://github.com/cashubtc/nutshell](https://github.com/cashubtc/nutshell)  
2. Releases · cashubtc/nutshell \- GitHub, accessed February 28, 2026, [https://github.com/cashubtc/nutshell/releases](https://github.com/cashubtc/nutshell/releases)  
3. cdk \- Rust \- Docs.rs, accessed February 28, 2026, [https://docs.rs/cdk/latest/cdk/](https://docs.rs/cdk/latest/cdk/)  
4. Releases · cashubtc/cdk \- GitHub, accessed February 28, 2026, [https://github.com/cashubtc/cdk/releases](https://github.com/cashubtc/cdk/releases)  
5. cdk-mintd \- crates.io: Rust Package Registry, accessed February 28, 2026, [https://crates.io/crates/cdk-mintd](https://crates.io/crates/cdk-mintd)  
6. ngutech21/moksha: A Cashu wallet and mint written in Rust \- GitHub, accessed February 28, 2026, [https://github.com/ngutech21/moksha](https://github.com/ngutech21/moksha)  
7. DUCAT-UNIT/unit-cashu-mint \- GitHub, accessed February 28, 2026, [https://github.com/DUCAT-UNIT/unit-cashu-mint](https://github.com/DUCAT-UNIT/unit-cashu-mint)  
8. Releases · cashubtc/cashu-ts \- GitHub, accessed February 28, 2026, [https://github.com/cashubtc/cashu-ts/releases](https://github.com/cashubtc/cashu-ts/releases)  
9. cashubtc/cashu-ts: A TypeScript library for building Cashu wallets \- GitHub, accessed February 28, 2026, [https://github.com/cashubtc/cashu-ts](https://github.com/cashubtc/cashu-ts)  
10. Start using Coco | Coco Cashu Docs \- GitHub Pages, accessed February 28, 2026, [https://cashubtc.github.io/coco/starting/start-here.html](https://cashubtc.github.io/coco/starting/start-here.html)  
11. Sixteenth Wave of Bitcoin Grants \- OpenSats, accessed February 28, 2026, [https://opensats.org/blog/sixteenth-wave-of-bitcoin-grants](https://opensats.org/blog/sixteenth-wave-of-bitcoin-grants)  
12. @cashu/crypto \- npm, accessed February 28, 2026, [https://www.npmjs.com/package/@cashu/crypto](https://www.npmjs.com/package/@cashu/crypto)  
13. cashubtc/npubcash-server \- GitHub, accessed February 28, 2026, [https://github.com/cashubtc/npubcash-server](https://github.com/cashubtc/npubcash-server)  
14. orangeshyguy21/orchard: Web application for Cashu mint management \- GitHub, accessed February 28, 2026, [https://github.com/orangeshyguy21/orchard](https://github.com/orangeshyguy21/orchard)  
15. cashubtc/nuts: Cashu protocol specifications https://cashubtc.github.io/nuts \- GitHub, accessed February 28, 2026, [https://github.com/cashubtc/nuts](https://github.com/cashubtc/nuts)  
16. Cashu NUTs Specifications, accessed February 28, 2026, [https://cashubtc.github.io/nuts/](https://cashubtc.github.io/nuts/)  
17. NUT-00 \- Cryptography and Models \- Cashu NUTs Specifications, accessed February 28, 2026, [https://cashubtc.github.io/nuts/00/](https://cashubtc.github.io/nuts/00/)  
18. nuts/06.md at main · cashubtc/nuts \- GitHub, accessed February 28, 2026, [https://github.com/cashubtc/nuts/blob/main/06.md](https://github.com/cashubtc/nuts/blob/main/06.md)  
19. NUT-11 \- Pay-To-Pubkey (P2PK) \- Cashu NUTs Specifications, accessed February 28, 2026, [https://cashubtc.github.io/nuts/11/](https://cashubtc.github.io/nuts/11/)  
20. Cashu Nutshell v0.14.0: P2PK, DLEQ Proofs, Mint & Wallet Improvements, accessed February 28, 2026, [https://www.nobsbitcoin.com/cashu-nutshell-v0-14-0/](https://www.nobsbitcoin.com/cashu-nutshell-v0-14-0/)  
21. nuts/12.md at main · cashubtc/nuts \- GitHub, accessed February 28, 2026, [https://github.com/cashubtc/nuts/blob/main/12.md](https://github.com/cashubtc/nuts/blob/main/12.md)  
22. A curated, collaborative list of awesome Cashu resources \- GitHub, accessed February 28, 2026, [https://github.com/cashubtc/awesome-cashu](https://github.com/cashubtc/awesome-cashu)  
23. The Cashu Protocol, accessed February 28, 2026, [https://docs.cashu.space/protocol](https://docs.cashu.space/protocol)  
24. Blind signature \- Wikipedia, accessed February 28, 2026, [https://en.wikipedia.org/wiki/Blind\_signature](https://en.wikipedia.org/wiki/Blind_signature)  
25. How is double-spending technically prevented in traditional banking? \[closed\] \- Software Engineering Stack Exchange, accessed February 28, 2026, [https://softwareengineering.stackexchange.com/questions/442535/how-is-double-spending-technically-prevented-in-traditional-banking](https://softwareengineering.stackexchange.com/questions/442535/how-is-double-spending-technically-prevented-in-traditional-banking)  
26. cdk-cli 0.14.2 \- Docs.rs, accessed February 28, 2026, [https://docs.rs/crate/cdk-cli/latest](https://docs.rs/crate/cdk-cli/latest)  
27. Integrating Proof of Liabilites in Cashu: A guide to Merkle Sum Sparse Merkle trees, accessed February 28, 2026, [https://www.youtube.com/watch?v=eXrHC7MlmiE](https://www.youtube.com/watch?v=eXrHC7MlmiE)  
28. Building Intuition for the Cashu Blind Signature Scheme \- \#3 by ZmnSCPxj \- Protocol Design, accessed February 28, 2026, [https://delvingbitcoin.org/t/building-intuition-for-the-cashu-blind-signature-scheme/506/3](https://delvingbitcoin.org/t/building-intuition-for-the-cashu-blind-signature-scheme/506/3)  
29. GRPC API Examples \- Voltage Documentation, accessed February 28, 2026, [https://docs.voltage.cloud/grpc-api-examples](https://docs.voltage.cloud/grpc-api-examples)  
30. How to write a Javascript gRPC client for the Lightning Network Daemon, accessed February 28, 2026, [https://dev.lightning.community/guides/javascript-grpc/](https://dev.lightning.community/guides/javascript-grpc/)  
31. The 6 different Lightning backends for Alby Hub, accessed February 28, 2026, [https://blog.getalby.com/the-6-different-lightning-backends-for-alby-hub/](https://blog.getalby.com/the-6-different-lightning-backends-for-alby-hub/)  
32. cdk\_cln \- Rust \- Docs.rs, accessed February 28, 2026, [https://docs.rs/cdk-cln/latest/cdk\_cln/](https://docs.rs/cdk-cln/latest/cdk_cln/)  
33. cdk/README.md at main · cashubtc/cdk \- GitHub, accessed February 28, 2026, [https://github.com/cashubtc/cdk/blob/main/README.md](https://github.com/cashubtc/cdk/blob/main/README.md)  
34. Cashu | Bitcoin Design, accessed February 28, 2026, [https://bitcoin.design/guide/how-it-works/ecash/cashu/](https://bitcoin.design/guide/how-it-works/ecash/cashu/)  
35. Lightning Is The Common Language Of The Bitcoin Economy, accessed February 28, 2026, [https://bitcoinmagazine.com/technical/lightning-is-the-common-language-of-the-bitcoin-economy](https://bitcoinmagazine.com/technical/lightning-is-the-common-language-of-the-bitcoin-economy)  
36. CVE-2025-65548 \- Red Hat Customer Portal, accessed February 28, 2026, [https://access.redhat.com/security/cve/cve-2025-65548](https://access.redhat.com/security/cve/cve-2025-65548)  
37. cashubtc repositories \- GitHub, accessed February 28, 2026, [https://github.com/orgs/cashubtc/repositories](https://github.com/orgs/cashubtc/repositories)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABoAAAAYCAYAAADkgu3FAAABFklEQVR4Xu3Uv0uCQRwG8K+gYKBSIkjo4CIhlH+BbkI42KAOgqOzs2NDSzZFo7u4tLY4iNTY3CioQ0MQbUE25HPcI3YXwvv6xju9D3x44b7c3cv9EgnyT2nRYIcbOCFP8W2iQzqHT7iEY8rCFXxTg308pS56sJLVriZc0BRiRnWP3MEM0lb7KXzQCMJm2XnUHypTuBdzoIjofVrS2a+a6xToHYbQpA6MoQ8J8pQL+oKabA9CXvRSPUKOPEXtza79ycAcHihqVF3Gl4ni8ET2QVA5gmd4oZRZdp7NIVB6Vk2lLHrvbilklp2nLdtbb1/UoujlnECSXKci+l6s4Ide2aa88duFA/bxPVX5+/DarkW/n0GC+Jw1fIZJ301KNxwAAAAASUVORK5CYII=>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAAYCAYAAAAPtVbGAAABHElEQVR4Xu3UsUsCcRQH8CcSFChJTYpbLkG4CP4HDg6JCNLW0tbUn+BobTW6NQTRLg6KCG39C20SOomTa/T98t6V/dA77jid7gsfOHye73w+fyJJYkgKyvAKc5jCB9RNAR4g690QJTttcmLe4BNqkLbaETyaGTzZ66FyDCMzFm3m5sIsoeXUAnMAPdEnpNL/8m/yhqM7d2qB4VN9Q8dsi9fkGTJOzTeH0BcdgTeO2FOEL3gX3ZZIGxOUCqzgRXR1aVu41sRNC5W9NOGWLER/TL+cwr0J3YRbMjG83rQ1/HZ3cGkipSE6siuzPjJeX4s2CRqnb3gjP5xjoyHcwC0MoG3viSX8z1AVmnAmf2eXmxx0RU8KPzxQkyTZUX4Aij00lqVcpeAAAAAASUVORK5CYII=>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAZCAYAAADnstS2AAAA2ElEQVR4Xu3SvQ7BUBwF8CtYfAwSidjEYrQwSMRkMRhswmjwAAZh8QQS8QI2E+8gMdlsBiQGi6fgnPY0zW0tbBIn+SXt/Z82vW2N+d3kYSFHaNpjO3FoyA2q1vRNeDc6QS4wC2UqG4gFZlY4ZIl4AcN9DCSrNScflfmMZ2lBBSawkpFfdXd/lZ6U4CFdv2pMH56yhqTW+XihzS5hKzO4Q9lqKGnYw1BSsIMxFKTuVo0pwkUL5JXb0JHaV2UeHIz7LikCc+O+Mu+r8t9xEoWEd6Lwgoxm9E8oLwGZKi4LR9U5AAAAAElFTkSuQmCC>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEYAAAAYCAYAAABHqosDAAACwklEQVR4Xu2XS6iNURTHlzzyzGuCSB6R8kheMaYoj0IkEyGlDIVEKQyQRBjIxEAeY2biloHXwMiIARJFUqIwwPq11rpnn+/sw73H7Z6r9r9+dc639/d9e6+91n/vT6SoqKiH1U/Z5VyqsMr7DFEOONF2Rpnk7b2lscoJ5aFzVRla1yMv5jhXua68U14rj8XmBxOUk8qIuAGVwDQJDBrl0Om72KTHK4O9nQdvcl4o27y9v7f3lnjfNLFJwfH65qzGKDeV58oKqY2ZxT7rvFXO+fWstio/leXJNYKyWuxGGJa0tUOzlA/O2kpbqpHOHeWuWICqmu18UtZX2up0WSzVpvr/gcp+ZY9YpHs7Q3JiAowxHWdVjDtKnmyYXt/cKbIeyD4C3qDRzhPltlgJjVPOK4uSfn1BZG2HM1xssZaJeWRkM8Ej8+GIX8spAnNF7FkNmud8FqtbgoFBYXCkYyvCs+LFXSE7sIowx/tiYwR84pCy06+vEVtUFpfyAEqlZeEt4S83lKPKKf+/MunXHS1RNnaDOXbbHxX+EuM9qExWtottGkuVicobsewHKqFl4S3Aw9eJGW6Y0jVlQK1rWxUl8siJYDLeQf57gfJVbCsH2kJxNKkeSy4oM5N+nSqByQQmTDc1XkQwCMo/12kPCuPF93Y4L8U2iHThKLePYoYKVeF97FIPlKfODLGdrE4RYaBmU+EvrBCeQ7TT6P9Nh8UMvKvstduaKjXeEBn0Ssy8mQenWzYLgtfh5EydbZ7tPs5mWYXpVg92KLIJM5vitEthvOmhjjMW4+NT4ZjUxrdB+eZskcZy2qf8Egtsw8GOC6zUD7FO8F65KJaavOxe0vbF4VulHeJzhfGmizNfeSY2pt3JdSa/2cEKmEeU3y2xyjgtFuzswe5/Eh6QO1PhifhGM3HfQrEjwWKpeWhRUVFRUVEf12+fcbqXobUungAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAZCAYAAADuWXTMAAABA0lEQVR4Xu3Tv0sCYRzH8Uc0aLBaAqGGrqVoDpobDXEXGiOwuSH6Mbm0BTVG4NQmbuHicP4DTkZDBOEY5CA0SeD7i99Hvh5dHAZN94HX8nyeh3ue5+6cS+OzgAp6+EAf12oZNWxPZ2u2VBdNbJqupF7RwZLp3AZe1DmytiQ51cCDLVbQRqjytozkDod2oIpvFNVvucGuHZh7sWwxdJOzFlTi7OATj8ioxJEtfOEiWpAAt7iPOPAT/OIzP2AiH4sc4wgjVcain7CKZ9Rd/Lbl9byr9ZmGnGKAPWUT4A1PavpUnz8tlrNdYqjkUuTHuEILxzhRsZF3Lvbd5GLW3M93kObfMwZLXzUe86P4EAAAAABJRU5ErkJggg==>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAaCAYAAABhJqYYAAAAsUlEQVR4Xu3QvwpBYRzG8Vf+pFDKICMuwSaTGN2AkUEGKaNZcQnugMGgXImJ0Q24B9/neFDKcDbDeepT5+339J5zfiEk+duk0LIxamhibjq/M8PQejhjFT7lI/Iq1rEMz9ulgSs6LskOGZWzyOnB0c0XVD2T9GsYq/ydBQ7Br/1OAV2UTEX9g1Kxts9hgjv6dsPAs5Hp06KosMfWNjhhjalpS/HLSjk8lx4tnhQtyc88AGI7HX5yGejgAAAAAElFTkSuQmCC>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAXCAYAAAAC9s/ZAAAA1ElEQVR4Xu3RsQpBURwG8L9QlFBGg+IBDMoku8FiUh6AwUAGsyysFuUFvILd7gFMBrErgyS+f+cbjtt1O7LdfPUb7v3OPd3/OSKhSB1WPhrWmizMPP0U0lqmoARbuJF+nNCSiUIT9tSCHESsNdKFJ/XtAsnAEgrkm583KMKZNpDk+zjMocrnj4nBmq5QETPjQMzMTmmTjjGBIYzEc1hBydMBHmLm1hGco3MrPYOdmKv6KvYfLN4rt9ToDh1P55QxXaDs6QLTg6OYg1N6Cycx9/9P+PMCUjEs5BuzEc8AAAAASUVORK5CYII=>

[image8]: <data:image/png;base64,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>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAkAAAAYCAYAAAAoG9cuAAAAhUlEQVR4XmNgGAWkABMgzgZiSSQcAcQOQMwMUqACxJ1AnAvEb6F4ORD7AvFtIHYBKUoGYhsgroIKgrAsEBcB8Wsg1gYp4gVidiBeA8TzoZgRisFWEa0IBKSB+AEQR0MxVgBy00sgNoZirADkyNNALAjFWMFCIJ7CgHALVsANxKzogiMDAAB6FxTp7wUVYAAAAABJRU5ErkJggg==>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHMAAAAYCAYAAADJcMJ/AAADbklEQVR4Xu2ZW4hOURTHl0Lu99zjkyTlVuJBPCiiXJJLSGnKCxmRSLx4wANSbkle5AEleRNJmnhRvFBSSg3hQeEFhcL6z1rL7LPPmdOZc86waf/q1zedfWa+ffbae+21zxBFIpFI5A+ynj2f41F28u+7w2MUe1x1+72H7eXct1m19nPsdKc9NPqyzewT9g37Qj3LDmWb2KV2sxGDGSalgjmIXax+YQ+QDBAcyx5kv7Or1dDowY5Q0fef7BGS53JpqA9J7htH8ruh0Y1dxr5nT5MEzmUu+4gkwFO8tjZWqQjaPK8NQX3Jtqj93MbAwMNhEG6xvZ3rGKCdKp6zDFgp+/SzK8GC+cyuI+m3D66dYe+z/b22Nk6pWMaY4S5T2Y/sFbV7sjko0LdrJP1Fvw0E0IKZNUBFwCQ+pJ9dxRySviMb5vVzL0m8UqBzLSoGwg0W0hD2l1fsNDV0UAMg1eKBAQYIaRfPUiWtVgnmMHYHO4vtwy5h17IDtB1/0+Lwmp2g1zsC9cAK/yKw1AQvsWtUFAu3SQbCvrQO0Gnbk4vq7395YCAwIA/YRexldmDijnKUCaZNIIzhSpLtCukRgbxK7atrofqDJIXmrcpcEOGv6nJqH8BJJGn1HknhUBeYPDZhiopNv+gD4r4LJKvzMTs+2VyaMsFEqoe72dkkKRQpf4b+vEXv26+izxv1Wilsr8zaL8ewrewNkjLfLfVDppmkmFvgNxSgoZ6k5FEHEwTHBHy61+ExdjilsTGDCFIryZgCdzu7qOI0gaC7TCSJkf+d2yijfonBTNJQ/7lgorRFDkfh4xc/YDDJuewpySYOQ8fSrPW5LsqkWcP6lDXGwE4TOJKgSHKxc/QmFal4K2XUEVb8oPKz6s9lPsleeoKkQ0X3rTw2kFTHnREP2hO/XACbgB0NXFmqBNP6lDXGABU4RAGUWaUyh1XEK/NlAZa+vSjwXxbgVRdS7112iNcWMpjZmOG7/IaKVAkmCp63lB5jA9U2vEOSKf3xRhH3XE29LEAZjBn/jWTZ4ougrYR3+rmdkm9SQsXOwNjTPpE80weSc1tdqbZKMHFKeEbpmsRnJHudpNLFcQaVPD5vUnuaxavI2mhQujjIcqbe/79QJZjY9zrzGhBBxwSAo6me7S3igP0X/z2KAxuJRCKRSCTyN/kFQuDlVx9RfHIAAAAASUVORK5CYII=>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGYAAAAXCAYAAAD5oToGAAAC7UlEQVR4Xu2YS8hNURSAlzzyjBB5lDwmyiORYkwYkOQxIAMkFJlIiTKgMCMjmRiITCWK9MfEYyzKBIkiGRkYeKyvtXb3v9u955x7zr3X+f/2V1/9/9nnnHvOXnuvvfYRSSQSiWHJCHeZelv9rH5QX6ib1NnqJXeSX1M3pqkX1WfqTXV8c3NXGOUeU6+18Yw7y68pzVT1jvtWXa+O9LZx6mX1k3rFrSs880KxwXQ+ausWYQAzCPaqf9TdYkHAeWKDAr+rq+2yzpmsPlIfuwQpZonYj2xz68xi9au6JW7oAafEMsuC6PhK94d6I2orTApMeXoWmNFiOZE0tchtBVOU9MBLY51h4LTqrG4zVr0nNqgnRG0b3d/q2eamYvASRS4mMER+oltnWAMHxJ6TNWetetCNO7AKc9R38u9aFjIQPpcSBUCIOCmKVNUv6KwZblgw85wpNrvzoFp8KtZZFC2n1QN+DDc3Tq3MOrFBTRW43aVSe6IedXmGjpmrfhR74H6Wvzws5TeGF8pzqzqdi3MI6wtVEvmfCmmf+tNd0zi1CYLO/Rk0oRrN46T6RazqCgNouVhgbrmt1utcwuJEWUf5lwV7m1LR7zMhNZNClvox3m2M2w7SH2VvGDBZkGmy1pfQr1hqa8Ho+ib5VUPYtA2FwNARbC73i+X/q2KbwTwIxl2xLIJZhHPINvH6AhQdFB9I8AhiR7A4DrjtFnRG23Hpbm5mej9w+bJQxNfqKi7OYPD6Asye92IpJpSvzPyqsLbgL2ldku8Rm7V4KGorDDdmyu2Sxo42wN/sbAlMXqqrA2F9CZ3FGvBSbMafc+d7WxUIPMYlOX20QayYuu6WzjLcjKCQ0h66pIEj6n11h58zFCAdMbtC569QX4ml4cNuFRj9pC9mSpD/w6xmULxRd0pnRUQm5EGqC6QC4ntT1o0JXvzhLvaElMivFaCyYg8xGH5/SnTsf8Cgifsn9oK0eNYUmN5SOjCJRCKRSCSGOX8BwiC1J4lvo9UAAAAASUVORK5CYII=>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABsAAAAXCAYAAAD6FjQuAAABcElEQVR4Xu3UvytGURgH8EcSQn5NbyjFgsHgRymDZDVTksEoi9HColgMMkhKGKTeLFLv5g+wKoPFIEIWWRjw/Xqe0z2uc/GmruV+67Pc53TOe5/nnlckyz+kDdbMpmcZ6mxNX6xGU1YrKmWQM4dwB/3QCCW2ph5OzC50Q7XVig43o1M4hgqv1gAbMGz+nFQPY1voEZa85x2wB63es2B6YUaiedA4DEFptOwjE+YVRkRnNQYLUOmtC6YdVmAWHsw+jMKF6IZ+tswNdMGq6MH8cT9mGgZhXnRzaoE5uBfd0MXNis7gQPSQKyjIL96sBsohD9uGraF4C92s6Ej0g+C6dXiGgWhpcprgUqJ5JMXNys3LhYfwMB7q7lti2MZb6DGhcBO+NVtGzV6N7WMbr0W/gW/D+XAO7g6F4t+t+P1i+NZvsBh7/iU7ErUg3oZa0fnwr4mbvZhz0SvDTMKT1YkfD3Va/VOqRP/3Ukmqh2XJEsw76j5O/803w98AAAAASUVORK5CYII=>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHUAAAAXCAYAAAA1OADtAAADX0lEQVR4Xu2YW6iNQRSAl1CUO5FDUXhwT24RkSgeSCJKLuVBSVJIyeU8UHgg8iApIeWWkkQRp8gDry7FyyERhRKKB6yvWXP2f8bsfbbO2Xv/u+arr3P65++cmVkza838IolEIpHICZ3MCepF9b36Rn2sLlIb1MNqT7NWdFbnqbfF9bFZbVInqaPN/eLGUm+MMI+rpzIeVPvYO1ODNlxnba3op142X6kLxE0edFePqe/E/bNaMlx9JG6hsfh84Oj/FfWzudGe1xtdzcHqNfWjOk3tL4Wx9lXvm+fUiWoPa2uht3pXvWcyQSHj1C/qsrChSgwzX6qnxS20kIXi+ois5nqGwD1Rb6rdMs+JzUlxmQqLkoKaP9oVVLY6OZnUOtKMQTog5VGvqo1fdEgfSEUxJqsPzQFBW71BSv2qHsg8Y+7PiytBJWHn/VYbg+chBPWsRHJ3Fdip/jFXBW1ZCCq1H/N0SKIvZJH1Zi9xm2e1uD7H+kobcZkvrn2luk/iGaoVbGu2N+mK9NoRcEJjAZQri6TUQmHHPVNfmINaN9cFs9Ud6lHztXpCXOCeSzz7UWI42Y9Vj4gLcKkF3cJQ9a36QDruijJdXf4fjjeLQW38oV4wY6s6z9Df3eJ2ph9Dk7iFTOCeqgP9y+Jqqa+ntF0SF0zixBWuzZ3K1v8u5U0W14c2/2AFWCwu7e4yi9FFXB/5ie2Fe3l4FyzmFjP2f5lXNgznAAKFlBPf5q+NHmqpr6c3xB2MeI+d/VOdUXg1Dtv+k7haWQo6dEhqE1RqCqmHifCTEWOUulcKH1DyBhvogzkraMtCSs7WUw/BJKgEt+T4SAFNZrG6xh/YKm7HlMMecV+hynW7WYwh4r4YnTFjA+IEz6Lji1JeIVDNJmOKwdj8OEm3lEcPG4r0628pJVkiLgVzugpXOb+vFRfU2GRWi21S+FI0M2gjoKTlWt2fy4X6edWMpWnwtTR2PwUWBqWoMXj+DwSLgJKG75gb1E3qLXWFvVNLCBynR6TWcHhggATzujqn8Gou8RlxsxnCPZz6ySdBf3X7Je60P8XeWaN+y7RziMIx1h6FVcE3Rlwq7qNyWMTzABM0V1w5aJDSC47FGR5qQlko4Y6oBByWmM+qzmkKamWpSVATiUQikUgkEsZf5OjJwLzS7l4AAAAASUVORK5CYII=>

[image14]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAPsAAAAXCAYAAADN9DlfAAAHtklEQVR4Xu2ae6hlUxzHf/LOe8hjKOMR0SAMGiFT1MgjGRoSJlPe5TEGicwkNd6PwUTyTIPG4w+Dhrgh77zyaqQuMUISRSSP32d+63fPuuusve85+9577r539re+3Xv23meftdfv9/091toiDRo0aNCgQYMGExGTlAuVm6cn1kDsrLxYuW56osHEwlqBeysfU36v/Eb5jvIo5WTlDYGbhO/UCRsGXqF8Sdmn3Cq+IIPNlE8o9w2fD1PemyHP7yAoLErOX6vcNLqmbthIeYHyY+V3yq+Udyu3DJyjPDpce4LyIjFfGEscF/i48kvljMGnx42tDlA+pPxCOTc5NxwUaTXVa5tWyW44PWRij1SuHc4hoNuVq5R3BNYRHqwQ+FPKZcp1Bl3RjssDHRsrd1G+FviX2MRtEF3DvByrXCkmDIhgxlocKXw+jlH+rFwsNk7Hwcr3AgkAe4TjZPWHxYQ2lsAWEIHgzFQdMbq1ldur17ZiPIwLGxySnKsK12tOq6leB4HsRiZ8OZAbpZiq/EVazl1nIPZPZbCIc9hJ+Xr4m+LswP/EMmIM5muJcsfkeDfYR3lGenCEMSvwd+VsaXdwPt8ZiFjiDDBTuUJMUGMNHLZPisfSqa2q2mskbMX4+pXbJ8erINZrTqsg1usgNGJvR6cOVBUj4UBDoRF7I/ZBWqVko48h5e8amMN2Yr0ApZ6Xe3UFPdKPMnTJhAGWSb7Up2SElI8viJVGgPm6Xnlg+FwV+yvPSQ+OIBgfxob0qKnQHd7GpOUeAfNt5fTkeC9B8IEEouuSczHqbivm/lEp9rVOwfOkei1CrNcBoPx/lQvigxnw5Yek1UfVGXEUZaL3VF4orcU6Jhwy+ZeEYyn8mqVimRGDcy8WrkaisqnqQCy0nRV4hJjxCWqnitkIYJ8+5beBucrFMT8w7c/dQYvmpxfwxPKTtMZHv828TfOLpL62cqSVJjY8Wax6YpxOPs8RWzxEyNjUnwV4Vd2tXleDhYPlYtGftN8rsJiwtdiAOuE2gUNtB/mkeRRdX3muWGn3pHJeuG6LwHfFFm/KgFEoDxeKbUlxj6Is2Q2qOBC/e5m0yvP3xZ6B+9ykfEbMpgQBHMJL9KrjvVLMYYYCK96pzcrYacJw5yZjk7kPEqtSsAXPmt6jTraKEVeaiHiRWPJ5S2w+Dg0k6N6q/FrMboj9M7GA51qtrNcdxCJ/2q+NNiizWJ08sUMeH+iZuQic9yh6lZjI91MervxbzBmAO92HYoYsA9VBv/Ifsd5vqIDTKao4EAGPcnZKILYjW3CcrbTbxJwbkeL0OAusCu7dJ+2iSoEIU5uVca/AoUBr4f06mf1MMft+JJbFyeYx6mSrGF5pEoSZU+aTYIXYCZT4KiQQkKj6wjX3KT8RS4yuVUiAJ1l1BR6CsocfGCoCsp/nvVBdQQSFf4hts8yQ1nMRGR3diJ1npg8ki1JCdguCWrzH63xa+UbmODxPWlspMXBeSkAyBPxBWuPnen9WsjFz4PMRg60qBJT+5vnSLp5OxT4a8F4d4qO8O0GlBpiH3PzUyVYAe0D09afyHmnt73vrwXlfm2DMCNnLfc75vV2rOb3yP21dOra7lLv7RZQH7P3hHGVgECx01F3sRFBIGXSa8gPlc9LurN2I3bNFuoA1XAwnW/iiWlGEZ6w4Bb+RPh9CoRI4XSz70+ZAMkyKsRS79+qQkvx+sVKYlfEi1M1WcaV5i1gL8qsUt478DgE8t7DsWi3SK/ajMngzEN/fTaLqBiP2BRYZlKjBQkfRAKtgklgE5o2fTvh54DS+XACPoN6vEzXJapQ9TCIZjTeugIudFxIorcrAxNMCDKcczqGqA/FcPB98QPIVGe0KPbu/gZYD7QCOgxPBHBC7z2UZrpZ2m5Xx0sAyeK/u/bpnesZE0uH8egNXG+pmK6+svF93H0Ws/M8zxG/yMe5+yW/Psd1G2Q/7JK9X5snnLBvwcAaywGxplR0O/icDIPacU9UJHkGhl0EEKHcW+vfp4TgT5YGOCS8D9/pNyjNKFVR1ILIy/Tkscmrfh/UymOAag/3mleGcl5A50DNmnaYH8F4dYiuCMxUbz8zczfMLI9TNVl5p9osJ2H2OQMtnFuriQMp8lwXXWYG0BKdIu1ZZvKVag1m/5iKETpR/MXCuWC/yvPKkcE3dgYF9AcNFzaIGe403iq3QppOIQzHxKTCs34vFHiZvlVgrM1Ko6kB8z8U+NTkXY1uxV4Yhq7eMncUx/mJXgvg1A1e3g7WBFVJcGYwm+G2C1YJAgO2WKB8R632xLaizrRAvXCot3yNIoTGexYNSnHxISkXwZIxesekrYlqFz4otzN4cWFStrQYLWLx8AFn5puwtWngA/EC6IBBzfmC8MDaaYKy+pRYHJ3oWMlsuYM1UviqWCXuNqg7Ec5Zl4xyoBqhy4GTJz0UKnIWSMVdS9gLYBNsN9Jxi48aW8bFeoKqtXMSpBuiv02MAm5ZpLgZzQFtLAEezufsVohF7b1HVgRqxN2IHwxL7mggMsVzshYZeA6cdKyF1AsrJBenBNRR1t1WDDkFUfFDqv63YS0wR21vmZY4GDSYUWLkcDzsOvQCLY4ulfJuzQYNxjW76pYkMekEE36BBgwYNxhv+B0nb6pxDyBdoAAAAAElFTkSuQmCC>

[image15]: <data:image/png;base64,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>

[image16]: <data:image/png;base64,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>

[image17]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABoAAAAXCAYAAAAV1F8QAAABiklEQVR4Xu3UPSiFURgH8Ee+S/nIzUARm8VXlLrEZrGYlGQwSClFYjAwSgndUhaTzcdmMhhlMSkpRYmyM5CP/+N5zj3nPV4nUXd6//Ur1/O857z3fc57iZL8M6WwAMfqBKrdBmQYtmO0Oj0NsOHVZ6DINOSRLHyg9qDAFDUV0AbX6kE/Fzo9/PcUnKsekusi4Y0u1LxXc7Op3mHAq9XDFpSr2ORso054VGmv5oZr7BUyJI+dwwvzJrxZMBNwo2pJFmiGaYoeDHO3p2R7eTYr0GXb4sOL7pIcAlYMkySD3YdZ25rNEnzAGKzDUKT6Q8x8FhVv0A59JI+Ij7afDniCF5gj+wiD4fk8w5XqJ3thiWnykoJLOKToEQ+G53MLo4rfgSMoc5u8mG/E1/4q7nz4JWX8De9IFmuC3my3zQjJYw2d0EjMfNx3Z5DkzW8kmVe3U+MbYzskvxA1Ti2YFpK7dxergzNYhWWyP0drcK/4xL2RXDuu9WDyoZK+nxoecFXM//+cnG2UJMlXPgGRflCDojDbPAAAAABJRU5ErkJggg==>

[image18]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEMAAAAXCAYAAABQ1fKSAAAChklEQVR4Xu2XS6hOURTHlzzyzDPyKHkNCCVFzAzIHZBEBgohxegOlBIxoDAjpaRkoCSZyYB0y8RjYiIDEyQGwoSBCf6/s/b27W/3ne+hr+9Mzq9+ddt7n3vPXmettfc1q6mp+Q9GBVfLO/Kz/CBfyCE5T14KTgnPDIKZwYvymbwtJybzk+UZeT3zgpyWrGMP+ZrNyfw/Zsi7wbfmi0aHuQnysvwkrwQHCe+BS8w/zPnm6WJuttwf/C3vy1nmHzcyXT4IEohlcnwyXzBVPpZPggQmZ6X8LncGq2C5/CK35xMBNo+v5Rs5p3m6eO/hYBqkJupgBMaapwwlsDTYirnmKcoLYRWwGfrY4nwigzKiVLYmY+vMew77xZbwB3jwbDaeQzBumTcrrAJ61Yj536dPbJRH5KRkDWyQv+RN8wxYKK+ZV0ApNA+aCelPGfQDujeB68VOweXkwqfmX52GfkoeDmPbGksL2DSnzke5Sd4zD0hbFpg/wC/s11G5Xu7q0VXFk+XE0qRf7JUnzTd30DwDyIScE/KPeflTIh1ZK3+an9stG0oCdw++SBXEpk05P7dG8HjncXFRxhbz9Qey8VKI9lfzXtCOeOGpKhjxbkPqH5Lv5FU5JlmTQ2awt66bPbU6EiyrW6LPUZTXZRmnzW+tvXi8eLI1sVfEfgFkyXvzfkN2k7UpBIk+8dL8otU1nNmUyh5rXMcj/LzP2pzLAyD2ivR+wVdno2TsObkojEfmm2fPjWy8I2ySQJBSj4Kk4jH5UO4Oa6piyBoZFDe9xvxiRekeDWNcx2MGfTNvnj/kK7kirOkajlm6Lu4w/z+As7xquCBxVOZ3BN43/Sesr9TBqKmpqanpnb9ea4gniSKgjgAAAABJRU5ErkJggg==>

[image19]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAZCAYAAADuWXTMAAAA8UlEQVR4Xu3Tr2qCYRTH8WeozT8MDTa1KEsGYeANDGE3IJjWdgeijIWVNQcWQYSt2MQrWNAsLCkLa8aBhoG2gd+DRzm+myIaLP7gU87vfeDw8LzOnbNKAEUM8Y0xnlUYT8isv9ak1Qe6SJnuVn2hj5DpXAKfqgKfLYlfddCyRQTv6KmgLT2po2QH9/hFQe1KDTk7OPiwrNjDCDG1d64wQRsXau/ICjNUvYUnq63idpjFD8p2+E/uVN4OLzHAq9u+dhKPSl7fRuS2p7hWNrJmwy0fkfiTow7LKg+Yq6Zb/hgveHOeS9oWeabiRkU363NOlwVdhCqO2OrP2QAAAABJRU5ErkJggg==>

[image20]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFIAAAAYCAYAAABp76qRAAACmUlEQVR4Xu2XS4iNYRjHH7lHrjNJTEQpIswMIsTORglFIQsLKVGMS9OMWFig5FYKJcrOZUUWFrOUjRKRSw2JUmbHglz+//M875z3e8/3zcx3snnH+6tfnfM973Pqe87z3kQSicQgZjQ8Ch/BLrPBi5Ot8EqOi7wxM+H5IH4AjvDGxMZkeAK+hR/ha/MYHAfbYKsbnApZTKlCDhEt3F142xzmgsYEuBi+g59Nfh/ujeHnvfApXGUyL0aGwn3wq2iTjbHnrBXdAp/B5xI0Hb+8gEfMIi7A3+a6IDYDXobjg+exwUIdhj1wRRBzcBY/hLdEx/eyBH6BK80iGPtpXpLqj7B4LCKLGTubRN9vexgIuAF3hw/5oBtOM1mgeXC/ZFuXBXtsdouO5ZQ+BZdWh0VJk/lG9P36m1kXYYv/gEVji3JtHGnuEV3v7sCD1aEVjpt/4E54Dm704gOF6yedWsKxlcz68lxuEWwmyvfiu5fGrY8doj9Am+Ea0Rbnju3Df4F+gz/gIQnWiQGyzNxcwgWVzPryXG4erpnod9GlrjRMYjK39bWmK8woN8ij0XwF70l2544VdmuXyWPOdD+Yg1sCM6RC/qNCcl14D3eIngHpAyleU/ypXbNrRQob5r7JWnBdzYMNRnlEnB8G3EbDQzi7k/JfYbFmw9W9o5VtJtfPvo5K/dFpfihhWyWzvjyXW4Q7Q7NBMruxB08m9KQEl5YGqR7EyXqTN5dZohvPcosRFv66yVvOFC8WO5zO9CW8Jnro9pkLr5o1R6OFot3niuV+7Ak8I3rPdJU/Cz+JHg/oL9HcXRYfLMwRfX/er9tFZ99NeFr0quiuixl4p5wotccXbiCTcp7/L7AuXNY2iE7lvE03kUgkEolEdPwFFN+pv7T6T4gAAAAASUVORK5CYII=>

[image21]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABIAAAAXCAYAAAAGAx/kAAABD0lEQVR4Xu3SsUtCURQG8CMqKA0qLjY41Bw4iP+Bg4EQOLS4NDW1F63RIA6CREO0i3+Ac2vgv9AUgeAihA01lN/H/a5enjze0qYf/AY9517fOU+znUgKLuUp4lQ9ebgRXxtAVfV1isKD3+aaDiGnOn/sXN7gQvW06lvpwi80g+94SRuGchDUYvNvFz3DDI71OQvXcGVujNhRfEoyhYm53VTgARpBX2Jq8gn35g6/wysUgr7EcDd+P2O4g74+t4K+xHA3xFd/Zm7BJ7CAEWQ2rfHxuwn3w/AwL+FlvDQxdfiS20iNY3E8jsqnpNj43UT/P4x/2g84kq10zL2ZH/iTOTyaG6sML0FtKT0e3mcfZAWL7TqUEBm4qQAAAABJRU5ErkJggg==>

[image22]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEkAAAAYCAYAAAC2odCOAAACn0lEQVR4Xu2WS6hNYRiGX7nfLym55SS5RAxcBjIwcB2YoJChMJCJAYWBiQElEQZKMhBJMaAMhFKuA3MmJ7mEZEQywPv6vn/vtf69FuvsznHWrv+tp3brX2uv1ft/3/t/QFJSUj9pBzlfwmmyhgxu3N3ZGkAWkqvkPXlNnjnryRRynIwODwQlkyqYNI6sdb6Rk2Sys4g8Ik8z1zpVE8g18oqsJgP9+nDnFHkHK4xCbXd+klXR2gbyi+xzOlFjyV1yD2ZWkRaQL2RjvBAk90Q3mZpfwm50rkmKCaHoUJXMyi/npC5R282LFyT130PnNhmWWVMZ3iEvyQynLlri7EEzCraSlWi2kqpCqEOO+LUy6flLZFS8IMm5z84x5PPoBrlOpjXubk96cfjfKignRZlUEfpWsRf27Vdg0aDMUWRos7XpQm2kdmpbwWkhU1SaF2DJfxS9c7JpIzb3gOWOTqMi6URe4RyEGTMdFgefyHzYxr5xnpPxf55sUyGLRDaP1pEfaA3yoIlkTHzxP0kRMdRRpV+EGSpCqy0mX53Lvhak37vQOvKcJXMy9zWUTPqHSSpBlWLo3Wxoa7jSqaY+z2ouzFiVuD6kv6QNFd2w8SVWNmsVyLGUecq2x84LMhsF8RL+6ICTlfKoyCRJQXwT1U3aBsu4qoSRZIgeLlHIpA8o/g7NRk+cByg+tWbCJm+h9xUqO0DGbSX3NYEvhb3wkDMCPTepLxTmtr+F8ibnO2yj4pbbDysEoQMsJ+WNdkyZoxs+OufIIL9np6+pwg6jOXNIdTBJmyjOoPwUDDm1BTYG3IedjOIW7GQ84RQOkVU0CdZu8aRaB5NGOi0ZUiLdp+FTI8Yy5PO3T1QHk2qtLlhbvoUNnzoFkyJ1IZmUlJTUe/oNm4ywXO6UUJ4AAAAASUVORK5CYII=>

[image23]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFMAAAAYCAYAAACGLcGvAAACx0lEQVR4Xu2YS8hNURTHl7zzlpKQWwh55jERZSCPwgADj6FkgBQDhTKQAROPJCnJQCbKSEnSF6VkbELqY6CQzBQK/39rrXv2Ofcczjn3Xlzf/tevr3v2PueetfZe/7XvJxIVFTXAtAdcLeAiWAeGNmf3rnZIa3zOWWNOc3ZNxWR2MJnjwXrjMzgHphiLwRPwNLjWq/I4GeNJSeKZBk4Z38A2v6GudhvfwdrM2GbwAxw2ellbRRO2KnPdE/sa9IHRqdGKYjmTfjA1PST75P9JJmN8BSZnri8wPoFbYEh6uLzGgMfGXTAiGBsJ7oEXYIbxr2g52G/4zqIvrgGDk2lNcbf1gduSThb7gXvnG7AwGKuseeCjcUbSfnlH9MvpK+2Igfhzy0B/I0WaJfquBw2+O3cULemltFoV5XHeBNsNNt/7os8iY5uza4o+Qq8kTB5X6JroKp2WznRyBuIBlGGlMYg354hJoO8dM5jA6aI29AHMT6Y2tQV8EU24L9ps0UV4ZDR8cl25V5LQLzeAr5K/yrQCBtOQ4oC7KVrTcNGqIddF34PklThV5JeMud/I2lxlxWR2KJkTwDPRh2QftFG0i7MsQi0Fh8BMUf+hLXTCCqoqTAKPdUVi4r3JZpsP5Tkgz8Gk9HB5uSkfNULRL/OSyXkPwCjR+9np2ax+pZ2iHlwWP6oN480FYmW8M5ZlxkLxHcM4s1ot6qXkvLRRaeFBPVvON0R/LawA48BxY6IknZZB0Pz5sn9abDa+o7i7iuQ/SPIO64tES/+hwdgqi37IHUBP5O57b1yWpAz22hhX84Ro1yculvYVcEDaWM02xMW+ZOR9PzeHx+hxvrVrhPHyL49WPE+TropmzTLnuS4UE3lE1Ff/lmgzfI9u+HUDXJDWf4hkWWLza4vdcheYa583ye89M6pAPDCzZJy840ZUScVkRkVFDST9BPqCwjoVi9vjAAAAAElFTkSuQmCC>

[image24]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGUAAAAYCAYAAADjwDPQAAAC2ElEQVR4Xu2YTYhNYRjHHyGE8pWPkM9oWBAziiTKRsiGEkmx0DQzTY3yMc1ijCYkG1lISpRYYCNWYsQKRcqGzZASsrWR+P/v87zOuW9zzj33nNud23h/9VvMe957Pt7neZ/nnBEJBAKBQCATE+AJ+AgOmDNixwPDQAhKAzJKNAj34B1zTNmMEc5JONMfbAAYlHfwuPlfcRrO8QcbgBb4DW40U+EDHDGPwaXlh+tCM2wTvRe619wMR0fTMlE0KLzeWtgJd4j2g1rA9R2Ec02WtBWi1ynrL+vgA9hkroJP4KL4JI+xcJZEC1hJlpK0hWUSnIMd8Ae8BXeaH+DWaGomigRlNXwD2+E8eBCeLZuRDwbgpmgvGWe2il7nLjwan3gNdrsBsEe07vGGkpgGd8HdGd0OJ5Z+OTSHRbcz74NBmA+7zO9wZTQ1E3mCssB8L7pQji2i50uCCcosT0s64vpJj+j56RrRSvBLtCqUYPdn5H7Dx+Y+qd12zcpk0czhvTBJmCzOpIedIprB9IrnW9Gs9McvwWX88RBcMH+KlhMmyg14VTQJk7gI/8Bt/gEP9hOem0FnoCmfj4x3k0gISkTDBIXwJp+KBobyAr3xCXWCjW8Q7vfG81Bt+WJp5UcdfQaXiPZMlqZKMBj3Jb3cEzb5j/AAfG0+hJPik3jBbngo9jdlpl53kxJgY34FP2X0OVzIH6bAnvJV9K2nKNUGhQszYFZ69jxwR7gmz+rEXUM/iz4vk2ATJ3KHcBHYeAgnU27zf02njrCpv4RT/QM5qDYoxJUv/0t7A+yT5DKaBdfk3Qeje7P8AheLNv31PMBdwZu4LPrad9vst2P1hhnKmu/qbBHyBGW2yc+DM6I9ha+qTJaiPZafGdwVpYUXLXX0BTwPT4n3LxduXVc/hyMYDtb1Wl0/T1AcTIrpUvnbqhp4HlYAP+H4vHyJ8MdHJMuldgEOBAKBQCAQKM5fXN+YFJOTDbYAAAAASUVORK5CYII=>

[image25]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACoAAAAYCAYAAACMcW/9AAACPUlEQVR4Xu2Wz4tOYRTHv0IRk1+TmWmU8mNlgdT4kRpCKaQolIWFhUQpNWYxqTcWSBMLm6kpmcVkQVmQksXEDkUK5Y+wY2HD9/uec9/3ec+93l9jXkY+9dk8z73PPfee85znAv/pDFvpuTg4wxym++Pgrxhw79PFYW6mmU9vwJ7fkFkRqAJ75G4Jc51iHX1GV7mFnKCT7rww1ynm0Dt02M2xgD6hJ90/yV76wl0S5rCGfqAb3SLmwkrignuQLqy5ojmUXnmJnqF9tdPllL9zc7HspB9hN8UbxSbYjedRrZ9T9Hp6URMcpRPuarqHPkXtl+uiL91DyXgZDUzBNlTc7VrwMyzIlN30ahirh9adokdccRm2edJnZtfJXJ3WC3SUfoOl+zSqX2ScLk+ua8Qy+pp+dx/QA7CSSvm3A11En8PqZS3tgTVm2Q6D9K37w1VbTGkYqHZ9t5uR3XQvGWsHbZZbdF8YUwuKwaSB5lql2s57FJ8ISr3SFA+BHfQKLHXb6Fd6G9a0ZcouWLqPJWMKSL17ezImlLVPrnpqDfqKr2BtSqb0wha8BqvRh+5FVPvoZvoFViaxfIS+3iTsLNca8jE9i/xLqXe+cfvDXOXoKrkRza+gK2FfMG4AoXouoTjQjKWwNbJ1itAhcNeNL1FG6VdPkwqqVdbTkTjYIsqQykzlEEuigqIfcvVWraAuUIIdjdPhOL2J4jqvMGsCFVmPbOoHNkH1pjN6OmygYyj4Y6rH73hwq2gztnuQ/D38BKFXb6UDtIDjAAAAAElFTkSuQmCC>