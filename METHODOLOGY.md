# Research and attack-feasibility methodology

## Purpose

This document explains how the Coldcard Mk3 seed-generation finding was investigated and how a defensive analyst can reason about possible key-space enumeration without publishing a theft-enabling workflow. The project validates the entropy-provider failure with synthetic inputs. It does not derive real wallets, search for real keys, or disclose private key material.

## Questions addressed

1. Which code path generated new-wallet entropy in the affected release?
2. Which runtime values influenced the fallback generator?
3. What changed in the fixed source and provider-selection boundary?
4. Can the affected and fixed upstream components be executed under matched synthetic controls?
5. What observations would be required to make a defensible claim about real-world theft?
6. Which facts remain unknown and therefore prevent a numeric claim about the practical search space?

## Source acquisition and provenance

The investigation preserved the vendor advisory, the Mk3 downloads page, the annotated affected source tag, the fixed v4-legacy revision, and the two dependency gitlinks. Local firmware images were hashed and parsed but are not redistributed. `evidence/provenance.json` and `evidence/source-dfu-mapping.json` record filenames, hashes, revisions, element hashes, mapping evidence, and mapping gaps.

The affected 4.1.9 source has a strong tag-to-release mapping through the annotated tag and upstream release-signature manifest. The supplied 4.2.0 image does not have an equivalent local tag or signed manifest entry tying it to one exact commit, so the report does not claim a reproducible fixed binary.

## Root-cause tracing

The analysis followed the call path from `shared/seed.py` to `shared/random.py`, libngu, and the globally linked `rng_get()` provider. It compared the affected tag and fixed revision, including board RNG code, MicroPython's fallback provider, Makefiles, and symbol checks.

The critical distinction is not a change to BIP-39 or the Python wallet path. In the affected build, libngu resolves to MicroPython's non-cryptographic fallback rather than the board hardware RNG. The fixed build exports the board provider under the expected global symbol, suppresses the fallback object, and checks the resulting symbols at build time.

## Executable differential validation

The harness compiles the exact pinned upstream libngu and provider C files. Narrow shims replace only hardware-register and MicroPython object plumbing that cannot run on the host. Every output is labeled `TEST-ONLY` and is never converted into a mnemonic, extended key, address, or transaction.

Matched controls are run in fresh processes:

- Affected positive control: repeated identical synthetic SysTick/UID/RTC tuples must produce one repeated digest.
- Affected contribution control: changing each modeled input must change the digest in the bounded test vectors.
- Fixed negative control: distinct synthetic hardware-RNG word streams must produce distinct digests in the bounded vectors.
- Fixed contribution control: changing each injected word must change the digest.
- Cross-check: the Python model must match the compiled upstream components for baseline vectors.

These controls prove provider dependence and deterministic repetition for repeated synthetic initial state. They do not measure physical entropy, estimate the distribution of real boot states, or prove that any specific wallet was generated from a tested state.

## Defensive feasibility analysis of enumeration

A real-world enumeration claim requires a bounded model of every unknown input that influenced the affected generator at first use. At a high level, an analyst would need to establish:

- the exact affected firmware and code path used to create the wallet;
- the device-specific value(s) entering initialization;
- the ranges and correlations of timing and RTC values at wallet creation;
- whether dice rolls or another independent entropy source were mixed in;
- whether a strong BIP-39 passphrase created an independent barrier;
- which script types and derivation paths were in use; and
- an independently justified time window and candidate population.

Without those facts, multiplying guessed ranges produces an attractive but unsupported work-factor number. This repository therefore reports only bounded synthetic state counts and does not extrapolate them into a count of vulnerable wallets or a practical attack cost.

A defensible feasibility study should publish aggregate measurements such as candidate-state counts, elapsed time on synthetic targets, false-positive controls, and confidence bounds. It should not publish real candidate seeds, private keys, precomputed wallet tables, target selectors, acceleration kernels, or executable wallet-search code.

## Theft and balance attribution standard

Weak entropy alone does not prove theft. A report should classify on-chain evidence separately:

- Confirmed affected wallet: the owner or vendor attests that the wallet was created on an affected device/version, with corroborating records.
- Confirmed unauthorized spend: the owner identifies a transaction as unauthorized and provides a verifiable transaction ID or signed statement.
- Attributed to this vulnerability: evidence links the unauthorized spend to exploitation of this exact seed-generation defect rather than phishing, backup compromise, malware, passphrase failure, or another cause.
- Amount stolen: value actually transferred without authorization, excluding change returned to the victim and avoiding double-counting through later hops.
- Current balance: a time-stamped on-chain observation, not the amount originally stolen.

For each public case, retain source URL, publication time, address or transaction ID, chain/network, block height/time, value calculation, attribution strength, and uncertainty. Use transaction IDs and public addresses for verification; never use or publish private keys or seed phrases. An absence of public cases means “no public case verified,” not “no theft occurred.”

`PUBLIC_INCIDENTS.md` and `evidence/public-incidents.json` implement this
classification. Cumulative analyst estimates are never added together; a later
hop is not a new loss; consolidation output and current balance are not assigned
to one victim unless the source identifies that victim's input. Fingerprint-only
clusters remain suspected attribution when no public seed-to-address
reconstruction or equivalent defect-specific proof exists.

## Why operational key-search details are excluded

A private key is direct control over funds. Publishing recovered keys, real-wallet candidate material, or a complete brute-force recipe would create immediate theft risk and would expose victims who may not have migrated. It is unnecessary to establish the root cause, test the provider boundary, estimate a synthetic work factor, or verify public transaction evidence.

Accordingly, coldhax intentionally excludes:

- real private keys, seed phrases, and wallet files;
- BIP-39 generation and wallet key derivation;
- address-targeted candidate checking;
- optimized enumeration, GPU/FPGA kernels, or distributed cracking;
- real device captures that could narrow a victim's state space; and
- instructions for spending or moving recovered funds.

## Reproducibility and review

The public repository contains the synthetic model, exact-upstream component harness, tests, generated evidence, and artifact hashes. Raw firmware, upstream source clones, local logs, disassemblies, binaries, and private state are excluded. `setup_sources.sh` retrieves pinned public upstream source revisions for the native harness.

Reproduction is successful only when the pinned revisions match, the native harness rebuilds, all controls pass, the Python tests pass after the final edit, JSON validates, and `sha256sum -c evidence/artifact-hashes.txt` succeeds. Limitations and unproven claims remain explicit in `REPORT.md`.
