"""계약 내용 텍스트 → 품목 DB 맵핑 (ML 기반 fuzzy matching)"""
import re
from typing import NamedTuple

from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Item


class ContractItemMatch(NamedTuple):
    """맵핑된 계약 품목"""
    item_id: int
    product: str
    quantity: float
    unit: str
    score: float  # 유사도 0~100
    original_text: str


def _parse_contract_parts(text: str) -> list[tuple[str, float, str]]:
    """
    "곱1, 두부2판" -> [("곱", 1, "박스"), ("두부", 2, "판")]
    "곱슬이 2박스, 일자 3박스" -> [("곱슬이", 2, "박스"), ("일자", 3, "박스")]
    - 단위(박스/판/관)가 있으면 해당 단위, 없으면 숫자 추출 후 기본 "박스"
    """
    units = ("박스", "판", "관")
    parts = [p.strip() for p in text.split(",") if p.strip()]
    result = []
    for part in parts:
        matched_unit = None
        for u in units:
            if u in part:
                matched_unit = u
                break
        if matched_unit:
            idx = part.find(matched_unit)
            before = part[:idx].strip()
        else:
            before = part
            matched_unit = "박스"  # 단위 생략 시 기본 박스 (예: 곱1 -> 곱 1박스)
        num_match = re.search(r"[\d.]+", before)
        if num_match:
            qty_str = num_match.group()
            try:
                qty = float(qty_str)
            except ValueError:
                qty = 1.0
            product = (before[: num_match.start()] + before[num_match.end() :]).strip()
        else:
            qty = 1.0
            product = before.strip()
        if product:
            result.append((product, qty, matched_unit))
    return result


def match_contract_content(text: str, db: Session) -> list[dict]:
    """
    계약 내용 텍스트를 품목 DB와 ML(유사도) 기반으로 맵핑.
    Returns: [{"item_id", "product", "quantity", "unit", "score", "original_text"}, ...]
    """
    if not text or not text.strip():
        return []
    items = list(db.execute(select(Item)).scalars().all())
    if not items:
        return []
    product_choices = [(i.id, i.product, i.unit) for i in items]
    parsed = _parse_contract_parts(text.strip())
    results = []
    for prod_name, qty, unit in parsed:
        if not product_choices:
            break
        # rapidfuzz: 짧은 입력(일, 곱 등)은 partial_ratio로 앞부분 매칭, 그 외 token_set_ratio
        choices = [p[1] for p in product_choices]
        scorer = fuzz.partial_ratio if len(prod_name) <= 2 else fuzz.token_set_ratio
        match_result = process.extractOne(
            prod_name,
            choices,
            scorer=scorer,
        )
        if match_result:
            matched_name, score, idx = match_result
            item_id = product_choices[idx][0]
            results.append({
                "item_id": item_id,
                "product": matched_name,
                "quantity": qty,
                "unit": unit,
                "score": float(score),
                "original_text": f"{prod_name} {int(qty) if qty == int(qty) else qty}{unit}",
            })
    return results


def contract_items_to_display_string(matches: list[dict]) -> str:
    """맵핑 결과를 표시용 문자열로 변환"""
    return ", ".join(
        f"{m['product']} {int(m['quantity']) if m['quantity'] == int(m['quantity']) else m['quantity']}{m['unit']}"
        for m in matches
    )
