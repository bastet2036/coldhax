# Third-party notices

Coldhax's root MIT license covers only original coldhax files. The project fetches and compiles pinned upstream source during local reproduction; that upstream source and the resulting locally linked binaries remain subject to their own terms.

## Coldcard firmware

- Source: https://github.com/Coldcard/firmware
- Pinned fixed revision: `43770339b0b97753b883c58764ce17f081350b30`
- Affected tag/commit: `2023-06-26T1241-v4.1.9` / `bc511ee34c8e7abaa0a4837571af9b6b8a4f9ef2`
- License file in the upstream repository: `COPYING-CC`
- Terms: MIT license with Commons Clause restriction. Consult the upstream license before redistribution or commercial use.

Coldhax does not redistribute the firmware source, firmware images, or complete firmware binaries.

## libngu

- Source: the `external/libngu` gitlink in the Coldcard firmware repository
- Pinned revision: `356b9137cf7ddf5de66ec4cdc0a4d757b2e42790`
- Compiled file: `ngu/random.c`, fetched locally
- Upstream license: “Licensed for Bitcoin Only”; consult the exact upstream `LICENSE` before use.

Coldhax does not redistribute libngu source. The native harness is specifically limited to defensive Bitcoin-wallet research.

## MicroPython

- Source: the `external/micropython` gitlink in the Coldcard firmware repository
- Pinned revision: `f3b2a8c2e988fc9cdf16812bb48a9964911329a9`
- Compiled file: `ports/stm32/rng.c`, fetched locally
- License: MIT; consult the upstream `LICENSE`.

## Yasmarang

The report discusses and models the Yasmarang transition present in the pinned upstream fallback implementation. Attribution and licensing statements for that implementation should be read from the pinned upstream source and repository history. Coldhax's model is provided only for the documented synthetic differential controls.

## OpenSSL

The native harness dynamically links the host OpenSSL `libcrypto` implementation for SHA-256 after upstream libngu emits 32 TEST-ONLY bytes. OpenSSL is a build/runtime dependency and is not vendored by this repository. Consult the OpenSSL license applicable to the installed version.

## Non-redistributed local inputs

Vendor DFU files, preserved vendor HTML, upstream clones, disassemblies, native objects/binaries, logs, and local state are excluded by `.gitignore`. Their hashes and provenance are recorded where useful, but no license under the coldhax root `LICENSE` is asserted for them.
