import pandas as pd

def normalize_id(val):
    """
    Robust normalization for IDs and Barcodes:
    - Removes '+++' (common for scanners)
    - Removes '.0' (if float-originated)
    - Strips whitespace
    - Removes leading zeros, but keeps at least one char if it was '0'
    """
    if pd.isna(val):
        return ""
    s = str(val).strip().replace('+', '')
    s = s.split('.')[0]
    normalized = s.lstrip('0')
    return normalized if normalized != "" else "0"


def normalize_barcode(val):
    """
    Normalization for Barcodes (EAN) that PRESERVES leading zeros:
    - Removes '+++' (common for scanners)
    - Removes '.0' (if float-originated)
    - Strips whitespace
    - Does NOT strip leading zeros (an EAN-13 can legitimately start with 0).
    Use this for any value that ends up written to a barcode output file, so
    that all modules emit an identical barcode for the same item.
    """
    if pd.isna(val):
        return ""
    s = str(val).strip().replace('+', '')
    return s.split('.')[0]
