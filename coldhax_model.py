#!/usr/bin/env python3
"""Safe source-level model of the Mk3 seed entropy path.

All outputs are synthetic and TEST-ONLY. This module does not implement BIP-39,
key derivation, address generation, or wallet searching.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable

MASK32 = (1 << 32) - 1


@dataclass
class Yasmarang:
    """Yasmarang transition used by MicroPython and libngu.

    The transition is verified against affected-image Thumb code at
    0x0803dfc4-0x0803e000 and the pinned upstream C sources. Initial state is
    supplied explicitly because each upstream layer initializes it differently.
    """

    pad: int
    n: int
    d: int
    dat: int = 0

    def word(self) -> int:
        self.pad = (self.pad + self.dat + self.d * self.n) & MASK32
        self.pad = ((self.pad << 3) + (self.pad >> 29)) & MASK32
        self.n = self.pad | 2
        self.d ^= ((self.pad << 31) + (self.pad >> 1)) & MASK32
        self.d &= MASK32
        self.dat ^= self.pad ^ (self.d >> 8) ^ 1
        self.dat &= 0xFF
        return (
            self.pad
            ^ ((self.d << 5) & MASK32)
            ^ (self.pad >> 18)
            ^ (self.dat << 1)
        ) & MASK32

    def bytes(self, count: int) -> bytes:
        """Emit transition words as little-endian bytes."""
        if count < 0:
            raise ValueError("count must be non-negative")
        out = bytearray()
        while len(out) < count:
            out.extend(self.word().to_bytes(4, "little"))
        return bytes(out[:count])


@dataclass(frozen=True)
class AffectedRegisterInputs:
    """Values read by the fallback's one-time initializer (all uint32)."""

    systick_current: int
    uid_word: int
    rtc_time: int
    rtc_subsecond: int

    def prng(self) -> Yasmarang:
        values = (self.systick_current, self.uid_word, self.rtc_time, self.rtc_subsecond)
        if any(not 0 <= value <= MASK32 for value in values):
            raise ValueError("register input outside uint32")
        return Yasmarang(
            pad=self.systick_current ^ self.uid_word,
            n=self.rtc_time,
            d=self.rtc_subsecond,
        )


TEST_ONLY_AFFECTED_INPUTS = AffectedRegisterInputs(
    systick_current=0x00543210,
    uid_word=0x54455354,
    rtc_time=0x00123456,
    rtc_subsecond=0x00000123,
)


def affected_seed_entropy(inputs: AffectedRegisterInputs) -> bytes:
    """Model 4.1.9's two upstream PRNG layers and SHA-256 seed step."""
    provider = inputs.prng()
    return _libngu_seed_entropy(provider.word() for _ in range(8))


def fixed_seed_entropy(hardware_words: Iterable[int]) -> bytes:
    """Model 4.2.0 with injected TEST-ONLY hardware-RNG words.

    Hardware behavior is deliberately not simulated. Injection marks the
    hardware boundary while retaining libngu's exact mixing and SHA-256 path.
    """
    return _libngu_seed_entropy(hardware_words)


def _libngu_seed_entropy(provider_words: Iterable[int]) -> bytes:
    """Model pinned libngu random.c mixing and the subsequent SHA-256 call."""
    raw = bytearray()
    whitening = Yasmarang(pad=0x0A8CE26F, n=69, d=233)
    last = 0
    for word in provider_words:
        if not 0 <= word <= MASK32:
            raise ValueError("provider word outside uint32")
        if word == last:
            raise ValueError("consecutive provider words repeat")
        last = word
        raw.extend((word ^ whitening.word()).to_bytes(4, "little"))
        if len(raw) >= 32:
            return sha256(bytes(raw[:32])).digest()
    raise ValueError("at least eight provider words are required")


def synthetic_hardware_words(test_case: int) -> list[int]:
    """Deterministic TEST-ONLY controls; not an RNG and not wallet material."""
    if test_case < 0:
        raise ValueError("test_case must be non-negative")
    return [((0x54455354 + test_case * 0x9E3779B9 + i) & MASK32) for i in range(8)]
