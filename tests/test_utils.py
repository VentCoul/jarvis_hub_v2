import numpy as np
from modules.utils import normalize_id, normalize_barcode


class TestNormalizeId:
    def test_strips_leading_zeros(self):
        assert normalize_id("000123") == "123"

    def test_removes_plus_and_float_suffix(self):
        assert normalize_id("+++123.0") == "123"

    def test_strips_whitespace(self):
        assert normalize_id("  123  ") == "123"

    def test_nan_returns_empty(self):
        assert normalize_id(np.nan) == ""

    def test_all_zeros_returns_single_zero(self):
        assert normalize_id("0000") == "0"

    def test_float_value(self):
        assert normalize_id(123.0) == "123"


class TestNormalizeBarcode:
    def test_preserves_leading_zeros(self):
        assert normalize_barcode("0123456789012") == "0123456789012"

    def test_removes_plus_and_float_suffix(self):
        assert normalize_barcode("+++0123456789012.0") == "0123456789012"

    def test_strips_whitespace(self):
        assert normalize_barcode("  0123  ") == "0123"

    def test_nan_returns_empty(self):
        assert normalize_barcode(np.nan) == ""

    def test_float_value_no_zero_strip(self):
        # A barcode read as float still keeps its integer digits intact.
        assert normalize_barcode(123.0) == "123"
