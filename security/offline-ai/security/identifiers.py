"""Pure offline checksum recognition for AU Medicare and NZ NHI identifiers.

NZ NHI rules: HISO 10046:2024; AU Medicare algorithm: ADHA HI software
conformance profile Appendix E. Validation is not proof of full anonymization.
"""
from __future__ import annotations
import re

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ"
_OLD = re.compile(r"^[A-HJ-NP-Z]{3}[0-9]{4}$")
_NEW = re.compile(r"^[A-HJ-NP-Z]{3}[0-9]{2}[A-HJ-NP-Z]{2}$")
_NHI = re.compile(r"(?<![A-Za-z0-9])(?:[A-HJ-NP-Z]{3}[0-9]{4}|[A-HJ-NP-Z]{3}[0-9]{2}[A-HJ-NP-Z]{2})(?![A-Za-z0-9])", re.I)
_MEDICARE = re.compile(r"(?<![0-9])[2-6][0-9]{3} ?[0-9]{4} ?[0-9] ?[0-9](?![0-9])")

def valid_nhi(candidate: str) -> bool:
    value = candidate.upper()
    if _OLD.fullmatch(value):
        parts = [_ALPHABET.index(c) + 1 for c in value[:3]] + [int(c) for c in value[3:6]]
        remainder = sum(v * w for v, w in zip(parts, (7, 6, 5, 4, 3, 2))) % 11
        if remainder == 0:
            return False
        check = 11 - remainder
        return (0 if check == 10 else check) == int(value[6])
    if _NEW.fullmatch(value):
        parts = [_ALPHABET.index(c) + 1 for c in value[:3]] + [int(c) for c in value[3:5]] + [_ALPHABET.index(value[5]) + 1]
        check = 23 - (sum(v * w for v, w in zip(parts, (7, 6, 5, 4, 3, 2))) % 23)
        return check <= 23 and value[6] == _ALPHABET[check - 1]
    return False

def valid_medicare(candidate: str) -> bool:
    digits = candidate.replace(" ", "")
    if len(digits) != 10 or not digits.isascii() or not digits.isdecimal() or digits[0] not in "23456":
        return False
    check = sum(int(d) * w for d, w in zip(digits[:8], (1, 3, 7, 9, 1, 3, 7, 9))) % 10
    return check == int(digits[8])

def identifier_spans(text: str) -> list[tuple[int, int]]:
    spans = [m.span() for m in _NHI.finditer(text) if valid_nhi(m.group())]
    spans.extend(m.span() for m in _MEDICARE.finditer(text) if valid_medicare(m.group()))
    return spans
