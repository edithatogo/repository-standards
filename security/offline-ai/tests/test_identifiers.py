from security.identifiers import valid_nhi, valid_medicare, identifier_spans

def test_legacy_nhi_checksum():
    assert valid_nhi("ABC1235")
    assert not valid_nhi("ABC1234")

def test_2026_nhi_checksum():
    assert valid_nhi("ZBN77VL")
    assert not valid_nhi("ZBN77VZ")
    assert valid_nhi("zbn77vl")

def test_medicare_checksum():
    assert valid_medicare("2123 4567 01")
    assert not valid_medicare("2123 4567 11")
    assert not valid_medicare("1123 4567 01")

def test_spans_preserve_boundaries():
    value = "Patient ABC1235 and ZBN77VL, Medicare 2123 4567 01."
    found = [value[a:b] for a,b in identifier_spans(value)]
    assert found == ["ABC1235", "ZBN77VL", "2123 4567 01"]

def test_avoid_substring_matches():
    assert not identifier_spans("XABC1235Z X21234567011")
