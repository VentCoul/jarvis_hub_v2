# logic.py
import pandas as pd
from .utils import normalize_id, normalize_barcode
from .constants import COLUMN_MAPPING
from collections import Counter

def detect_column(df, category):
    for col in COLUMN_MAPPING.get(category, []):
        if col in df.columns:
            return col
    return df.columns[0]

def read_inventory(inventory_path):
    """
    Reads the inventory workbook once, preferring a sheet named 'Data'.
    Article/barcode columns are forced to str so that leading zeros survive
    (pandas would otherwise coerce numeric-looking ids to int and drop them).
    Quantity columns are left to pandas to infer as numeric.
    """
    xls = pd.ExcelFile(inventory_path)
    sheet_name = 'Data' if 'Data' in xls.sheet_names else 0
    id_dtypes = {col: str for col in COLUMN_MAPPING['article'] + COLUMN_MAPPING['barcode']}
    return pd.read_excel(xls, sheet_name=sheet_name, dtype=id_dtypes)

def process_clearance_add(clearance_path, inventory_path, store_id, location_filter):
    try:
        df_clr = pd.read_excel(clearance_path)
        store_col = detect_column(df_clr, 'store')
        article_col = detect_column(df_clr, 'article')
        df_clr[article_col] = df_clr[article_col].astype(str).str.strip().str.lstrip('0')
        mask = df_clr[store_col].astype(str) == str(store_id)
        target_articles = set(df_clr[mask][article_col].unique())
        
        df_inv = read_inventory(inventory_path)
        df_inv['ItemNo'] = df_inv['ItemNo'].apply(normalize_id)
        df_inv['Barcode'] = df_inv['Barcode'].apply(normalize_barcode)
        matched = df_inv[df_inv['ItemNo'].isin(target_articles)].copy()

        if location_filter != "Загальна":
            matched = matched[matched['Location'].str.contains(location_filter, case=False, na=False)]

        if matched.empty: return []

        final = matched.groupby('Barcode')['TotalQuantity'].sum().reset_index()
        return [f"{r['Barcode']};{int(r['TotalQuantity'])}" for _, r in final[final['TotalQuantity'] > 0].iterrows()]
    except Exception as e: raise RuntimeError(f"Clearance Error: {e}")

def process_missed_items(inventory_path, division_filter, gender_filter):
    """
    Items missing from Sales Floor (Total Hall Qty <= 0) but present in Warehouse (Qty > 0).
    Replicates the Pivot Table view as requested by the user.
    """
    try:
        df = read_inventory(inventory_path)

        df.columns = [str(c).strip() for c in df.columns]
        cols = df.columns.tolist()
        
        art_col = next((c for c in cols if any(x in c.lower() for x in ['itemno', 'article', 'артикул'])), 'ItemNo')
        var_col = next((c for c in cols if any(x in c.lower() for x in ['variant', 'size', 'розмір'])), 'Variant')
        loc_col = next((c for c in cols if any(x in c.lower() for x in ['location', 'локація', 'місце'])), 'Location')
        qty_col = next((c for c in cols if any(x in c.lower() for x in ['totalquantity', 'qty', 'кількість'])), 'TotalQuantity')
        shelf_col = next((c for c in cols if any(x in c.lower() for x in ['shelf', 'полиця'])), 'Shelf')
        bc_col = next((c for c in cols if any(x in c.lower() for x in ['barcode', 'шк'])), 'Barcode')
        desc_col = next((c for c in cols if any(x in c.lower() for x in ['description', 'опис'])), 'Description')
        div_col = next((c for c in cols if any(x in c.lower() for x in ['division', 'дивізіон'])), 'Division_Description')
        gen_col = next((c for c in cols if any(x in c.lower() for x in ['gender', 'стать'])), 'Gender')

        df[art_col] = df[art_col].apply(normalize_id)
        df[var_col] = df[var_col].fillna('-').astype(str).str.strip()
        df[qty_col] = pd.to_numeric(df[qty_col], errors='coerce').fillna(0)
        df[shelf_col] = df[shelf_col].fillna('-').astype(str).str.strip()
        df[loc_col] = df[loc_col].fillna('').astype(str).str.strip()

        locs = df[loc_col].unique()
        wh_loc_name = next((l for l in locs if 'склад' in str(l).lower() or 'warehouse' in str(l).lower()), None)
        sf_loc_name = next((l for l in locs if 'зал' in str(l).lower() or 'floor' in str(l).lower() or 'shop' in str(l).lower()), None)
        if wh_loc_name is None or sf_loc_name is None:
            raise RuntimeError(
                "Не вдалося визначити локації 'Склад' і 'Торговий зал' у звіті. "
                f"Знайдені локації: {', '.join(str(l) for l in locs) or '(порожньо)'}"
            )

        hall_totals = df[df[loc_col] == sf_loc_name].groupby([art_col, var_col])[qty_col].sum().reset_index()
        hall_totals.columns = [art_col, var_col, 'Hall_Total_Sum']

        wh_data = df[df[loc_col] == wh_loc_name].copy()
        merged = pd.merge(wh_data, hall_totals, on=[art_col, var_col], how='left').fillna(0)
        missed = merged[(merged[qty_col] > 0) & (merged['Hall_Total_Sum'] <= 0)].copy()

        if division_filter != "Усі":
            mapping = {"Одяг": ["Apparel", "Bodywear"], "Взуття": ["Footwear"], "Аксесуари": ["Accessories", "Socks"]}
            if div_col in missed.columns:
                missed = missed[missed[div_col].isin(mapping.get(division_filter, []))]
        if gender_filter != "Усі":
            gen_map_ui = {"Men": "Male", "Women": "Female"}
            target_gen = gen_map_ui.get(gender_filter, gender_filter)
            if gen_col in missed.columns:
                missed = missed[missed[gen_col] == target_gen]

        missed = missed.sort_values(by=[shelf_col, art_col, var_col])
        
        result = pd.DataFrame()
        result['Артикул'] = missed[art_col]
        result['Полиця'] = missed[shelf_col]
        result['Опис'] = missed[desc_col]
        result['Розмір'] = missed[var_col]
        result['Штрихкод'] = missed[bc_col]
        result['Торговий зал'] = 0
        result['Склад'] = missed[qty_col]
        result['Загальний підсумок'] = result['Склад']

        return result
    except Exception as e: raise RuntimeError(f"Missed Items Error: {e}")

def process_movement(clearance_path, inventory_path, scan_path, store_id):
    try:
        # 1. Load Clearance and define Promo Articles for the specific store
        df_clr = pd.read_excel(clearance_path)
        cl_art_col = detect_column(df_clr, 'article')
        cl_st_col = detect_column(df_clr, 'store')
        
        # Filter by store and normalize articles
        df_clr[cl_art_col] = df_clr[cl_art_col].astype(str).str.strip().str.lstrip('0')
        promo_arts = set(df_clr[df_clr[cl_st_col].astype(str) == str(store_id)][cl_art_col].unique())

        # 2. Load Inventory to get Barcode -> Article mapping
        df_inv = read_inventory(inventory_path)

        # Clean inventory columns
        inv_bc_col = next((c for c in df_inv.columns if any(x in str(c).lower() for x in ['barcode', 'шк'])), 'Barcode')
        inv_art_col = next((c for c in df_inv.columns if any(x in str(c).lower() for x in ['itemno', 'article', 'артикул'])), 'ItemNo')

        df_inv[inv_bc_col] = df_inv[inv_bc_col].apply(normalize_barcode)
        df_inv[inv_art_col] = df_inv[inv_art_col].apply(normalize_id)

        # Map Barcode to Article (ItemNo)
        inv_map = df_inv.drop_duplicates(inv_bc_col).set_index(inv_bc_col)[inv_art_col].to_dict()

        # 3. Process the Scan file
        with open(scan_path, 'r', encoding='utf-8') as f:
            scanned_raw = [normalize_barcode(line.strip()) for line in f if line.strip()]

        # Aggregate scan counts (remove repeats)
        scan_counts = Counter(scanned_raw)

        # 4. Classification
        promo_list = []
        regular_list = []
        all_combined_list = []
        
        for bc, qty in scan_counts.items():
            entry = f"{bc};{qty}"
            all_combined_list.append(entry)
            
            # Find the article for this barcode
            article = inv_map.get(bc)
            
            if article and article in promo_arts:
                promo_list.append(entry)
            else:
                regular_list.append(entry)
                
        return promo_list, regular_list, all_combined_list
    except Exception as e: raise RuntimeError(f"Movement Error: {e}")

def _read_price_file(price_path):
    """Read a price file that may have decorative header rows before the actual table."""
    known_cols = set(COLUMN_MAPPING['article'] + COLUMN_MAPPING['barcode'])
    df_raw = pd.read_excel(price_path, header=None, nrows=20)
    header_row = 0
    for i, row in df_raw.iterrows():
        vals = [str(v).strip() for v in row if pd.notna(v)]
        if known_cols & set(vals):
            header_row = i
            break
    df = pd.read_excel(price_path, header=header_row)
    df = df.dropna(subset=[df.columns[0]])
    if df.empty:
        raise RuntimeError("Файл переоцінки порожній або не вдалося знайти таблицю.")
    return df


def process_price_update(price_path, clearance_path, inventory_path, store_id):
    try:
        df_price = _read_price_file(price_path)

        id_col = None
        is_barcode = False
        for col in COLUMN_MAPPING['article']:
            if col in df_price.columns:
                id_col = col
                break
        if not id_col:
            for col in COLUMN_MAPPING['barcode']:
                if col in df_price.columns:
                    id_col = col
                    is_barcode = True
                    break
        if not id_col:
            id_col = df_price.columns[0]
            sample = str(df_price[id_col].iloc[0])
            if len(sample) >= 10:
                is_barcode = True

        normalizer = normalize_barcode if is_barcode else normalize_id
        target_ids = set(df_price[id_col].apply(normalizer).unique())
        total_in_price = len(target_ids)

        df_clr = pd.read_excel(clearance_path)
        art_col_clr = detect_column(df_clr, 'article')
        st_col_clr = detect_column(df_clr, 'store')
        df_clr[art_col_clr] = df_clr[art_col_clr].astype(str).str.strip().str.lstrip('0')
        promo_arts = set(df_clr[df_clr[st_col_clr].astype(str) == str(store_id)][art_col_clr].unique())

        df_inv = read_inventory(inventory_path)
        df_inv['ItemNo_Norm'] = df_inv['ItemNo'].apply(normalize_id)
        df_inv['Barcode_Norm'] = df_inv['Barcode'].apply(normalize_barcode)

        inv_col = 'Barcode_Norm' if is_barcode else 'ItemNo_Norm'
        matched_inv = df_inv[df_inv[inv_col].isin(target_ids)].copy()

        if matched_inv.empty:
            return [], [], total_in_price, 0

        final = matched_inv.groupby(['Barcode_Norm', 'ItemNo_Norm'])['TotalQuantity'].sum().reset_index()
        final = final[final['TotalQuantity'] > 0]
        found_arts = len(final['ItemNo_Norm'].unique())

        promo, reg = [], []
        for _, row in final.iterrows():
            line = f"{row['Barcode_Norm']};{int(row['TotalQuantity'])}"
            if row['ItemNo_Norm'] in promo_arts:
                promo.append(line)
            else:
                reg.append(line)

        return promo, reg, total_in_price, found_arts
    except Exception as e: raise RuntimeError(f"Price Update Error: {e}")

def process_shipping(scan_path, inventory_path, template_path, doc_num):
    from openpyxl import load_workbook
    from collections import Counter
    try:
        with open(scan_path, 'r', encoding='utf-8') as f:
            scanned_barcodes = [normalize_barcode(line.strip()) for line in f if line.strip()]
        scanned_barcodes = [bc for bc in scanned_barcodes if bc]
        if not scanned_barcodes:
            return None

        df_inv = read_inventory(inventory_path)
        df_inv['Barcode_Norm'] = df_inv['Barcode'].apply(normalize_barcode)
        bc_map = df_inv.drop_duplicates('Barcode_Norm').set_index('Barcode_Norm')[['ItemNo', 'Variant']].to_dict('index')

        rows = Counter()
        for bc in scanned_barcodes:
            info = bc_map.get(bc)
            if info:
                key = (normalize_id(str(info['ItemNo'])), str(info.get('Variant', '')).strip())
            else:
                key = (bc, '')
            rows[key] += 1

        wb = load_workbook(template_path)
        ws = wb.active
        start_row, line_num = 4, 10000
        for (article, variant), qty in rows.items():
            ws.cell(row=start_row, column=1, value=doc_num)
            ws.cell(row=start_row, column=2, value=line_num)
            ws.cell(row=start_row, column=3, value=article)
            ws.cell(row=start_row, column=4, value=qty)
            ws.cell(row=start_row, column=5, value=variant)
            start_row += 1
            line_num += 10000
        return wb
    except Exception as e: raise RuntimeError(f"Shipping Error: {e}")
