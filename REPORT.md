# Coldcard Mk3 seed-generation finding

## Executive finding

Coldcard Mk3 4.1.9's `New Wallet` Python path requests 32 bytes from
`ngu.random`, hashes those bytes with SHA-256, and uses the digest as 256-bit
BIP-39 entropy. The Python seed path itself is unchanged in the fixed source.
The security boundary failed below it: libngu expected a global C `rng_get()`
provider, but the Mk3 board's hardware provider was only available through the
private `rng_get_or_fault()` and Python wrappers. The linked global provider was
therefore MicroPython's non-cryptographic Yasmarang fallback PRNG. Its one-time
initializer used SysTick, one fixed device UID word, and two RTC register values
rather than the STM32 hardware RNG.

Fix commit `4543629941a83a3e2788ac06a12b208338cb8314` exports the board hardware
function as `rng_get()`, suppresses MicroPython's fallback `rng.o`, and adds a
link-output symbol check. This changes libngu's source of words without changing
`shared/seed.py` or the libngu/micropython gitlinks.

This report demonstrates the mechanism by executing the exact pinned upstream
libngu and provider C files with narrow synthetic register shims (evidence tier
b), then cross-checking those outputs against the corrected model. It does not
claim device execution, full firmware emulation, or measurement of the STM32
physical RNG.

## Versions and provenance

- Affected release tag: `2023-06-26T1241-v4.1.9`.
  - Annotated tag object: `79a5eb06c18322d6173e75d07c409af81bad984f`.
  - Peeled commit: `bc511ee34c8e7abaa0a4837571af9b6b8a4f9ef2`.
- Fixed release source: branch `v4-legacy` at
  `43770339b0b97753b883c58764ce17f081350b30`.
  - The local repository has no 4.2.0 tag.
  - Version becomes 4.2.0 at `8a71a5a66727dca943d860163450faa9f7bc7488`;
    the RNG fix is `4543629941a83a3e2788ac06a12b208338cb8314`;
    HEAD updates generated build-date/version data.
- Affected DFU SHA-256:
  `f6fb19d95bd1e38535f137bed60cafbfcd52379a686e3d12f372f881d78e640e`.
- Fixed DFU SHA-256:
  `a84666a5ca33293c7f633721c2e1d43a00ed6bcb10968acaa63821e725601b7f`.
- Both source revisions pin libngu
  `356b9137cf7ddf5de66ec4cdc0a4d757b2e42790` and MicroPython
  `f3b2a8c2e988fc9cdf16812bb48a9964911329a9`.

`evidence/provenance.json` records all local input hashes, source URLs, generation
time, Git revisions, and each DfuSe element's address, size, and hash. The two
required submodules are initialized at exactly those gitlinks; neither gitlink nor
either upstream worktree was modified.

## Executed upstream component path (tier b)

The native harness compiles the pinned source files themselves rather than copied
implementations:

- libngu `ngu/random.c` SHA-256
  `812585e47b2f9251693280c95b5e58558cbd564d62e4398b17388f9cb5198abb`;
- affected MicroPython `ports/stm32/rng.c` SHA-256
  `66ecfdf8111b80aa09456d49751100466f9e596a20839af32b5e6529b4e26742`;
- fixed board `stm32/COLDCARD/rng.c` SHA-256
  `50629f09b7f87a2381c86c358de525a2188d6b57e1e6903b5b7fdb13dc5de839`.

The affected build undefines host `__linux__` only for libngu `random.c`, matching
the STM32 build's `MICROPY_PY_STM` provider selection instead of libngu's host
`random()` branch. Its shim supplies only SysTick, UID, RTC time, and RTC
subsecond. The fixed shim executes the exact board `rng_get_or_fault()` and global
`rng_get()` while `HAL_GetTick()` delivers each synthetic test word through
`RNG->DR`. MicroPython object APIs not reached by entropy generation are inert
stubs and are removed by section garbage collection.

Each run is a fresh process. For both revisions, 256 identical provider inputs
produce one unique raw and SHA-256 output, and 256 varied provider inputs produce
256 unique outputs. A high-bit flip in each of the four affected register inputs
and each of the eight fixed hardware words changes the digest. The security
distinction is the provider boundary: fixed execution depends on hardware RNG
deliveries; affected execution has no input beyond the non-TRNG register tuple.
Complete controls, samples, revisions, source hashes, and binary hashes are in
`evidence/upstream-execution.json`.

The harness hashes libngu's 32 output bytes with local OpenSSL. This is equivalent
to, but does not execute, the unchanged Python `ngu.hash.sha256s` call. It emits
only synthetic `TEST-ONLY` entropy bytes and implements no BIP-39 or wallet code.

The complete Unix simulator was rejected as weaker evidence for this mechanism:
its checked-in variant does not enable libngu, and libngu selects host `random()`
under Linux rather than the STM32 provider/link path at issue.

## Source trace

### Seed path (unchanged)

At the affected tag, `shared/seed.py:364-377`:

1. `make_new_wallet()` calls `random.bytes(32)`.
2. `shared/random.py:5-11` aliases that operation to `ngu.random.bytes`.
3. The code applies `ngu.hash.sha256s(seed)` before the BIP-39 word path.

Dice mixing is independent. `shared/seed.py:292-348` initializes SHA-256 with the
existing device-generated seed and updates it with each entered roll. This is
consistent with the advisory's statement that independent dice entropy survives
the bug; this project does not assess user dice quality.

### Hardware and binding path

In 4.1.9, `stm32/COLDCARD/rng.c:61-80` defines a **static**
`rng_get_or_fault()` which starts the STM32 RNG, waits for `RNG_SR_DRDY`, reads
`RNG->DR`, and faults on timeout. The exported Python functions and
`random_buffer()` call this private function, but no global `rng_get()` exists.

The fixed source adds:

- `stm32/COLDCARD/rng.c:82-85`: global `rng_get()` delegates to
  `rng_get_or_fault()`.
- `stm32/COLDCARD/rng.h:6`: declaration of global `rng_get()`.
- `stm32/COLDCARD/mpconfigboard.mk:69-75`: replaces MicroPython's fallback
  `rng.o` with an empty object and deliberately poisons `pyb_rng_yasmarang`.
- `stm32/Makefile:49-69`: verifies the fallback object defines no symbols and
  the board object defines global `rng_get`.

No source change occurs in `shared/seed.py`, and the two dependency gitlinks are
identical. The actual security fix is symbol/provider selection at link time.

## Firmware evidence

The local DFUs parse as DfuSe images with two elements. In each image the main
firmware is 729,600 bytes at `0x08008000`; the identical 30,720-byte element at
`0x08000000` has SHA-256
`d6b1d781333e996d18ff8d8388263135b6c29e1265d5c97812de350f82b7f127`.
The main firmware element differs between releases. Embedded strings identify
4.1.9/2023-06-26 and 4.2.0/2026-07-31 and contain libngu's `random.c` path.

Independent binary disassembly found the fallback at
`0x0803df94-0x0803e000` in the affected main image. Its first-call initializer:

1. reads SysTick current value from `0xe000e018`;
2. reads the STM32 UID word at `0x1fff7590` and XORs it into the initial pad;
3. reads RTC time from `0x40002800` into `n`;
4. reads RTC subsecond at `0x40002828` into `d`; and
5. starts the Yasmarang transition with an initially zero byte state.

The Thumb instructions at `0x0803dfc4-0x0803e000` implement the transition
transcribed in the model. The fixed build removes this implementation and routes
the consumer to the board RNG provider. Raw extracted images and full
disassemblies remain private under `state/`; they are not needed to run the
harness.

This does not prove the supplied fixed DFU was reproducibly built from HEAD. The
submodules are now initialized, but no 4.2.0 tag or signed release-manifest entry
maps that DFU to an exact commit. Docker cannot access its daemon socket and the
host has no ARM cross-compiler, so the historical Alpine build recipe could not
be exercised. For 4.1.9, the annotated source tag, repository signature manifest,
filename, and DFU hash align. `evidence/source-dfu-mapping.json` preserves the
exact evidence and blockers; no source/binary equivalence is claimed.

## Safe model and proof gates

`coldhax_model.py` transcribes the shared Yasmarang transition and now models both
layers visible in exact upstream execution: MicroPython's register-initialized
affected provider and libngu's fixed-state whitening PRNG. The fixed path accepts
an injected stream of eight 32-bit words, marking the STM32 peripheral as outside
the model. Tests require model outputs to equal compiled-upstream outputs for the
baseline vectors. No mnemonic or key derivation is implemented.

Executed bounded gates (`evidence/proof-gates.json`):

- Positive control: 256 modeled cold boots supplied the same synthetic
  SysTick/UID/RTC tuple produce exactly one unique output. This directly
  demonstrates repetition when the observable initializer tuple repeats; it
  does not claim every real reboot has that same tuple.
- Negative control: 256 distinct deterministic `TEST-ONLY` injected hardware
  streams produce 256 unique SHA-256 outputs. Flipping one bit in each of the
  eight input words changes the result, demonstrating that all 256 injected bits
  reach the hash output in this bounded set.

These are deterministic functional tests. They do not estimate entropy, prove
uniformity, or validate the physical STM32 RNG. No p-values or broad statistical
claims are appropriate for these gates.

## Vendor claims versus demonstrated facts

Vendor claims (from the preserved advisory):

- Mk3 firmware 4.0.1 through 4.1.9 inclusive is affected; 4.2.0 fixes new seed
  generation.
- The advisory, updated August 1, expands scope beyond this Mk3 investigation:
  seeds generated on Mk4/Mk5 before standard 5.6.0 or Edge 6.6.0X, and on Q
  before standard 1.5.0Q or Edge 6.6.0QX, are also affected. It describes their
  impact as about 72 bits of entropy rather than the expected 128 bits. This
  project has not independently validated those models or release tracks.
- Existing affected seeds are not repaired by an update.
- At least 50 fair, private, independent dice rolls provide at least 128 bits of
  dice entropy; 99 provide approximately 256 bits.
- A strong unique BIP-39 passphrase adds an independent barrier.

Independently demonstrated here:

- The tagged 4.1.9 seed path obtains 32 bytes through libngu and hashes them.
- The source fix changes the global provider used by libngu from the fallback
  path to the board hardware path and adds build-time symbol assertions.
- The affected DFU contains the fallback initializer and transition using
  SysTick, UID, and RTC values rather than the hardware RNG.
- Exact pinned upstream libngu plus affected/fixed provider components execute
  with narrow synthetic register shims and pass matched controls.
- The affected executable path repeats for an identical initializer tuple; the
  fixed executable path preserves changes in each supplied hardware word.

Not independently demonstrated:

- The complete vendor-claimed affected version range.
- A numeric real-world Mk3 entropy estimate, exploitability, or any wallet impact.
- Physical hardware RNG quality or behavior.
- Execution of either complete upstream firmware image in a simulator/device.
- Reproducible source-to-DFU identity.
- Dice or passphrase entropy claims.

## Enumeration and incident-attribution boundary

`METHODOLOGY.md` records the complete safe research methodology. Conceptually,
assessing enumeration feasibility requires bounding every unknown value that
influenced the affected generator at first use and accounting for independent dice
or passphrase entropy. This project does not have defensible measurements for the
real distribution of those values, so it does not publish a numeric real-world
search-space estimate.

The repository also does not implement BIP-39 generation, key derivation,
address-targeted candidate checking, optimized enumeration, or spending. It never
collects or publishes real private keys. Those artifacts are unnecessary to prove
the provider-selection defect and would create direct risk to users who may not
have migrated.

Any claimed stolen balance must be supported by a public transaction identifier,
an owner/vendor statement that the wallet was generated on an affected release,
and evidence distinguishing exploitation of this defect from backup compromise,
phishing, malware, or another cause. Amounts must exclude victim change and avoid
double-counting later hops. Current balance and amount stolen are separate,
time-stamped measurements. A lack of publicly verified cases must be reported as
such rather than interpreted as proof that no theft occurred.

`PUBLIC_INCIDENTS.md` records the public evidence found through 2026-08-04
13:02:05 UTC. Galaxy Research's August 3 high-confidence cumulative estimate is
1,596 BTC across approximately 7,300 source addresses in three victim-confirmed
major waves plus 14 smaller incidents. Galaxy says 73 individual victims
contacted its analyst, but publishes no complete address/transaction corpus; the
aggregate cannot be independently reconstructed and is not a seed-to-address
proof. It supersedes rather than adds to the earlier 1,367.05 BTC / 4,585-address
snapshot. An August 4 follow-up raises the smaller-footprint count to 15 and
reports Footprint O as 12 BTC from 126 addresses, identified through one
anonymous victim report of less than 1 BTC. It publishes no revised cumulative
headline or identifiers, so no derived addition is made.

Three public Chainabuse owner reports materially improve transaction-level
evidence. One owner reports an exact 5.39099821 BTC Mk3 loss; its cited
transaction pays exactly that amount and then moves once into a published Galaxy
Wave 3 vault. A second owner identifies three Coldcard-hack transactions paying
0.17998515 BTC into a P2TR sink. A third Mk3 owner publishes 23 source addresses
inside the August 2 consolidation; explorer data matches every input and their
exact 5.13591373 BTC sum. None is added again to an overlapping transaction,
cluster, or Galaxy total. The P2TR sink is part of a 46.97389047 BTC
three-destination community sample, but only the owner's three identified
receipts are owner-corroborated; the remainder is fingerprint attribution.

Other owner/witness reports identify Coldcard-origin wallets in the sweeps,
including one Mk3 testing-wallet report with a public transaction ID, an owner
report of 18.25245043 BTC drained from three Coldcard wallets, and a direct owner
report of 2 BTC drained from a Mk3 wallet. A separate analyst report says a
nearly 30 BTC Coldcard victim had approximately 17 BTC peeled through THORChain
to Duel.com, but publishes no public on-chain identifiers. Those exact owner
reports and the approximate analyst report cannot be independently verified or
added to cumulative totals. No reviewed source publicly reconstructed a victim
seed and matched it to a drained address, so defect attribution remains
suspected rather than conclusive. Current destination balances remain separate,
and cumulative waves, fees, and later hops are not added. A potential fourth
wave was revised to a stated 709-address / 448.73 BTC core after multisig
exclusions. Galaxy's later thread calls it medium-high confidence and reports a
2,055 BTC total if included, but still excludes it from the 1,596 BTC headline
because no specific victim has confirmed inclusion. The earlier correction
arithmetic, newer total, and unpublished corpus do not fully reconcile, so no
Wave 4-only amount is derived here.

## Remediation

Follow the vendor advisory, not this research harness: install Mk2/Mk3 firmware
4.2.0 or later, Mk4/Mk5 standard 5.6.0 or Edge 6.6.0X or later, or Q standard
1.5.0Q or Edge 6.6.0QX or later before generating a replacement. Standard and
Edge are separate tracks. An update does not repair an existing seed. Treat
migration as a careful operational procedure, verify backups and
addresses on trusted hardware, test with a small transfer, and retain the old
backup until confirmation. Never enter seed words or dice sequences into this
project or a networked service.
