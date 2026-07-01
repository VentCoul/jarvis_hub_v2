# constants.py
"""
Centralized configuration for the Retail Management System.
Allows easy adjustment for different data formats without changing core logic.
"""

COLUMN_MAPPING = {
    'store': ['# Mall', 'Store', 'Магазин', 'Location_Code'],
    'article': ['Item', 'Article', 'Артикул', 'ItemNo', 'Parent_Item'],
    'barcode': ['Barcode', 'Штрих-код', 'EAN'],
    'quantity': ['TotalQuantity', 'Qty', 'Кількість', 'Current_Inventory'],
    'variant': ['Variant', 'Size', 'Розмір'],
    'division': ['Division_Description', 'Division', 'Дивізіон'],
    'gender': ['Gender', 'Стать']
}

THEME_CONFIG = {
    "appearance": "Dark",
    "color_theme": "blue"
}
