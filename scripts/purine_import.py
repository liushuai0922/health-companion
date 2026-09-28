"""Read the USDA/ODS purine workbook without an Excel runtime."""
import io
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile

SOURCE_URL = "https://www.ars.usda.gov/ARSUserFiles/80400535/Data/Purine/PURINEDATABASEANDDATASOURCES2025.xlsx"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def read_rows(book_bytes, sheet):
    with ZipFile(io.BytesIO(book_bytes)) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in item.findall(".//m:t", NS)) for item in root.findall("m:si", NS)]
        root = ET.fromstring(archive.read(f"xl/worksheets/sheet{sheet}.xml"))
        for row in root.findall("m:sheetData/m:row", NS):
            values = {}
            for cell in row.findall("m:c", NS):
                col = re.match(r"[A-Z]+", cell.get("r", ""))
                if not col:
                    continue
                value = cell.find("m:v", NS)
                inline = cell.find("m:is", NS)
                item = value.text if value is not None else "".join(t.text or "" for t in inline.findall(".//m:t", NS)) if inline is not None else ""
                if cell.get("t") == "s" and item:
                    item = shared[int(item)]
                values[col.group()] = item
            yield int(row.get("r")), values


def parse_purines(book_bytes):
    records = []
    for sheet, category, unit in ((1, "North America food", "mg/100g"), (2, "International food", "mg/100g"), (3, "Alcoholic beverage", "mg/100mL")):
        for row_number, row in read_rows(book_bytes, sheet):
            if row_number <= 5 or not row.get("A"):
                continue
            try:
                total = float(row.get("S", ""))
            except (ValueError, TypeError):
                continue
            if not 0 <= total <= 10000:
                continue
            name = row["A"].strip()
            if len(name) > 500:
                continue
            records.append({"key": f"sheet{sheet}-row{row_number}", "food_name_en": name,
                            "category": category, "total_purines_mg": total, "unit": unit,
                            "sample_n": row.get("B", "").strip(), "year": row.get("U", "").strip(),
                            "source_code": row.get("V", "").strip(), "country": row.get("W", "").strip(),
                            "source_url": SOURCE_URL})
    return records
