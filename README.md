# Coldcard Mk3 seed-generation finding: upstream C execution

This authorized defensive project now reaches evidence tier **(b)**: pinned upstream
libngu and MicroPython/Coldcard C entropy components execute natively with narrow,
deterministic hardware-register shims. All emitted bytes are conspicuously marked
`TEST-ONLY` and are never converted into mnemonic words, keys, or wallets.

`REPORT.md` contains the technical findings. `METHODOLOGY.md` documents the
source-tracing, executable differential controls, non-operational assessment of
enumeration feasibility, and the evidence standard for attributing public thefts.
`PUBLIC_INCIDENTS.md` applies that standard to current public reports and
time-stamped on-chain observations. It deliberately excludes real private keys
and executable wallet-search methods.

It does **not** use a real wallet, derive keys, search key space, interact with
hardware, emulate a complete device, or assess the physical STM32 RNG.

## Strongest result

The native harness compiles, without copying their implementations:

- pinned libngu `random.c` at gitlink
  `356b9137cf7ddf5de66ec4cdc0a4d757b2e42790`;
- affected provider `ports/stm32/rng.c` at pinned MicroPython gitlink
  `f3b2a8c2e988fc9cdf16812bb48a9964911329a9`; and
- fixed provider `stm32/COLDCARD/rng.c` at v4-legacy revision
  `43770339b0b97753b883c58764ce17f081350b30`.

For each control the harness starts a fresh process, preserving upstream static
cold-start initialization. With 256 identical synthetic inputs, each revision is
deterministic (one output). With 256 varied inputs, each produces 256 outputs.
The important boundary difference is executable: affected 4.1.9 consumes only the
injected SysTick/UID/RTC tuple, while fixed 4.2.0 consumes eight injected hardware
RNG data-register deliveries. One high-bit flip in every provider input changes
the resulting SHA-256 value in the bounded controls.

`evidence/upstream-execution.json` binds these claims to source hashes, git
revisions, native binary hashes, controls, and synthetic sample bytes. SHA-256 is
provided by local OpenSSL after exact upstream libngu emits 32 bytes; this stands
in for the unchanged `ngu.hash.sha256s` Python call and is an explicit boundary.

## Reproduce

Requirements: Python 3.11+, Git, GCC, OpenSSL development headers/library, and
make-compatible POSIX shell tools. Retrieve the exact public upstream revisions
once, then the native harness can run without network access.

```sh
git clone https://github.com/bastet2036/coldhax.git
cd coldhax
./setup_sources.sh
python3 run_upstream_evidence.py
python3 -m unittest -v
python3 -m json.tool evidence/upstream-execution.json >/dev/null
python3 -m json.tool evidence/source-dfu-mapping.json >/dev/null
python3 -m json.tool evidence/public-incidents.json >/dev/null
python3 -m py_compile coldhax_model.py generate_evidence.py run_upstream_evidence.py test_coldhax_model.py test_public_incidents.py
sha256sum -c evidence/artifact-hashes.txt
```

`generate_evidence.py` additionally parses locally acquired vendor DFU files and
preserved advisory HTML. Those inputs are intentionally not redistributed. Its
committed outputs are included for review, but a fresh full regeneration requires
the exact files and hashes listed in `evidence/provenance.json`.

The native controls execute 1,048 fresh harness processes in total. Expected
primary gates for each revision are 1/256 unique outputs for repeated identical
provider input and 256/256 for varied provider input. These are functional
controls, not randomness statistics.

## Evidence tiers and boundaries

- **Achieved tier (b):** exact pinned upstream C entropy components execute with
  narrow register/HAL shims. The affected shim supplies SysTick, UID, RTC time,
  and RTC subsecond. The fixed shim delivers synthetic RNG words through the
  exact board provider's `HAL_GetTick`/`RNG->DR` boundary.
- **Not achieved tier (a):** the Unix simulator does not represent the affected
  STM32 link/provider path; its checked-in configuration does not enable libngu,
  and libngu's Unix branch uses host `random()`. A full simulator would therefore
  obscure rather than execute the affected mechanism.
- The Python model remains a cross-check. It now includes both Yasmarang layers:
  the affected MicroPython provider and libngu's independent whitening layer.
- MicroPython object plumbing is stubbed and garbage-collected from the native
  binaries. The actual entropy functions are upstream source, not transcriptions.

## Source-to-DFU status

`evidence/source-dfu-mapping.json` records the result. The 4.1.9 source tag,
repository release-signature manifest, filename, and local DFU hash align. The
provided 4.2.0 DFU has no local source tag or signed release-manifest entry, so its
exact commit cannot be proven. Exact rebuild work is blocked in this environment
by Docker socket permission and the absent ARM cross-compiler. These are mapping
limits; no match was forced.

## Files

- `harness/` — native build, shims, and MicroPython API stubs outside upstream.
- `setup_sources.sh` — fetches and verifies pinned public upstream source only.
- `METHODOLOGY.md` — safe research, feasibility, and attribution methodology.
- `PUBLIC_INCIDENTS.md` — public case accounting with attribution limits,
  transaction evidence, and separately time-stamped destination balances.
- `run_upstream_evidence.py` — rebuilds and runs both exact-upstream controls.
- `evidence/upstream-execution.json` — machine-readable tier-(b) results.
- `evidence/source-dfu-mapping.json` — machine-readable mapping evidence/blockers.
- `evidence/public-incidents.json` — machine-readable public incident observations.
- `coldhax_model.py` / `test_coldhax_model.py` — model and native/model cross-checks.
- `test_public_incidents.py` — incident-schema, accounting, attribution, and
  obvious-sensitive-material regression checks.
- `generate_evidence.py` — provenance, DFU parsing, model gates, artifact hashes.
- `logs/` and `state/` — private raw build/execution and investigation records.

Never feed seed words, keys, wallet files, device captures, or real hardware RNG
samples into this project. Every generated byte is synthetic and unsuitable for
wallet use.
