# **Deep Research: Programmable eCash and Advanced Spending Conditions in the Cashu Protocol**

## **The Architecture of Programmable eCash and Blind Signatures**

The evolution of digital bearer instruments necessitates the development of programmable constraints that govern the transfer and redemption of value without compromising the fundamental privacy guarantees of the underlying cryptographic protocols. Within the Cashu ecosystem—a Chaumian eCash protocol built on top of Bitcoin—these programmable constraints are referred to as "spending conditions." The foundational architecture of Cashu relies on a Blind Diffie-Hellman Key Exchange (BDHKE), ensuring that the issuing entity (the mint) remains entirely oblivious to the tokens it signs.1 The introduction of spending conditions requires a delicate cryptographic balance: the mint must enforce logical rules at the time of token redemption, yet it must not possess any knowledge of these rules at the time of token issuance.

To understand how conditions interact with the mint, it is necessary to deconstruct the BDHKE issuance and redemption lifecycle. Under the standard BDHKE model, a user generates a random secret ![][image1], maps it to a point on the elliptic curve ![][image2], blinds it with a random factor ![][image3] to create a blinded message ![][image4], and submits this payload to the mint.1 The mint, possessing a private key ![][image5] for a specific denomination, returns a blinded signature ![][image6].1 The user unblinds this signature by subtracting ![][image7] (where ![][image8] is the mint's public key), obtaining the unblinded signature ![][image9].1

In a basic token, the secret ![][image1] is merely a string of high-entropy bytes. However, when programmable conditions are applied, the secret ![][image1] is structured as a specific JSON array.2 Because the mint only ever signs the blinded point ![][image10], it cannot inspect the JSON payload during the minting (signing) phase.2 The programmable conditions are completely hidden behind the blinding factor. It is only during the token's lifecycle events—specifically a swap (transferring value) or a melt (converting eCash to Lightning Network payments)—that the user must reveal the unescaped secret string to the mint to prove ownership.2

Upon revelation, the mint parses the secret string. If the secret conforms to the well-known JSON format specified by the protocol, the mint identifies it as a conditional token and dynamically executes the required verification logic before authorizing the transaction.2 This architectural design confirms that the mint does not need to know about the spending condition at signing time; awareness and enforcement occur exclusively at the time of redemption.2

## **Current State of Cashu Spending Conditions**

The Cashu protocol has formalized several specific types of spending conditions built upon a foundational specification known as NUT-10. These specifications dictate how clients and mints serialize, transport, and verify constraints.

### **NUT-10: The Foundation of Spending Conditions**

NUT-10 (Spending Conditions) is the foundational specification that defines the overarching transport mechanism for programmatic constraints.2 It is currently a finalized, implemented standard supported by major reference mints and wallets.4 NUT-10 does not define specific cryptographic conditions itself; rather, it defines the *well-known secret format* that all subsequent conditions must inherit.2

The structure mandated by NUT-10 takes the following JSON format: \["kind", {"nonce": "\<str\>", "data": "\<str\>", "tags": \[\[ "key", "value1", "value2",...\],... \]}\].2

* **kind**: A string indicating the specific type of spending condition (e.g., P2PK, HTLC).2  
* **nonce**: A high-entropy string ensuring the global uniqueness of the secret to prevent hash collisions and double-spending of identical conditions.2  
* **data**: The primary cryptographic lock payload, such as a public key or a hash digest.2  
* **tags**: An array of string tuples used for auxiliary parameters, including multi-signature thresholds, time-locks, and signature scope flags.2

By utilizing this schema, NUT-10 requires a change to the token format exclusively at the application layer. The underlying cryptographic primitives (the blinded signatures) remain identical, ensuring backward compatibility with mints that simply treat the JSON string as a generic secret, provided the mint's info endpoint indicates a lack of support for specific conditions.2

### **NUT-11: Pay-to-Public-Key (P2PK)**

NUT-11 details the P2PK secret kind, enabling an eCash token to be locked to a receiver's Elliptic Curve Cryptography (ECC) public key.6

The specification explicitly mandates the use of libsecp256k1's serialized 64-byte Schnorr signatures.6 Currently, Ed25519 is not supported in the standard Cashu P2PK specification. The reliance on secp256k1 is deliberate, as it ensures cryptographic parity with the Bitcoin base layer and the Lightning Network, simplifying the development of wallets that manage both on-chain Bitcoin and off-chain eCash.6

To redeem a P2PK-locked token, the spender must supply a valid Schnorr signature corresponding to the public key defined in the secret's data field.6 This signature is attached to the transaction payload within a P2PKWitness object, formatted as {"signatures": \[\<Array\_of\_hex\_strings\>\]}.6 The message to be signed is the unescaped string representation of the Proof.secret field.6

A critical security feature of NUT-11 is the scope of the cryptographic signature, dictated by the sigflag tag.6

* **SIG\_INPUTS:** The default behavior. It requires that each token (input) provided in a transaction be signed independently, proving ownership of individual tokens.6  
* **SIG\_ALL:** This flag enforces strict transaction-level security. If any input utilizes SIG\_ALL, all other inputs must be of the same kind and possess identical data and tags.6 The signature must commit to the entire transaction state—both inputs and outputs.6

The aggregation algorithm for SIG\_ALL prevents transaction malleability and output substitution attacks by a malicious mint. For a swap transaction, the message string is formulated by concatenating the secret and unblinded signature ![][image11] of all inputs, followed by the amount and blinded message ![][image10] of all outputs: ![][image12].6 For a melt transaction, the aggregation string appends any blank outputs and the Lightning quote\_id.6

### **NUT-14: Hashed Timelock Contracts (HTLCs)**

NUT-14 defines the standard for Hashed Timelock Contracts within the Cashu ecosystem.4 While the data payload structures mimic the flexibility of P2PK, the verification logic differs. HTLCs operate on the principle of a hashlock coupled with a timelock, allowing for trustless, atomic swaps between parties or across different ledger layers.8

The token is locked using the cryptographic hash of a secret preimage. To redeem the funds, the recipient must present the exact preimage that resolves to the locked hash digest.8 A time-based condition ensures that if the recipient fails to produce the preimage within a specified timeframe, the funds revert to the original sender.8 NUT-14 is fully implemented in modern mints and forms the basis for atomic interoperability with the Lightning Network.4

### **The Roadmap for Programmable eCash**

The Cashu community's roadmap for programmable eCash relies heavily on expanding the extensibility of the NUT-10 base. Several advanced spending conditions are actively proposed or in development:

* **NUT-28 (Pay-to-Blinded-Key \- P2BK):** A recently proposed standard that introduces ECDH-derived key constraints to enhance privacy.12 By blinding the receiver's public key using an ephemeral shared secret, P2BK prevents external observers (and potentially colluding mints) from linking disparate tokens to the same static identity profile.  
* **NUT-XX (STARK-proven Computations):** Tracked under Pull Request \#288 in the nuts repository, this experimental specification introduces a spending condition capable of verifying Zero-Knowledge proofs generated via Cairo.13 This represents the ultimate evolution of programmable eCash, allowing arbitrary, Turing-complete logic to dictate token redemption while maintaining absolute privacy.13

| Specification | Description | Cryptographic Primitive | Protocol Status |
| :---- | :---- | :---- | :---- |
| **NUT-10** | Spending Conditions Base | Arbitrary JSON Arrays | Finalized / Active |
| **NUT-11** | Pay-to-Public-Key (P2PK) | secp256k1 Schnorr Signatures | Finalized / Active |
| **NUT-14** | Hashed Timelock Contracts | SHA-256 Hashlocks | Finalized / Active |
| **NUT-28** | Pay-to-Blinded-Key | ECDH Key Derivation | Proposed (Draft) |
| **NUT-XX** | STARK Computations | Cairo / zk-STARKs | Experimental PR \#288 |

## **Condition Handling in Existing Mints**

Analyzing how existing reference mints handle these specifications provides a blueprint for constructing a highly performant TypeScript implementation. The ecosystem is currently anchored by two primary reference implementations: Nutshell and the Cashu Development Kit (CDK).

### **Nutshell (Python)**

Nutshell is the original reference implementation of the Cashu protocol.5 It achieved comprehensive support for NUT-10, NUT-11, and NUT-14 starting in version 0.14.0.5 Nutshell handles spending conditions dynamically at runtime. When a swap or melt POST request is received, the mint software iterates through the inputs array.2 If a secret field successfully deserializes as a NUT-10 compliant JSON array, Nutshell's routing logic directs the validation to specific sub-modules based on the kind parameter.15

For P2PK tokens, Nutshell utilizes the coincurve library to execute elliptic curve operations, validating the secp256k1 Schnorr signatures against the unescaped secret string.7 The mint maintains a stateful ledger—backed by SQLite or PostgreSQL—to track the hashes of spent secrets.14 This state management is crucial; it ensures that even if a cryptographic spending condition is met perfectly, the fundamental protection against double-spending remains intact.

### **Cashu Development Kit \- CDK (Rust)**

The CDK is a rigorous, memory-safe implementation written in Rust that provides core libraries for mint and wallet construction, alongside standalone binaries (cdk-mintd, cdk-cli).4 The CDK provides robust, native support for all finalized spending conditions.4

In its Rust architecture, the CDK models spending conditions using strict algebraic data types and serialization traits (serde). The validation pipeline is integrated deeply into the state machine. When processing incoming tokens, the CDK precisely reconstructs the exact string payload required for signature verification—handling the intricate string concatenation required by the SIG\_ALL flag—and defers to highly optimized cryptographic crates (secp256k1) for signature validation.6

### **Implications for a TypeScript Architecture**

For an independent TypeScript mint to maintain interoperability with existing wallets built on Nutshell or CDK standards, it must flawlessly replicate the string parsing, escaping, and concatenation rules.6 The most critical vulnerability vector in developing a custom mint lies in the normalization of the JSON secret prior to hashing.6

Because the Proof.secret is transported as an escaped JSON string within a larger HTTP JSON payload, the TypeScript mint must extract the raw, unescaped string exactly as it was originally constructed by the user's wallet.6 It must then apply the SHA-256 hash required for the libsecp256k1 signature verification.6 Failing to handle character encoding, whitespace, or Unicode byte-order marks correctly will alter the hash digest, resulting in valid signatures being erroneously rejected. The use of robust libraries like noble-secp256k1 is mandatory to ensure mathematical accuracy in a JavaScript/WASM environment.

## **Technical Feasibility of Specific Condition Types**

The modularity of a bespoke TypeScript mint permits the introduction of proprietary spending conditions tailored to specialized applications, such as AI agent micro-economies and peer-to-peer merchant networks.

### **1\. Time-Locks for Subscription Services**

Time-locked tokens allow users to allocate capital for future recurring payments, ensuring the funds cannot be spent by the recipient before a designated date. In the Bitcoin base layer, time-locks are implemented at the script level using CheckLockTimeVerify (CLTV) for absolute time and CheckSequenceVerify (CSV) for relative time.18 These opcodes rely on the decentralized consensus of block height or the Median Time Past (MTP) of recent blocks.18

Because eCash operates entirely off-chain, it cannot natively rely on block height. Consequently, Cashu implements absolute time-locks within the NUT-11 (P2PK) specification via the locktime tag, which relies on the mint server's local wall-clock time represented as a Unix timestamp.6 The protocol dictates three distinct lock states:

* **Active Lock:** The current server time is less than the locktime value. Only the primary locking mechanisms (e.g., the recipient's public key) apply.6  
* **Expired Lock:** The current server time exceeds the locktime value. This state triggers fallback or refund conditions.6  
* **Permanent Lock:** The locktime tag is absent or malformed, rendering the time constraint inert.6

When a lock expires, the token triggers a "Refund MultiSig" pathway. If a refund tag is present in the token's secret, the token becomes spendable by the cryptographic keys listed in that tag, allowing a subscriber to automatically reclaim unspent tokens after a billing period elapses.6 If no refund tag exists, an expired token defaults to being unlocked, allowing anyone possessing the unblinded signature to claim the funds.6

**The Challenge of Clock Skew:** The reliance on wall-clock time introduces significant architectural fragility. If a client's local system clock is heavily skewed relative to the server running the TypeScript mint, a wallet might generate a token that is instantly expired upon arrival, or conversely, locked for far longer than intended. To mitigate this, a production-grade TypeScript mint must implement rigorous Network Time Protocol (NTP) synchronization and expose its current Unix timestamp via a public API endpoint. Wallets can then fetch the mint's precise time to calibrate their locktime parameter generation dynamically.

### **2\. Escrow and Multi-Sig for Dispute Resolution**

Multi-party computation and threshold signatures are essential components for merchant dispute resolution in circular economies. In traditional models, a 2-of-3 multisig setup (involving the Buyer, Seller, and an Arbitrator) secures funds in escrow until a consensus is reached or a dispute is mediated.19

Cashu facilitates N-of-M signature configurations natively via the Locktime MultiSig pathway embedded in NUT-11.6 When minting an escrow token, the buyer configures the secret with a primary public key in the data field, appends additional participant public keys into a pubkeys tag, and defines the necessary threshold requirement in the n\_sigs tag.6 For a 2-of-3 escrow scenario, ![][image13] equals the primary key plus two additional keys in the tag (![][image14]), and the n\_sigs tag is set to the integer 2\.6

**Implementation Nuances:** A custom TypeScript mint must meticulously handle the validation of multisig witnesses. libsecp256k1 Schnorr signatures rely on auxiliary random data, meaning they are non-deterministic.6 A single private key can generate infinite valid signatures for the same message. Consequently, the mint cannot simply count the number of valid signatures provided in the P2PKWitness array to verify the threshold.6 Instead, the validation algorithm must extract the recovered public key from each valid signature and verify that the signatures correspond to a minimum of n\_sigs *unique* public keys from the authorized set.6 A naive implementation that merely counts signatures would be vulnerable to a single participant submitting multiple distinct signatures from their own key to bypass the threshold requirement.

### **3\. Proof-of-Service for AI Agents**

A highly specialized use case involves autonomous AI agents paying for computational resources using "proof-of-service" tokens. In this paradigm, an agent submits a computational workload alongside a locked eCash token. The token is only redeemable if the compute provider can mathematically prove they successfully completed the requested task.

While not natively defined in the default NUT-10 specifications, this logic closely mirrors the mechanics of a Hash Time-Locked Contract (HTLC) defined in NUT-14.8 In a standard HTLC, the token is locked to the hash of a random preimage. For a proof-of-service implementation, the architecture must be inverted: the token is locked to the hash of the *expected computational output*.20

The architectural flow operates as follows:

1. The AI agent defines a deterministic compute task.  
2. The agent calculates the SHA-256 hash of the expected output state (the "service receipt").  
3. The agent generates an eCash token locked to this specific hash via a custom NUT-XX tag, e.g., \`\`.  
4. The compute provider executes the task, generating the resulting output.  
5. To redeem the token, the provider submits the actual output data directly to the mint alongside the swap request.  
6. The TypeScript mint hashes the provided output and verifies it against the lock in the secret. If the hashes match, the token is unlocked and credited to the provider.

This model is conceptually identical to Lightning Network keysend payments that utilize custom TLV (Type-Length-Value) records, where arbitrary data payloads dictate settlement rules. The advantage of deploying this logic on a custom TypeScript mint is the ability to write custom hashlock verifiers that can parse and interpret specialized AI workload receipts natively, acting as an unbiased decentralized oracle for the machine economy.

### **4\. Rate-Limited Redemption Constraints**

Implementing tokens valid for exactly ![][image15] redemptions per time period introduces severe complexities related to state management and privacy. Traditional Chaumian eCash relies on the absolute invalidation of a unique secret upon redemption to prevent double-spending.21 Modifying this binary state to allow "partial" or "rate-limited" spending directly contradicts the fundamental privacy model. To enforce a limit, the mint would need to maintain an active counter tied to a specific token identifier, thereby tracking the user's transaction velocity and unmasking their identity over multiple sessions.

Academic cryptographic research addresses this limitation through constructs like "Everlasting Anonymous Rate-Limited Tokens" (EARLT).22 These advanced frameworks utilize complex cryptographic structures—such as Camenisch-Lysyanskaya (CL) signatures, BBS+ signatures, or KZG polynomial commitments—to create a "token dispenser".22 A user interacts with an issuer to receive a dispenser parameterized by ![][image5] total uses. The user can then generate unlinkable, publicly verifiable proofs that a token originates from a valid dispenser without revealing *which* specific dispenser it came from. Cryptographic nullifiers ensure the user cannot exceed the limit ![][image5] without their anonymity being mathematically revoked.22

Translating EARLT mechanics into the standard Cashu framework is currently beyond the scope of existing BDHKE primitives. Cashu's unblinded signatures (![][image11]) are static and binary.1 Implementing true rate-limiting without tracking user identity would require migrating the mint's core architecture away from BDHKE toward a zero-knowledge accumulator model, representing a fundamental rewrite of the protocol layer.

## **Zero-Knowledge Based Conditions (The Frontier)**

The integration of Zero-Knowledge (ZK) proofs represents the absolute frontier of programmable eCash, allowing complex conditions to be proven off-chain by the user without ever revealing the parameters or business logic of the condition to the mint.

### **STARK-based eCash and Cairo Integration**

The most significant development in this sector is Cashu PR \#288, which proposes an experimental NUT-XX for STARK-proven computations.13 This proposal leverages Cairo, a Turing-complete programming language designed specifically to generate Scalable Transparent ARguments of Knowledge (STARK) proofs.13 By utilizing Cairo, this protocol extension enables entirely generic smart contracts to be bound to eCash tokens.25

Under this model, the token's JSON secret encodes the hash of a specific compiled Cairo program alongside a set of public inputs.13 To spend the token, the user executes the Cairo program locally on their device. This execution generates a succinct STARK proof that attests to the correct execution of the code and the satisfaction of all internal programmatic constraints.13 The user then submits this proof to the mint. The mint, acting purely as a verifier, runs a highly efficient cryptographic validation algorithm on the proof.

Because STARK verification requires exponentially less computational overhead than executing the logic itself, the mint can enforce boundlessly complex conditions—such as dark-pool order matching, private KYC/AML compliance checks, or advanced decentralized gaming logic—with negligible performance impact on the server.26 This drastically reduces the trust required in the mint operator while maintaining perfect privacy regarding the specifics of the transaction.

### **TypeScript and WebAssembly (WASM) Tooling**

For a TypeScript-based mint to participate in these advanced ZK verifications, the backend environment must bridge the cryptographic performance gaps inherent to JavaScript via WebAssembly (WASM). JavaScript's native numeric limitations (specifically the 53-bit precision limit of the IEEE 754 standard) heavily bottleneck the complex elliptic curve cryptography and finite field arithmetic required for ZK verification.28

Building a ZK-capable TypeScript mint requires integration with highly specialized performance libraries:

* **snarkjs:** A comprehensive JavaScript and WASM library utilized for generating and verifying zk-SNARK proofs, specifically supporting Groth16 and PLONK protocols.29 It can be embedded natively within a Node.js mint backend to verify zero-knowledge payloads submitted alongside tokens.  
* **wasmati:** A sophisticated TypeScript framework that allows developers to write WebAssembly code at the raw instruction level directly within TypeScript.28 This tool is utilized heavily in systems like SnarkyJS to achieve maximum performance for the finite field additions and polynomial calculations necessary for ZK verification, bypassing the overhead of standard JavaScript garbage collection.28  
* **stwo-cairo:** As highlighted in the Cashu PR \#288 documentation, experimental NPM packages have been deployed to port stwo-cairo logic directly to Wasm64.13 This enables both browser-compatible wallets and Node.js mints to interact natively with STARK proofs without requiring a secondary Rust or C++ backend.13

## **Token Format Design and Serialization**

The introduction of complex spending conditions directly impacts the payload size and serialization efficiency of the eCash token itself. Historically, Cashu tokens utilized a Base64 encoded JSON format known as TokenV3.31 However, as the protocol integrated complex multi-signature arrays, lengthy hexadecimal public keys, routing hints, and extensive JSON secrets, the TokenV3 string size grew cumbersome, leading to issues with QR code density and NFC transmission limits.

### **TokenV4 and CBOR Serialization**

To address data bloat and improve parsing efficiency, the Cashu Development Kit spearheaded the introduction of TokenV4.32 TokenV4 acts as a highly space-efficient serialization standard by replacing JSON with the Concise Binary Object Representation (CBOR) format.32 V4 tokens are easily distinguished by the prefix cashuB, followed by the Base64 URL-safe encoded CBOR binary payload.32

CBOR natively maps to JSON data models but encodes data types and lengths directly into byte headers. This strips away the quotation marks, colons, and whitespace required by JSON, significantly reducing the token footprint.32 In TokenV4, all object keys are reduced to single alphanumeric characters. Most importantly, lengthy cryptographic strings—such as the unblinded signature ![][image11] and the keyset ID—are encoded natively as raw binary byte arrays rather than expanded hexadecimal strings, cutting their size in half.32

### **Extending Formats for Custom Conditions**

For a proprietary TypeScript mint implementing custom conditions like the "Proof-of-Service" AI tokens, extending the format requires strict adherence to backward compatibility principles. The NUT-10 specification explicitly requires that receivers (both mints and wallets) MUST ignore unknown fields and tags to preserve forward compatibility across the network.32

When embedding custom verification logic, the extensions must be placed securely inside the tags array of the well-known secret, formatted as standard string tuples \["key", "value"\].6 A token encoding an AI agent's service receipt requirement would be structured in JSON prior to CBOR serialization as follows:

, \["deadline", "171829000"\]\]}\]

When this custom token is passed through a TokenV4 CBOR serializer, the nested arrays and hash strings are heavily compressed. Standard Cashu wallets that are unaware of the "PoS" conditional tag will treat the token normally during transport, routing it effectively through Nostr relays or Lightning gateways. However, when the token arrives at the destination TypeScript mint—which is explicitly programmed to intercept the "PoS" kind—it will trigger the custom validation route, requesting the service receipt before finalizing the settlement.

## **Open Research and Academic Precedents**

The conceptual foundations of programmable eCash and spending conditions are deeply rooted in decades of cryptographic research. Understanding this literature provides vital context for architecting secure mint implementations.

* **David Chaum's Blind Signatures (1982):** The entire Cashu architecture is predicated on David Chaum's original paper, "Blind Signatures for Untraceable Payments".23 While Chaum introduced the mechanism for separating identity from the token via RSA blinding, his early models did not account for programmable spending conditions or smart contracts, focusing strictly on the prevention of double-spending and absolute anonymity.23  
* **Stefan Brands and Restrictive Blinding:** The concept of embedding metadata (like conditions) into a blind signature traces back to the work of Stefan Brands. In his research on "Rethinking Public Key Infrastructure" and anonymous credentials, Brands introduced mathematical mechanisms to bind attributes to a token such that they could be verified during presentation without breaking anonymity. These concepts eventually evolved into modern zero-knowledge proof applications.22  
* **EARLT and Rate Limiting:** Academic research heavily explores the intersection of anonymity and limit enforcement. Papers surrounding "Everlasting Anonymous Rate-Limited Tokens" investigate how to prevent malicious actors from abusing anonymous systems by enforcing context-based restrictions (like ![][image16]\-times authentication) using zero-knowledge token dispensers.22  
* **Bitcoin Script and Miniscript:** Modern research from institutions like Blockstream and Chaincode Labs heavily influences Cashu's condition design. The development of Bitcoin's Miniscript—a language for writing structured, analyzable spending conditions—provides the logical framework for Cashu's P2PK and HTLC tag structures.18 Cashu aims to mirror the capabilities of Bitcoin Script off-chain.

## **Competitive Landscape**

While Cashu utilizes a purely Chaumian, script-based approach to programmable privacy, alternative protocols tackle the issue of conditional digital cash through entirely different architectural paradigms.

### **Fedimint**

Fedimint (Federated Mint) alters the fundamental trust model of the issuance entity. Rather than a single custodian operating the BDHKE issuance, Fedimint disperses custody across a federation of independent servers (guardians) utilizing sophisticated threshold signatures.35 A predefined quorum of guardians (e.g., 3 out of 4\) must reach Byzantine Fault Tolerant (BFT) consensus to issue or redeem tokens.35

Regarding programmable spending conditions, Fedimint handles operational logic quite differently than Cashu. Instead of encoding conditions as JSON scripts hidden within the token secret (as specified in Cashu's NUT-10), Fedimint operates on a modular, application-level architecture.35 Smart-contract-like capabilities are achieved by deploying custom software modules to the federation nodes themselves.37 These modules can act as decentralized exchanges, lending pools, or automated escrow systems.37 Because the logic executes across the federation's consensus mechanism rather than being isolated within a token payload, Fedimint provides higher assurances against rogue mint operators maliciously ignoring spending conditions. However, this architecture requires a significantly higher developmental and operational overhead to deploy custom logic.35

### **GNU Taler**

GNU Taler takes an entirely different regulatory and technical approach. Initiated to provide ethical, privacy-preserving digital cash that complies with state regulations, Taler implements a concept known as "asymmetric privacy".38 While the payer (the consumer) maintains perfect cryptographic anonymity via blind signatures, the payee (the merchant) is strictly accountable, ensuring "income transparency" to satisfy taxation and KYC/AML compliance.38

Unlike Cashu, GNU Taler does not rely on a blockchain or the Lightning Network; it interfaces directly with legacy financial systems (like SEPA or SWIFT) via centralized exchange escrow accounts.38 For conditional spending, Taler heavily utilizes formal digital contracts and a complex "refresh protocol".38 When a user purchases an item, the Taler backend creates a detailed cryptographic contract encompassing refunds, delivery metrics, and conditional provisions.40 If an item is not delivered, the system enables an anonymous refund back to the buyer's wallet, utilizing zero-knowledge linkages without breaking the initial blind signature privacy.38 Taler's approach to conditional logic is highly specialized for retail e-commerce and banking regulation rather than open-ended programmable bearer tokens.

### **Liquid Network**

The Liquid Network, a Bitcoin sidechain developed by Blockstream, approaches programmability through Issued Assets.37 Liquid allows for the creation of custom tokens that inherit the security and script capabilities of the underlying Bitcoin protocol. Through the use of Confidential Transactions, Liquid hides the asset type and transfer amounts, but unlike Cashu, it still relies on a globally visible ledger.41 Spending conditions in Liquid are enforced by the federation utilizing advanced Bitcoin opcodes (like OP\_CHECKDATASIG), providing robust smart contracting capabilities but lacking the absolute untraceability of Chaumian blinded tokens.42

## **Strategic Directives for TypeScript Mint Architecture**

For the development of an independent, extensible TypeScript Cashu mint, the trajectory diverges from waiting for global protocol standardization towards implementing immediate, pragmatic utility.

**1\. Proof-of-Service Integration:**

The most immediate differentiator for a custom mint is the implementation of Proof-of-Service conditions to facilitate AI agent micropayments. Rather than waiting for the complex STARK-based Cairo integration (NUT-XX) to mature into a finalized standard, the optimal technical path is to construct a proprietary hybrid of NUT-11 (P2PK) and NUT-14 (HTLC). By creating a custom secret kind that locks the token to both a service provider's public key and the SHA-256 hash of the desired compute output, the TypeScript mint can autonomously act as an unbiased cryptographic arbiter for machine-to-machine transactions.

**2\. TokenV4 CBOR Tooling:**

The mint's core architecture must natively support TokenV4 (CBOR) serialization to ensure backward compatibility with the broader Nostr and Lightning wallet ecosystem. Integrating lightweight TypeScript libraries, such as cbor-x, is essential to parse incoming byte buffers into JSON representations swiftly before executing cryptographic validation.

**3\. State Execution and Cryptographic Libraries:**

Node.js instances must leverage the noble-secp256k1 library (or equivalent Wasm-optimized curve operations) to ensure that the rigorous signature verification required by the SIG\_ALL string aggregation executes without processing latency. The mint must implement strict, deterministic JSON unescaping for the secret string, as any deviation from the exact byte structure presented by the client wallet will result in false-positive signature rejections.

By deploying custom verification routes built atop the open NUT-10 specification, the TypeScript mint can effectively sandbox advanced financial constructs—ranging from time-locked subscription sub-accounts to multi-agent compute escrows—positioning itself uniquely ahead of official protocol consensus while retaining universal interoperability on the issuance and Lightning network settlement layers.

#### **Works cited**

1. The Cashu Protocol, accessed February 28, 2026, [https://docs.cashu.space/protocol](https://docs.cashu.space/protocol)  
2. nuts/10.md at main · cashubtc/nuts \- GitHub, accessed February 28, 2026, [https://github.com/cashubtc/nuts/blob/main/10.md](https://github.com/cashubtc/nuts/blob/main/10.md)  
3. Cashu: A Vision For A Bitcoin Powered Ecash Ecosystem, accessed February 28, 2026, [https://bitcoinmagazine.com/technical/cashu-a-vision-for-a-bitcoin-powered-ecash-ecosystem](https://bitcoinmagazine.com/technical/cashu-a-vision-for-a-bitcoin-powered-ecash-ecosystem)  
4. cashubtc/cdk: Cashu Development Kit \- GitHub, accessed February 28, 2026, [https://github.com/cashubtc/cdk](https://github.com/cashubtc/cdk)  
5. Cashu Nutshell v0.14.0: P2PK, DLEQ Proofs, Mint & Wallet Improvements, accessed February 28, 2026, [https://www.nobsbitcoin.com/cashu-nutshell-v0-14-0/](https://www.nobsbitcoin.com/cashu-nutshell-v0-14-0/)  
6. NUT-11 \- Pay-To-Pubkey (P2PK) \- Cashu NUTs Specifications, accessed February 28, 2026, [https://cashubtc.github.io/nuts/11/](https://cashubtc.github.io/nuts/11/)  
7. nuts/11.md at main · cashubtc/nuts \- GitHub, accessed February 28, 2026, [https://github.com/cashubtc/nuts/blob/main/11.md?ref=blog.cashu.space](https://github.com/cashubtc/nuts/blob/main/11.md?ref=blog.cashu.space)  
8. What is a Hashed Timelock Contract (HTLC)? \- Nervos Network, accessed February 28, 2026, [https://www.nervos.org/knowledge-base/What\_is\_a\_Hashed\_Timelock\_Contract\_(explainCKBot)](https://www.nervos.org/knowledge-base/What_is_a_Hashed_Timelock_Contract_\(explainCKBot\))  
9. Hashed-Timelock Agreements \- Interledger Foundation, accessed February 28, 2026, [https://interledger.org/developers/rfcs/hashed-timelock-agreements/](https://interledger.org/developers/rfcs/hashed-timelock-agreements/)  
10. Hashed Timelock Contract (HTLC) | Builder's Guide, accessed February 28, 2026, [https://docs.lightning.engineering/the-lightning-network/multihop-payments/hash-time-lock-contract-htlc](https://docs.lightning.engineering/the-lightning-network/multihop-payments/hash-time-lock-contract-htlc)  
11. Kukks/DotNut: A C\# Cashu library \- GitHub, accessed February 28, 2026, [https://github.com/Kukks/DotNut](https://github.com/Kukks/DotNut)  
12. cashubtc/nuts: Cashu protocol specifications https://cashubtc.github.io/nuts \- GitHub, accessed February 28, 2026, [https://github.com/cashubtc/nuts](https://github.com/cashubtc/nuts)  
13. NUT-XX: STARK-proven Computations (Cairo) by vincentpalma · Pull Request \#288 · cashubtc/nuts \- GitHub, accessed February 28, 2026, [https://github.com/cashubtc/nuts/pull/288?ref=blog.cashu.space](https://github.com/cashubtc/nuts/pull/288?ref=blog.cashu.space)  
14. Releases · cashubtc/nutshell \- GitHub, accessed February 28, 2026, [https://github.com/cashubtc/nutshell/releases](https://github.com/cashubtc/nutshell/releases)  
15. nuts/10.md at main · cashubtc/nuts \- GitHub, accessed February 28, 2026, [https://github.com/cashubtc/nuts/blob/main/10.md?ref=blog.cashu.space](https://github.com/cashubtc/nuts/blob/main/10.md?ref=blog.cashu.space)  
16. cdk/README.md at main · cashubtc/cdk \- GitHub, accessed February 28, 2026, [https://github.com/cashubtc/cdk/blob/main/README.md](https://github.com/cashubtc/cdk/blob/main/README.md)  
17. cashu \- Rust \- Docs.rs, accessed February 28, 2026, [https://docs.rs/cashu/latest/cashu/](https://docs.rs/cashu/latest/cashu/)  
18. Contents \- arXiv.org, accessed February 28, 2026, [https://arxiv.org/html/2207.09460v11](https://arxiv.org/html/2207.09460v11)  
19. Bitcoin and Cryptocurrency Technologies, accessed February 28, 2026, [https://www.lopp.net/pdf/princeton\_bitcoin\_book.pdf](https://www.lopp.net/pdf/princeton_bitcoin_book.pdf)  
20. A Survey on Security and Privacy Issues of Bitcoin \- arXiv, accessed February 28, 2026, [https://arxiv.org/pdf/1706.00916](https://arxiv.org/pdf/1706.00916)  
21. A Hitchhiker's Guide to Privacy-Preserving Cryptocurrencies: A Survey on Anonymity, Confidentiality, and Auditability \- arXiv.org, accessed February 28, 2026, [https://arxiv.org/html/2505.21008v1](https://arxiv.org/html/2505.21008v1)  
22. Everlasting Anonymous Rate-Limited Tokens‹ \- Cryptology ePrint Archive, accessed February 28, 2026, [https://eprint.iacr.org/2025/1030.pdf](https://eprint.iacr.org/2025/1030.pdf)  
23. Everlasting Anonymous Rate-Limited Tokens \- ResearchGate, accessed February 28, 2026, [https://www.researchgate.net/publication/398424339\_Everlasting\_Anonymous\_Rate-Limited\_Tokens](https://www.researchgate.net/publication/398424339_Everlasting_Anonymous_Rate-Limited_Tokens)  
24. user authentication \- Cryptology ePrint Archive \- IACR, accessed February 28, 2026, [https://eprint.iacr.org/search?q=user%20authentication](https://eprint.iacr.org/search?q=user+authentication)  
25. Dora: A Simple Approach to Zero-Knowledge for RAM Programs \- Cryptology ePrint Archive, accessed February 28, 2026, [https://eprint.iacr.org/2023/1749.pdf](https://eprint.iacr.org/2023/1749.pdf)  
26. Zero-Knowledge Proofs in Blockchain Finance Opportunity vs. Reality \- Corporates and Institutions, accessed February 28, 2026, [https://corporates.db.com/files/documents/publications/Zero-Knowledge-Proofs-in-Blockchain-Finance-Opportunity-vs-Reality.pdf?language\_id=1](https://corporates.db.com/files/documents/publications/Zero-Knowledge-Proofs-in-Blockchain-Finance-Opportunity-vs-Reality.pdf?language_id=1)  
27. odradev/awesome-zero-knowledge \- GitHub, accessed February 28, 2026, [https://github.com/odradev/awesome-zero-knowledge](https://github.com/odradev/awesome-zero-knowledge)  
28. wasmati: You should write your WebAssembly in TypeScript \- ZK/SEC Quarterly, accessed February 28, 2026, [https://blog.zksecurity.xyz/posts/wasmati/](https://blog.zksecurity.xyz/posts/wasmati/)  
29. Zero-Knowledge Proofs Demystified: A Practical Code Guide for Developers \- Medium, accessed February 28, 2026, [https://medium.com/@ancilartech/zero-knowledge-proofs-demystified-a-practical-code-guide-for-developers-3f94682a852b](https://medium.com/@ancilartech/zero-knowledge-proofs-demystified-a-practical-code-guide-for-developers-3f94682a852b)  
30. You can build your own ZK App using Typescript\! Check out this Zero Knowledge Proof Coding Tutorial \- YouTube, accessed February 28, 2026, [https://www.youtube.com/watch?v=XlRC\_EW3Ogs](https://www.youtube.com/watch?v=XlRC_EW3Ogs)  
31. CashuSwift is a native library for building Cashu Ecash wallets on all of Apple's platforms \- GitHub, accessed February 28, 2026, [https://github.com/zeugmaster/CashuSwift](https://github.com/zeugmaster/CashuSwift)  
32. NUT-00 \- Cryptography and Models \- Cashu NUTs Specifications, accessed February 28, 2026, [https://cashubtc.github.io/nuts/00/](https://cashubtc.github.io/nuts/00/)  
33. Block 852152: Important News of the Week \- No Bullshit Bitcoin, accessed February 28, 2026, [https://www.nobsbitcoin.com/852152/](https://www.nobsbitcoin.com/852152/)  
34. Bitcoin Review Podcast BR097 \- Cove Wallet, Harbor, ecash, Sparrow, Liana, Bull Bitcoin, JoinMarket, Hardware Wallets, Coinbase Breach, BitLocker Vulnerability, Lightning Phoenixd, LSP Legality \+ MORE ft. Praveen, Ben, Paul, accessed February 28, 2026, [https://bitcoin.review/podcast/episode-97/](https://bitcoin.review/podcast/episode-97/)  
35. Understanding the Different Types of Fedimint Setups \- June 27, 2024, accessed February 28, 2026, [https://www.fedi.xyz/blog/understanding-the-different-types-of-fedimint-setups](https://www.fedi.xyz/blog/understanding-the-different-types-of-fedimint-setups)  
36. Core Technology Components \- Fedimint, accessed February 28, 2026, [https://fedimint.org/docs/GettingStarted/TechCompontents](https://fedimint.org/docs/GettingStarted/TechCompontents)  
37. Fedi & Fedimint: Decentralised Chaumian E-cash on Bitcoin \- The Bitfinex Blog, accessed February 28, 2026, [https://blog.bitfinex.com/education/fedi-fedimint-decentralised-chaumian-e-cash-on-bitcoin/](https://blog.bitfinex.com/education/fedi-fedimint-decentralised-chaumian-e-cash-on-bitcoin/)  
38. The GNU Taler System, accessed February 28, 2026, [https://www.taler.net/files/taler-book.pdf](https://www.taler.net/files/taler-book.pdf)  
39. Taler \- GNU, accessed February 28, 2026, [https://www.gnu.org/ghm/2020-january/taler.pdf](https://www.gnu.org/ghm/2020-january/taler.pdf)  
40. Taler SAP integration: Theoretical Framework and Practical Implementation, accessed February 28, 2026, [https://www.taler.net/papers/integration-of-gnu-taler-with-erp-systems-thesis.pdf](https://www.taler.net/papers/integration-of-gnu-taler-with-erp-systems-thesis.pdf)  
41. LLRing: Logarithmic Linkable Ring Signatures with Transparent Setup \- Cryptology ePrint Archive, accessed February 28, 2026, [https://eprint.iacr.org/2024/421.pdf](https://eprint.iacr.org/2024/421.pdf)  
42. Our roadmap \- eCash | Cash for the Internet, accessed February 28, 2026, [https://e.cash/roadmap](https://e.cash/roadmap)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAaCAYAAABhJqYYAAAAsUlEQVR4Xu3QvwpBYRzG8Vf+pFDKICMuwSaTGN2AkUEGKaNZcQnugMGgXImJ0Q24B9/neFDKcDbDeepT5+339J5zfiEk+duk0LIxamhibjq/M8PQejhjFT7lI/Iq1rEMz9ulgSs6LskOGZWzyOnB0c0XVD2T9GsYq/ydBQ7Br/1OAV2UTEX9g1Kxts9hgjv6dsPAs5Hp06KosMfWNjhhjalpS/HLSjk8lx4tnhQtyc88AGI7HX5yGejgAAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,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>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAkAAAAYCAYAAAAoG9cuAAAAhUlEQVR4XmNgGAWkABMgzgZiSSQcAcQOQMwMUqACxJ1AnAvEb6F4ORD7AvFtIHYBKUoGYhsgroIKgrAsEBcB8Wsg1gYp4gVidiBeA8TzoZgRisFWEa0IBKSB+AEQR0MxVgBy00sgNoZirADkyNNALAjFWMFCIJ7CgHALVsANxKzogiMDAAB6FxTp7wUVYAAAAABJRU5ErkJggg==>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHMAAAAYCAYAAADJcMJ/AAADbklEQVR4Xu2ZW4hOURTHl0Lu99zjkyTlVuJBPCiiXJJLSGnKCxmRSLx4wANSbkle5AEleRNJmnhRvFBSSg3hQeEFhcL6z1rL7LPPmdOZc86waf/q1zedfWa+ffbae+21zxBFIpFI5A+ynj2f41F28u+7w2MUe1x1+72H7eXct1m19nPsdKc9NPqyzewT9g37Qj3LDmWb2KV2sxGDGSalgjmIXax+YQ+QDBAcyx5kv7Or1dDowY5Q0fef7BGS53JpqA9J7htH8ruh0Y1dxr5nT5MEzmUu+4gkwFO8tjZWqQjaPK8NQX3Jtqj93MbAwMNhEG6xvZ3rGKCdKp6zDFgp+/SzK8GC+cyuI+m3D66dYe+z/b22Nk6pWMaY4S5T2Y/sFbV7sjko0LdrJP1Fvw0E0IKZNUBFwCQ+pJ9dxRySviMb5vVzL0m8UqBzLSoGwg0W0hD2l1fsNDV0UAMg1eKBAQYIaRfPUiWtVgnmMHYHO4vtwy5h17IDtB1/0+Lwmp2g1zsC9cAK/yKw1AQvsWtUFAu3SQbCvrQO0Gnbk4vq7395YCAwIA/YRexldmDijnKUCaZNIIzhSpLtCukRgbxK7atrofqDJIXmrcpcEOGv6nJqH8BJJGn1HknhUBeYPDZhiopNv+gD4r4LJKvzMTs+2VyaMsFEqoe72dkkKRQpf4b+vEXv26+izxv1Wilsr8zaL8ewrewNkjLfLfVDppmkmFvgNxSgoZ6k5FEHEwTHBHy61+ExdjilsTGDCFIryZgCdzu7qOI0gaC7TCSJkf+d2yijfonBTNJQ/7lgorRFDkfh4xc/YDDJuewpySYOQ8fSrPW5LsqkWcP6lDXGwE4TOJKgSHKxc/QmFal4K2XUEVb8oPKz6s9lPsleeoKkQ0X3rTw2kFTHnREP2hO/XACbgB0NXFmqBNP6lDXGABU4RAGUWaUyh1XEK/NlAZa+vSjwXxbgVRdS7112iNcWMpjZmOG7/IaKVAkmCp63lB5jA9U2vEOSKf3xRhH3XE29LEAZjBn/jWTZ4ougrYR3+rmdkm9SQsXOwNjTPpE80weSc1tdqbZKMHFKeEbpmsRnJHudpNLFcQaVPD5vUnuaxavI2mhQujjIcqbe/79QJZjY9zrzGhBBxwSAo6me7S3igP0X/z2KAxuJRCKRSCTyN/kFQuDlVx9RfHIAAAAASUVORK5CYII=>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAZCAYAAADnstS2AAAA2ElEQVR4Xu3SvQ7BUBwF8CtYfAwSidjEYrQwSMRkMRhswmjwAAZh8QQS8QI2E+8gMdlsBiQGi6fgnPY0zW0tbBIn+SXt/Z82vW2N+d3kYSFHaNpjO3FoyA2q1vRNeDc6QS4wC2UqG4gFZlY4ZIl4AcN9DCSrNScflfmMZ2lBBSawkpFfdXd/lZ6U4CFdv2pMH56yhqTW+XihzS5hKzO4Q9lqKGnYw1BSsIMxFKTuVo0pwkUL5JXb0JHaV2UeHIz7LikCc+O+Mu+r8t9xEoWEd6Lwgoxm9E8oLwGZKi4LR9U5AAAAAElFTkSuQmCC>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFgAAAAXCAYAAACPm4iNAAAC1klEQVR4Xu2YS6iNURTHlxBCHlfJY4SJd10hJVEMDEgiIiaSSF15xIBiiCQyMjNQ8poIA9ItMwZGJiSXRBFKKCn8/621nHP2Oft73Hvu9aX9q1/dzv7O7u6191p7fUckkUgkSjHInAevwHfwNXwEV8PJ8BQcbVaNEfCIeR92wwn1D7RgEjwDL2a4RXTuPjEeXjWfw1VwsI1x8nPwLTxvn1URHg4GlN6E1+GQhieaGQonwmvwlejhYtDpYvOF6IaNse+Uhl/kBA9MBjtkDvwM14cDFcMD/BQeDsZiMBsfSnxDOM9vuCYcKEoKcD8GmCnCOsP0n2G2ginDWjwzHKgYC833cGkwFoNr+gj3B5/7nXQB/oBLGoeLwRP5Cx4PPg9hgC/BUeFAxdhl9sApogGaBbskfuGtFQ1guCGLzE/wpLQ+3ZkMh7dFU58lYCAZK7XLpIjc2LzNZTAvm0z3YXA33AtvwAO1Rxvgxc0Y7IQbzLPwnrlMdO7STIVvROvPQLddvJ19MUWca2bhtZceFQ1sJ1wOf8LNf5+swU3rhrdE4+Ebugm+NDmPd1SlWAC/ie543g6xfelzL9jPsPZ+N5/BFVJbF7O1FbH6S3i5UZbQlcFYIXxy1tYsOkRrUNUDzNrLXpZug0/gHckuLbyDeLrD+ku2muwgOHdpPD1o7J/gCdgnvWxRMjgm+pZY1INmDK+/rL3ebvFEswQyU6eL1tIQ1t8e0QuxHnZX/uL1Ac5uHC4Ob1CWCdYcb0sc/r1dNMB5JeRf4/XX05rwUPB1f5poHa1vs8aZj6W5/2WmnhA92dRj0yv4RU7AUuG35g64B96FG+2ZqjNf9LQyiB5IXlrs3U+LBoxBHCn6Owv7ZMr0/yqN2fJFtLtie0fbAi8B7/vWiaZU7ObkBtDwR5F6D5mxy6Xd8H/liQyzkKnON9N2HZK8dfvam9adAlyMvHVHA5xIJBKJxH/DH5RVr7bXyP0sAAAAAElFTkSuQmCC>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABsAAAAXCAYAAAD6FjQuAAABcElEQVR4Xu3UvytGURgH8EcSQn5NbyjFgsHgRymDZDVTksEoi9HColgMMkhKGKTeLFLv5g+wKoPFIEIWWRjw/Xqe0z2uc/GmruV+67Pc53TOe5/nnlckyz+kDdbMpmcZ6mxNX6xGU1YrKmWQM4dwB/3QCCW2ph5OzC50Q7XVig43o1M4hgqv1gAbMGz+nFQPY1voEZa85x2wB63es2B6YUaiedA4DEFptOwjE+YVRkRnNQYLUOmtC6YdVmAWHsw+jMKF6IZ+tswNdMGq6MH8cT9mGgZhXnRzaoE5uBfd0MXNis7gQPSQKyjIL96sBsohD9uGraF4C92s6Ej0g+C6dXiGgWhpcprgUqJ5JMXNys3LhYfwMB7q7lti2MZb6DGhcBO+NVtGzV6N7WMbr0W/gW/D+XAO7g6F4t+t+P1i+NZvsBh7/iU7ErUg3oZa0fnwr4mbvZhz0SvDTMKT1YkfD3Va/VOqRP/3Ukmqh2XJEsw76j5O/803w98AAAAASUVORK5CYII=>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABIAAAAXCAYAAAAGAx/kAAABD0lEQVR4Xu3SsUtCURQG8CMqKA0qLjY41Bw4iP+Bg4EQOLS4NDW1F63RIA6CREO0i3+Ac2vgv9AUgeAihA01lN/H/a5enjze0qYf/AY9517fOU+znUgKLuUp4lQ9ebgRXxtAVfV1isKD3+aaDiGnOn/sXN7gQvW06lvpwi80g+94SRuGchDUYvNvFz3DDI71OQvXcGVujNhRfEoyhYm53VTgARpBX2Jq8gn35g6/wysUgr7EcDd+P2O4g74+t4K+xHA3xFd/Zm7BJ7CAEWQ2rfHxuwn3w/AwL+FlvDQxdfiS20iNY3E8jsqnpNj43UT/P4x/2g84kq10zL2ZH/iTOTyaG6sML0FtKT0e3mcfZAWL7TqUEBm4qQAAAABJRU5ErkJggg==>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEMAAAAXCAYAAABQ1fKSAAAChklEQVR4Xu2XS6hOURTHlzzyzDPyKHkNCCVFzAzIHZBEBgohxegOlBIxoDAjpaRkoCSZyYB0y8RjYiIDEyQGwoSBCf6/s/b27W/3ne+hr+9Mzq9+ddt7n3vPXmettfc1q6mp+Q9GBVfLO/Kz/CBfyCE5T14KTgnPDIKZwYvymbwtJybzk+UZeT3zgpyWrGMP+ZrNyfw/Zsi7wbfmi0aHuQnysvwkrwQHCe+BS8w/zPnm6WJuttwf/C3vy1nmHzcyXT4IEohlcnwyXzBVPpZPggQmZ6X8LncGq2C5/CK35xMBNo+v5Rs5p3m6eO/hYBqkJupgBMaapwwlsDTYirnmKcoLYRWwGfrY4nwigzKiVLYmY+vMew77xZbwB3jwbDaeQzBumTcrrAJ61Yj536dPbJRH5KRkDWyQv+RN8wxYKK+ZV0ApNA+aCelPGfQDujeB68VOweXkwqfmX52GfkoeDmPbGksL2DSnzke5Sd4zD0hbFpg/wC/s11G5Xu7q0VXFk+XE0qRf7JUnzTd30DwDyIScE/KPeflTIh1ZK3+an9stG0oCdw++SBXEpk05P7dG8HjncXFRxhbz9Qey8VKI9lfzXtCOeOGpKhjxbkPqH5Lv5FU5JlmTQ2awt66bPbU6EiyrW6LPUZTXZRmnzW+tvXi8eLI1sVfEfgFkyXvzfkN2k7UpBIk+8dL8otU1nNmUyh5rXMcj/LzP2pzLAyD2ivR+wVdno2TsObkojEfmm2fPjWy8I2ySQJBSj4Kk4jH5UO4Oa6piyBoZFDe9xvxiRekeDWNcx2MGfTNvnj/kK7kirOkajlm6Lu4w/z+As7xquCBxVOZ3BN43/Sesr9TBqKmpqanpnb9ea4gniSKgjgAAAABJRU5ErkJggg==>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABoAAAAYCAYAAADkgu3FAAABFklEQVR4Xu3Uv0uCQRwG8K+gYKBSIkjo4CIhlH+BbkI42KAOgqOzs2NDSzZFo7u4tLY4iNTY3CioQ0MQbUE25HPcI3YXwvv6xju9D3x44b7c3cv9EgnyT2nRYIcbOCFP8W2iQzqHT7iEY8rCFXxTg308pS56sJLVriZc0BRiRnWP3MEM0lb7KXzQCMJm2XnUHypTuBdzoIjofVrS2a+a6xToHYbQpA6MoQ8J8pQL+oKabA9CXvRSPUKOPEXtza79ycAcHihqVF3Gl4ni8ET2QVA5gmd4oZRZdp7NIVB6Vk2lLHrvbilklp2nLdtbb1/UoujlnECSXKci+l6s4Ide2aa88duFA/bxPVX5+/DarkW/n0GC+Jw1fIZJ301KNxwAAAAASUVORK5CYII=>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAZCAYAAADuWXTMAAAA8UlEQVR4Xu3Tr2qCYRTH8WeozT8MDTa1KEsGYeANDGE3IJjWdgeijIWVNQcWQYSt2MQrWNAsLCkLa8aBhoG2gd+DRzm+myIaLP7gU87vfeDw8LzOnbNKAEUM8Y0xnlUYT8isv9ak1Qe6SJnuVn2hj5DpXAKfqgKfLYlfddCyRQTv6KmgLT2po2QH9/hFQe1KDTk7OPiwrNjDCDG1d64wQRsXau/ICjNUvYUnq63idpjFD8p2+E/uVN4OLzHAq9u+dhKPSl7fRuS2p7hWNrJmwy0fkfiTow7LKg+Yq6Zb/hgveHOeS9oWeabiRkU363NOlwVdhCqO2OrP2QAAAABJRU5ErkJggg==>

[image12]: <data:image/png;base64,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>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABEAAAAYCAYAAAAcYhYyAAABDklEQVR4Xu3SvyuFURzH8a8Q5celLLJI6iaTrpQyUHdg4B9gMRmkbkarWUp2mVltBrtZKak7kW5d/4L353k+39xMBoPh+dSr2znf5znfc859IqpU+X2WcYhp68c6Tvyr8Tj2cGzz0ZNFnOEIz3aDTSzhBee4xAK27RX1cPTyWpRdP23FtVE84B41zzWsi6bnYgxDuMWV9bk2h3fseqzs2JvrRf5kEWUGbRxYRtvVw7oLRYvrbuQOw54vojv5iO/zZnRPj5j0OJuJms1iw7XiL3vClCnqom4X+RDZQse0u32sZvE6yi1qu3kf+l7aUZ4/o89BzeQULQxkcQSDOXC0mI6hD6032qFM/Jiv8i/zBdIbMSvtUD1KAAAAAElFTkSuQmCC>

[image14]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAE8AAAAWCAYAAACBtcG5AAAB8UlEQVR4Xu2XzStEYRTGj1Dkq7AgG4msZCFZsLDARmxQSlbykShSlK2VhZKFBTb+Akk2WPgTbCwVsmFBiZV8PI/33Dt3Lmbmjpl7lfdXv5hz75i3Z+5530PEYrFY/i+FcFStjb+UdXLUNrgBN+GgmDVFQS7sFbMOrod2af1bbHgxUg5vDB7BO/istsTdkTqlsMhfTAJDm1PHYTlshRfwBJbFbg2FPLgOF2A+bFC5ni2tuZSISbRPfh8e/wYNQh28VFfELJ4Mw3c4qa/DohpewXNY6anvwkfY7Km5RBVeI7xV92CB1rkGroWLDhN2wojK39lJlF1wCWvcOz1EFR5xFuhtiX4xT96MpxYF3PvoAxzwXXOJMjw/PCgOJLU9bxmeBnBCUqMdnsEbdVZ8+52XIOE1qTwRva6q/jqt/3xnctgqi/AYVvmuRUGxeigJvsy/EB6Dm4c7EvzUzjZLkuAACxLeT6Tbts6cNySmDZ324MnGpzARmW5b7rWvcM1Xd8LjzPeFKMPjRkz3xQTIJ5WnHV/zZ5gwvDcxcydxvlh2FEPt1vonU/AaPolJlt5rjVN1ENIJj08XP486n+/4Ajtit4YCD6ttMSMSZ00Oy5Sj1LSYIF1sePEECi+TpBPeX6UC9sBO1Rnes0Y6/9taLBZLGHwADPKVYL7mfQwAAAAASUVORK5CYII=>

[image15]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABIAAAAXCAYAAAAGAx/kAAAA30lEQVR4XmNgGDHAD4pnoWEDIOYA4lIscp5gnWiAB4pVgfg0EH8EYjsgZgViRiA2BuIHUNwIVQeyAC/IAeL/QBwB5YMMmwDEQVBMNKCaQYpA/ASIdwAxPxBXMZBoAAywAPFyIP4JxJsZIAENCieygAcQ/wPipQwUGAICwUD8F4ivA7E4mhzRwAyIZwJxDQNqoJMENIF4NgMkkJEDnRNZET4gD8VroDQIIAe6JVQMLwClUlDsgDCIjQxggT6FARLoWAM+A4hfMUDCAYZXAzEXVB6Udr4gyT2D4mSo/CgYBQCxgjDskX3fPwAAAABJRU5ErkJggg==>

[image16]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAYCAYAAADOMhxqAAAAtElEQVR4Xu3QvQ4BURQE4FOQKPxWIjqdSDYRSqUWL6BGolB6AFFuJGqPoBU9iYaWRuVNzNi56+roFDvJl2zuyZ09u2ZJ/iltmEhehjCDisRpwBRWsocQ6jCCkxTcBba2YCMHb9iBm8RvyUERjjJ2Az2fpeQOf77AcN+HcA0mBVtYy0f6cJeyzmoWFXSF3xloZkuL2ojNTA+uUJWFqSwDO5iLSxMu9l5p4M1evzEtfrKeJF/nCQ/KJEIr2R45AAAAAElFTkSuQmCC>