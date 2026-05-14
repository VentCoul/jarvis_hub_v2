# logic.py
import pandas as pd
from .utils import normalize_id
from .constants import COLUMN_MAPPING
from collections import Counter

def detect_column(df, category):
    for col in COLUMN_MAPPING.get(category, []):
        if col in df.columns:
            return col
    return df.columns[0]

def process_clearance_add(clearance_path, inventory_path, store_id, location_filter):
    try:
        df_clr = pd.read_excel(clearance_path)
        store_col = detect_column(df_clr, 'store')
        article_col = detect_column(df_clr, 'article')
        df_clr[article_col] = df_clr[article_col].astype(str).str.strip().str.lstrip('0')
        mask = df_clr[store_col].astype(str) == str(store_id)
        target_articles = set(df_clr[mask][article_col].unique())
        
        df_inv = pd.read_excel(inventory_path, sheet_name='Data' if 'Data' in pd.ExcelFile(inventory_path).sheet_names else 0)
        df_inv['ItemNo'] = df_inv['ItemNo'].apply(normalize_id)
        matched = df_inv[df_inv['ItemNo'].isin(target_articles)].copy()
        
        if location_filter != "Загальна":
            matched = matched[matched['Location'].str.contains(location_filter, case=False, na=False)]
        
        if matched.empty: return []
        
        final = matched.groupby('Barcode')['TotalQuantity'].sum().reset_index()
        return [f"{str(r['Barcode']).split('.')[0]};{int(r['TotalQuantity'])}" for _, r in final[final['TotalQuantity'] > 0].iterrows()]
    except Exception as e: raise RuntimeError(f"Clearance Error: {e}")

def process_missed_items(inventory_path, division_filter, gender_filter):
    """
    Items missing from Sales Floor (Total Hall Qty <= 0) but present in Warehouse (Qty > 0).
    Replicates the Pivot Table view as requested by the user.
    """
    try:
        xls = pd.ExcelFile(inventory_path)
        sheet_name = 'Data' if 'Data' in xls.sheet_names else (xls.sheet_names[0])
        df = pd.read_excel(xls, sheet_name=sheet_name)
        
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
        wh_loc_name = next((l for l in locs if 'склад' in str(l).lower() or 'warehouse' in str(l).lower()), 'Склад')
        sf_loc_name = next((l for l in locs if 'зал' in str(l).lower() or 'floor' in str(l).lower() or 'shop' in str(l).lower()), 'Торговий зал')

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
        df_inv = pd.read_excel(inventory_path, sheet_name='Data' if 'Data' in pd.ExcelFile(inventory_path).sheet_names else 0)
        
        # Clean inventory columns
        inv_bc_col = next((c for c in df_inv.columns if any(x in str(c).lower() for x in ['barcode', 'шк'])), 'Barcode')
        inv_art_col = next((c for c in df_inv.columns if any(x in str(c).lower() for x in ['itemno', 'article', 'артикул'])), 'ItemNo')
        
        df_inv[inv_bc_col] = df_inv[inv_bc_col].apply(normalize_id)
        df_inv[inv_art_col] = df_inv[inv_art_col].apply(normalize_id)
        
        # Map Barcode to Article (ItemNo)
        inv_map = df_inv.drop_duplicates(inv_bc_col).set_index(inv_bc_col)[inv_art_col].to_dict()

        # 3. Process the Scan file
        with open(scan_path, 'r') as f:
            scanned_raw = [normalize_id(line.strip()) for line in f if line.strip()]

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

def process_price_update(price_path, clearance_path, inventory_path, store_id):
    try:
        # 1. Load Price Update file
        df_price = pd.read_excel(price_path)
        
        # Identify ID column (Article or Barcode)
        id_col = None
        is_barcode = False
        
        # Check Article first (most common for office reports)
        for col in COLUMN_MAPPING['article']:
            if col in df_price.columns:
                id_col = col
                break
        
        # If not found, check for barcode
        if not id_col:
            for col in COLUMN_MAPPING['barcode']:
                if col in df_price.columns:
                    id_col = col
                    is_barcode = True
                    break
        
        # Fallback to first column if still nothing
        if not id_col:
            id_col = df_price.columns[0]
            sample = str(df_price[id_col].iloc[0])
            if len(sample) >= 10: is_barcode = True
        
        target_ids = set(df_price[id_col].apply(normalize_id).unique())

        # 2. Load Clearance file
        df_clr = pd.read_excel(clearance_path)
        art_col_clr = detect_column(df_clr, 'article')
        st_col_clr = detect_column(df_clr, 'store')
        df_clr[art_col_clr] = df_clr[art_col_clr].astype(str).str.strip().str.lstrip('0')
        promo_arts = set(df_clr[df_clr[st_col_clr].astype(str) == str(store_id)][art_col_clr].unique())

        # 3. Load Inventory
        df_inv = pd.read_excel(inventory_path, sheet_name='Data' if 'Data' in pd.ExcelFile(inventory_path).sheet_names else 0)
        df_inv['ItemNo_Norm'] = df_inv['ItemNo'].apply(normalize_id)
        df_inv['Barcode_Norm'] = df_inv['Barcode'].apply(normalize_id)

        # 4. Filter Inventory by targeted items
        inv_col = 'Barcode_Norm' if is_barcode else 'ItemNo_Norm'
        matched_inv = df_inv[df_inv[inv_col].isin(target_ids)].copy()

        if matched_inv.empty: return [], []

        # 5. Group by Barcode and separate Promo vs Regular
        final = matched_inv.groupby(['Barcode', 'ItemNo_Norm'])['TotalQuantity'].sum().reset_index()
        final = final[final['TotalQuantity'] > 0]

        promo, reg = [], []
        for _, row in final.iterrows():
            line = f"{str(row['Barcode']).split('.')[0]};{int(row['TotalQuantity'])}"
            if row['ItemNo_Norm'] in promo_arts:
                promo.append(line)
            else:
                reg.append(line)
        
        return promo, reg
    except Exception as e: raise RuntimeError(f"Price Update Error: {e}")

def process_shipping(scan_path, inventory_path, template_path, doc_num):
    from openpyxl import load_workbook
    try:
        with open(scan_path, 'r') as f:
            scanned = {}
            for line in f:
                bc = normalize_id(line.strip())
                if bc: scanned[bc] = scanned.get(bc, 0) + 1
        if not scanned: return None

        df_inv = pd.read_excel(inventory_path, sheet_name='Data' if 'Data' in pd.ExcelFile(inventory_path).sheet_names else 0)
        df_inv['Barcode'] = df_inv['Barcode'].apply(normalize_id)
        inv_data = df_inv.drop_duplicates('Barcode').set_index('Barcode').to_dict('index')

        wb = load_workbook(template_path)
        ws = wb.active
        start_row, line_num = 2, 10000
        for bc, qty in scanned.items():
            item = inv_data.get(bc, {})
            ws.cell(row=start_row, column=1, value=doc_num)
            ws.cell(row=start_row, column=2, value=line_num)
            ws.cell(row=start_row, column=3, value=bc)
            ws.cell(row=start_row, column=4, value=item.get('ItemNo', 'Unknown'))
            ws.cell(row=start_row, column=5, value=qty)
            start_row += 1
            line_num += 10000
        return wb
    except Exception as e: raise RuntimeError(f"Shipping Error: {e}")
