import pandas as pd
import pytest
from openpyxl import Workbook
from modules.logic import (
    process_clearance_add, process_movement,
    process_price_update, process_shipping,
)


@pytest.fixture
def clearance_file(tmp_path):
    """Store 5 has promo article 123; store 9 has unrelated article 999."""
    path = tmp_path / "clearance.xlsx"
    pd.DataFrame({
        "# Mall": [5, 5, 9],
        "Item": ["123", "123", "999"],
    }).to_excel(path, index=False)
    return str(path)


@pytest.fixture
def inventory_file(tmp_path):
    """Two items with realistic numeric barcodes (Excel stores these as numbers)."""
    path = tmp_path / "inventory.xlsx"
    pd.DataFrame({
        "ItemNo": ["123", "456"],
        "Barcode": ["4820001234567", "4820009876543"],
        "TotalQuantity": [3, 2],
        "Location": ["Торговий зал", "Торговий зал"],
    }).to_excel(path, index=False)
    return str(path)


@pytest.fixture
def scan_file(tmp_path):
    """First barcode scanned twice (promo), second once (regular)."""
    path = tmp_path / "scan.txt"
    path.write_text("4820001234567\n4820001234567\n4820009876543\n", encoding="utf-8")
    return str(path)


def _barcode(line):
    return line.split(";")[0]


def test_clearance_emits_barcode_and_qty(clearance_file, inventory_file):
    out = process_clearance_add(clearance_file, inventory_file, "5", "Загальна")
    assert out == ["4820001234567;3"]


def test_movement_classifies_promo_vs_regular(clearance_file, inventory_file, scan_file):
    promo, regular, all_combined = process_movement(clearance_file, inventory_file, scan_file, "5")
    assert promo == ["4820001234567;2"]
    assert regular == ["4820009876543;1"]
    assert sorted(all_combined) == ["4820001234567;2", "4820009876543;1"]


def test_barcode_consistency_across_modules(clearance_file, inventory_file, scan_file):
    """Regression for A1: the same item must emit an identical barcode token
    from every module."""
    clr_out = process_clearance_add(clearance_file, inventory_file, "5", "Загальна")
    promo, _, _ = process_movement(clearance_file, inventory_file, scan_file, "5")
    assert _barcode(clr_out[0]) == _barcode(promo[0]) == "4820001234567"


def _write_text_inventory(path):
    """Build an inventory workbook where Barcode is stored as TEXT, so a
    genuine leading zero survives into the dataframe (mirrors a real export)."""
    wb = Workbook()
    ws = wb.active
    ws.append(["ItemNo", "Barcode", "TotalQuantity", "Location"])
    # Force the barcode cells to text so the leading zero is preserved.
    ws.append(["123", "0123456789012", 3, "Торговий зал"])
    ws["B2"].number_format = "@"
    ws["B2"].value = "0123456789012"
    wb.save(path)


def test_leading_zero_preserved_end_to_end(tmp_path, clearance_file):
    """When the source actually carries a leading-zero barcode, it must NOT be
    stripped on the way to the output line."""
    inv = tmp_path / "inv_text.xlsx"
    _write_text_inventory(str(inv))

    out = process_clearance_add(clearance_file, str(inv), "5", "Загальна")
    assert out == ["0123456789012;3"]


@pytest.fixture
def clearance_file_float(tmp_path):
    """Clearance with a blank Item cell — pandas reads the whole Item column as
    float64, so '123' arrives as 123.0. Regression for the silent-empty bug."""
    path = tmp_path / "clearance_float.xlsx"
    pd.DataFrame({
        "# Mall": [5, 5, 9],
        "Item": [123, None, 999],
    }).to_excel(path, index=False)
    return str(path)


def test_clearance_matches_float_read_articles(clearance_file_float, inventory_file):
    """A float-read clearance article (123.0) must still match inventory '123'."""
    out = process_clearance_add(clearance_file_float, inventory_file, "5", "Загальна")
    assert out == ["4820001234567;3"]


def test_movement_matches_float_read_articles(clearance_file_float, inventory_file, scan_file):
    """Promo classification must survive a float-read clearance article column."""
    promo, regular, _ = process_movement(clearance_file_float, inventory_file, scan_file, "5")
    assert promo == ["4820001234567;2"]
    assert regular == ["4820009876543;1"]


def _alt_inventory(tmp_path):
    """Inventory using the alternative (but supported) column names:
    Article/EAN/Qty/Size instead of ItemNo/Barcode/TotalQuantity/Variant."""
    path = tmp_path / "inv_alt.xlsx"
    pd.DataFrame({
        "Article": ["123", "456"],
        "EAN": ["4820001234567", "4820009876543"],
        "Qty": [3, 2],
        "Size": ["M", "L"],
    }).to_excel(path, index=False)
    return str(path)


def test_price_update_accepts_alternative_columns(tmp_path, clearance_file):
    """Переоцінка must honour alternative inventory headers via detect_column."""
    inv = _alt_inventory(tmp_path)
    price = tmp_path / "price.xlsx"
    pd.DataFrame({"Article": ["123", "456"]}).to_excel(price, index=False)

    promo, reg, total, found = process_price_update(str(price), clearance_file, inv, "5")
    assert total == 2
    assert found == 2
    assert promo == ["4820001234567;3"]   # 123 is promo for store 5
    assert reg == ["4820009876543;2"]      # 456 is regular


def test_shipping_accepts_alternative_columns(tmp_path):
    """Відправка must honour alternative inventory headers via detect_column.
    Plain template (no XML map) -> openpyxl fallback path, returns bytes."""
    import io
    from openpyxl import load_workbook
    inv = _alt_inventory(tmp_path)
    scan = tmp_path / "scan.txt"
    scan.write_text("4820001234567\n4820001234567\n", encoding="utf-8")

    tmpl = tmp_path / "tmpl.xlsx"
    wb0 = Workbook(); wb0.active.append(["hdr"]); wb0.save(tmpl)

    data = process_shipping(str(scan), inv, str(tmpl), "ПЕР001")
    assert isinstance(data, (bytes, bytearray))
    ws = load_workbook(io.BytesIO(data)).active
    # Row 4 = first data row: doc, line, article(123), qty(2), variant(M)
    assert ws.cell(row=4, column=1).value == "ПЕР001"
    assert ws.cell(row=4, column=3).value == "123"
    assert ws.cell(row=4, column=4).value == 2
    assert ws.cell(row=4, column=5).value == "M"


def test_shipping_preserves_xml_map(tmp_path):
    """When the template carries a BC XML map, the output must keep it (and the
    single-cell mappings) so LS Central accepts the import."""
    import io, zipfile
    from openpyxl import load_workbook

    # Minimal template mimicking the LS Central export: xmlMaps + an xml table.
    tmpl = tmp_path / "bc_tmpl.xlsx"
    _write_xml_map_template(str(tmpl))

    inv = _alt_inventory(tmp_path)
    scan = tmp_path / "scan.txt"
    scan.write_text("4820001234567\n4820001234567\n4820009876543\n", encoding="utf-8")

    data = process_shipping(str(scan), inv, str(tmpl), "ПЕР005")
    assert isinstance(data, (bytes, bytearray))

    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        assert "xl/xmlMaps.xml" in names          # map survived
        assert "xl/tables/table1.xml" in names
        table = z.read("xl/tables/table1.xml").decode("utf-8")
    # 2 unique items -> rows 4 and 5 -> table range grows to A3:E5
    assert 'ref="A3:E5"' in table

    ws = load_workbook(io.BytesIO(data)).active
    assert ws["A4"].value == "ПЕР005"
    assert ws["C4"].value == "123"
    assert ws["D4"].value == "2"
    assert ws["C5"].value == "456"


def _write_xml_map_template(path):
    """Build a tiny .xlsx that contains an XML map + xml-typed table, matching
    the shape LS Central exports (header row 3, placeholder data row 4)."""
    import zipfile
    ns = 'xmlns:x="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    sheet = (
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<x:worksheet xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" {ns}>'
        '<x:sheetData>'
        '<x:row r="3"><x:c r="A3" t="inlineStr"><x:is><x:t>Номер документу</x:t></x:is></x:c></x:row>'
        '<x:row r="4"><x:c r="A4" t="inlineStr"><x:is><x:t></x:t></x:is></x:c></x:row>'
        '</x:sheetData></x:worksheet>'
    )
    table = (
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<x:table id="5" name="Table5" displayName="Table5" ref="A3:E4" tableType="xml" {ns}>'
        '<x:autoFilter ref="A3:E4" /><x:tableColumns count="5">'
        '<x:tableColumn id="1" name="Номер документу" /></x:tableColumns></x:table>'
    )
    ct = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '</Types>'
    )
    styles = ('<?xml version="1.0" encoding="UTF-8"?>'
              f'<x:styleSheet {ns}><x:cellXfs count="2">'
              '<x:xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>'
              '<x:xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>'
              '</x:cellXfs></x:styleSheet>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
    wb = ('<?xml version="1.0" encoding="UTF-8"?>'
          f'<x:workbook xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" {ns}>'
          '<x:sheets><x:sheet name="Sheet1" sheetId="1" r:id="rId1"/></x:sheets></x:workbook>')
    wb_rels = ('<?xml version="1.0" encoding="UTF-8"?>'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
               '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
        z.writestr("xl/styles.xml", styles)
        z.writestr("xl/tables/table1.xml", table)
        z.writestr("xl/xmlMaps.xml", '<?xml version="1.0"?><MapInfo/>')
