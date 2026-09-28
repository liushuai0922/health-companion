"""Conservative Chinese search labels for local English reference snapshots.

Labels identify a food family, not a translation of variety or preparation.
Keep the English source description beside every label.
"""

import re


SOURCE_NAMES = {
    "RxNorm": "美国药品标准名称库",
    "DailyMed": "美国药品说明书库",
    "USDA FoodData Central": "美国农业部食品数据中心 · 精选样本",
    "国家卫健委食养指南": "国家卫健委食养指南",
    "USDA/ODS 食物嘌呤": "食物嘌呤参考数据",
    "USDA SR Legacy 全目录": "美国农业部历史食品成分库",
    "USDA Foundation Foods": "美国农业部基础食品成分库",
    "MedlinePlus 健康主题": "美国国家医学图书馆健康主题库",
}

# Longer, specific phrases precede broad food names.
FOOD_TERMS = (
    ("牛肝", "beef liver"), ("鸡肝", "chicken liver"),
    ("西兰花", "broccoli"), ("花椰菜", "cauliflower"),
    ("糙米", "brown rice"), ("白米", "white rice"),
    ("燕麦", "oats"), ("豆腐", "tofu"), ("苹果", "apple"),
    ("香蕉", "banana"), ("牛肉", "beef"), ("鸡肉", "chicken"),
    ("猪肉", "pork"), ("羊肉", "lamb"), ("三文鱼", "salmon"),
    ("鳕鱼", "cod"), ("金枪鱼", "tuna"), ("鲭鱼", "mackerel"),
    ("虾", "shrimp"), ("鱼", "fish"), ("鸡蛋", "egg"),
    ("牛奶", "milk"), ("酸奶", "yogurt"), ("奶酪", "cheese"),
    ("菠菜", "spinach"), ("番茄", "tomato"), ("土豆", "potato"),
    ("黄瓜", "cucumber"), ("胡萝卜", "carrot"),
    ("蘑菇", "mushroom"), ("豆类", "beans"),
    ("面包", "bread"), ("米饭", "rice"), ("啤酒", "beer"),
    ("葡萄酒", "wine"), ("咖啡", "coffee"),
)

ALIASES = {"马铃薯": "potato", "洋芋": "potato", "西红柿": "tomato",
           "牛乳": "milk", "鲑鱼": "salmon", "花菜": "cauliflower",
           "黄豆": "soybean", "大豆": "soybean", "绿豆": "mung bean"}


def english_food_query(term: str) -> str:
    term = term.strip().casefold()
    if not term:
        return ""
    for zh, en in FOOD_TERMS:
        if zh in term:
            return en
    for zh, en in ALIASES.items():
        if zh in term:
            return en
    return term


def chinese_food_query(term: str) -> str | None:
    """A recognized Chinese food category, or None for English/unknown input."""
    term = term.strip().casefold()
    for zh, en in FOOD_TERMS:
        if zh in term:
            return zh
    for alias, en in ALIASES.items():
        if alias in term:
            return next((zh for zh, word in FOOD_TERMS if word == en), None)
    return None


def food_label(description: str) -> str | None:
    """Return a broad Chinese index label only for a clear leading food name."""
    normalized = description.casefold().strip()
    for prefix, label in (("cereals, oats", "燕麦"), ("rice, brown", "糙米"),
                          ("rice, white", "白米"), ("fish, cod", "鳕鱼"),
                          ("fish, salmon", "三文鱼"), ("fish, tuna", "金枪鱼")):
        if normalized.startswith(prefix) and (len(normalized) == len(prefix) or normalized[len(prefix)] in ", "):
            return label
    for zh, en in FOOD_TERMS:
        if re.match(rf"^{re.escape(en)}(?:s)?(?:\b|,)", normalized):
            return zh
    return None
