"""Seeded metamorphic checksum fixtures; no external fuzzing runtime."""
import random
from security.identifiers import valid_nhi, valid_medicare, identifier_spans

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ"
WEIGHTS = (7, 6, 5, 4, 3, 2)

def test_generated_medicare_and_check_digit_mutations():
    rng = random.Random(20261111)
    for _ in range(800):
        first = str(rng.randrange(2, 7)) + "".join(str(rng.randrange(10)) for _ in range(7))
        check = sum(int(d)*w for d,w in zip(first,(1,3,7,9,1,3,7,9))) % 10
        candidate = first + str(check) + str(rng.randrange(10))
        assert valid_medicare(candidate)
        invalid = first + str((check+1) % 10) + candidate[-1]
        assert not valid_medicare(invalid)
        assert identifier_spans(" " + candidate + " ") == [(1, 11)]

def test_generated_legacy_nhi_and_mutations():
    rng = random.Random(20261112)
    found = 0
    for _ in range(800):
        letters = "".join(rng.choice(ALPHABET) for _ in range(3))
        digits = "".join(str(rng.randrange(10)) for _ in range(3))
        values = [ALPHABET.index(c)+1 for c in letters] + [int(c) for c in digits]
        remainder = sum(x*y for x,y in zip(values,WEIGHTS)) % 11
        if remainder == 0: continue
        check = 11 - remainder
        check = 0 if check == 10 else check
        candidate = letters + digits + str(check)
        assert valid_nhi(candidate)
        assert valid_nhi(candidate.lower())
        assert not valid_nhi(candidate[:-1] + str((check+1) % 10))
        found += 1
    assert found > 600

def test_generated_new_nhi_and_mutations():
    rng = random.Random(20261113)
    for _ in range(800):
        letters = "".join(rng.choice(ALPHABET) for _ in range(3))
        digits = "".join(str(rng.randrange(10)) for _ in range(2))
        letter = rng.choice(ALPHABET)
        values = [ALPHABET.index(c)+1 for c in letters] + [int(c) for c in digits] + [ALPHABET.index(letter)+1]
        index = 23 - (sum(x*y for x,y in zip(values,WEIGHTS)) % 23)
        candidate = letters + digits + letter + ALPHABET[index-1]
        assert valid_nhi(candidate)
        assert not valid_nhi(candidate[:-1] + ALPHABET[index%24])
