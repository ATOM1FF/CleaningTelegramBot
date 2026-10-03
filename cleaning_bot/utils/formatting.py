from typing import Any

from locales import get_locale

ITEM_KEYS = {
    "carpet": "type_carpet",
    "curtain": "type_curtain",
    "bedding": "type_bedding",
    "sofa": "type_sofa",
    "other": "type_other",
}


def item_type_from_label(label: str) -> str | None:
    for language in ("uz", "ru", "en"):
        texts = get_locale(language)
        for item_type, key in ITEM_KEYS.items():
            if label == texts[key]:
                return item_type
    return None


def format_items(items: list[dict[str, Any]], language: str, locale: dict[str, Any]) -> tuple[str, float]:
    rows = []
    total_area = 0.0
    for item in items:
        item_name = locale[ITEM_KEYS[item["type"]]]
        quantity = int(item["quantity"])
        area = float(item.get("area", float(item["width"]) * float(item["length"])))
        total_area += area * quantity
        unit = locale["unit_piece"]
        rows.append(
            f"- {item_name}: {item['width']}x{item['length']} {locale['unit_meter']}, "
            f"{quantity} {unit}; {area * quantity:.2f} {locale['unit_area']}"
        )
    return "\n".join(rows), total_area


def status_label(status: str, locale: dict[str, Any]) -> str:
    return locale.get(f"status_{status}", status)
