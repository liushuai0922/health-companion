"""Offline parsers for official USDA food archives and MedlinePlus topic XML."""
import csv
import io
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from zipfile import ZipFile

NUTRIENTS = {"1003": "protein_g", "1004": "fat_g", "1005": "carbohydrate_g", "1079": "fiber_g", "1093": "sodium_mg"}
ENERGY_PRIORITY = ("2048", "2047", "1008")
TOPIC_ALIASES = {
    "Diabetes Type 2": ("2 型糖尿病", ["type2_diabetes"]),
    "High Blood Pressure": ("高血压", ["hypertension"]),
    "Steatotic Liver Disease": ("脂肪性肝病", ["fatty_liver"]),
    "Cholesterol": ("胆固醇与血脂", ["hyperlipidemia"]),
    "Gout": ("痛风", ["gout", "hyperuricemia"]),
    "Chronic Kidney Disease": ("慢性肾脏病", ["chronic_kidney_disease"]),
    "Stroke": ("脑卒中", ["stroke"]),
    "Osteoporosis": ("骨质疏松症", ["osteoporosis"]),
    "Nutrition for Older Adults": ("老年人营养", ["sarcopenia", "older_adult"]),
    "Obesity": ("肥胖", ["obesity"]),
}


def csv_member(archive, suffix):
    member = next(name for name in archive.namelist() if name.endswith("/" + suffix))
    return csv.DictReader(io.TextIOWrapper(archive.open(member), encoding="utf-8-sig", newline=""))


def parse_food_composition(blob, expected_type, release):
    with ZipFile(io.BytesIO(blob)) as archive:
        foods = {}
        for row in csv_member(archive, "food.csv"):
            if row["data_type"] != expected_type:
                continue
            fdc_id = int(row["fdc_id"])
            foods[fdc_id] = {"fdc_id": fdc_id, "description_en": row["description"].strip(),
                             "data_type": expected_type, "release": release, "source_url": f"https://fdc.nal.usda.gov/food-details/{fdc_id}/nutrients",
                             **{field: None for field in (*NUTRIENTS.values(), "energy_kcal")}}
        energy = {}
        for row in csv_member(archive, "food_nutrient.csv"):
            fdc_id = int(row["fdc_id"])
            if fdc_id not in foods or not row["amount"]:
                continue
            nutrient_id = row["nutrient_id"]
            try:
                amount = float(row["amount"])
            except ValueError:
                continue
            if amount < 0:
                continue
            field = NUTRIENTS.get(nutrient_id)
            if field:
                foods[fdc_id][field] = amount
            elif nutrient_id in ENERGY_PRIORITY and (fdc_id not in energy or ENERGY_PRIORITY.index(nutrient_id) < ENERGY_PRIORITY.index(energy[fdc_id])):
                foods[fdc_id]["energy_kcal"] = amount
                energy[fdc_id] = nutrient_id
    return list(foods.values())


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in {"p", "br", "li", "div"}:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in {"p", "li", "div"}:
            self.parts.append(" ")


def parse_medline_topics(blob, release):
    with ZipFile(io.BytesIO(blob)) as archive:
        member = next(name for name in archive.namelist() if name.endswith(".xml"))
        root = ET.fromstring(archive.read(member))
    if root.tag != "health-topics":
        raise ValueError("Unexpected MedlinePlus XML root")
    records = []
    for topic in root.findall("health-topic"):
        if topic.get("language") != "English":
            continue
        title = topic.get("title", "").strip()
        alias, codes = TOPIC_ALIASES.get(title, (None, []))
        parser = TextOnly()
        parser.feed(topic.findtext("full-summary") or "")
        summary = re.sub(r"\s+", " ", "".join(parser.parts)).strip()[:3000]
        records.append({"topic_id": int(topic.get("id")), "title_en": title, "title_zh": alias,
                        "summary_en": summary, "condition_codes": codes, "source_url": topic.get("url"), "release": release})
    return records
