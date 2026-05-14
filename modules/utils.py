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
