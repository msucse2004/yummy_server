"""주소 → 위도/경도 변환 (Kakao Local API 우선, 실패 시 Nominatim 폴백)"""
import re
import time
from decimal import Decimal

import httpx
import structlog

KAKAO_GEOCODE_URL = "https://dapi.kakao.com/v2/local/search/address.json"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "YummyDelivery/1.0"
log = structlog.get_logger(__name__)


def _make_address_variants(addr: str) -> list[str]:
    """주소 변형 생성: 괄호 제거, 도로명/지번 분리 등"""
    variants = [addr]
    s = addr.strip()
    if not s:
        return variants
    m = re.search(r"^(.+?)\s*\(([^)]+)\)\s*$", s)
    if m:
        main_part = m.group(1).strip()
        paren_part = m.group(2).strip()
        if main_part and main_part not in variants:
            variants.append(main_part)
        if paren_part:
            region_match = re.match(r"^([\s가-힣\d]+?(?:시|도|구|군)\s+)", s)
            if region_match:
                landlot = (region_match.group(1).strip() + " " + paren_part).strip()
                if landlot and landlot not in variants:
                    variants.append(landlot)
    return variants


def _geocode_kakao(addr: str, api_key: str) -> tuple[Decimal | None, Decimal | None]:
    """Kakao API로 조회"""
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                KAKAO_GEOCODE_URL,
                params={"query": addr},
                headers={"Authorization": f"KakaoAK {api_key.strip()}"},
            )
            data = resp.json() if resp.content else {}
            if resp.status_code != 200:
                return None, None
            docs = data.get("documents") if isinstance(data, dict) else None
            if docs and isinstance(docs, list) and len(docs) > 0:
                item = docs[0]
                lat, lon = item.get("y"), item.get("x")
                if lat is not None and lon is not None:
                    return Decimal(str(lat)), Decimal(str(lon))
    except Exception:
        pass
    return None, None


def _geocode_nominatim(addr: str) -> tuple[Decimal | None, Decimal | None]:
    """Nominatim(OpenStreetMap) 폴백 - 1 req/sec"""
    if any("\uac00" <= c <= "\ud7a3" for c in addr):
        addr = f"{addr}, 대한민국"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                NOMINATIM_URL,
                params={"q": addr, "format": "json", "limit": 1},
                headers={"User-Agent": USER_AGENT},
            )
            if resp.status_code != 200:
                return None, None
            data = resp.json()
            if not isinstance(data, list):
                data = []
            if data and len(data) > 0:
                item = data[0]
                lat, lon = item.get("lat"), item.get("lon")
                if lat is not None and lon is not None:
                    return Decimal(str(lat)), Decimal(str(lon))
    except Exception:
        pass
    return None, None


def geocode_address(address: str, api_key: str) -> tuple[Decimal | None, Decimal | None]:
    """
    주소로 위도/경도 조회. Kakao 우선, 실패 시 주소 변형 재시도, 최종 폴백은 Nominatim.
    """
    if not address or not address.strip():
        return None, None
    if not api_key or not api_key.strip():
        log.warning("geocode_skip", reason="KAKAO_REST_API_KEY not set")
        return None, None
    addr = address.strip()
    if len(addr) < 2:
        return None, None
    variants = _make_address_variants(addr)
    for v in variants:
        if len(v) < 2:
            continue
        result = _geocode_kakao(v, api_key)
        if result[0] is not None and result[1] is not None:
            log.info("geocode_ok", source="kakao", address=addr[:50], lat=result[0], lon=result[1])
            return result
    for v in variants:
        if len(v) < 2:
            continue
        result = _geocode_nominatim(v)
        if result[0] is not None and result[1] is not None:
            time.sleep(1.0)
            log.info("geocode_ok", source="nominatim", address=addr[:50], lat=result[0], lon=result[1])
            return result
        time.sleep(1.0)
    log.info("geocode_empty", address=addr[:50], msg="kakao and nominatim both failed")
    return None, None


def maybe_geocode_and_update(
    address: str | None,
    latitude: Decimal | float | None,
    longitude: Decimal | float | None,
    api_key: str = "",
) -> tuple[Decimal | float | None, Decimal | float | None]:
    """
    위도/경도가 비어 있고 주소가 있으면 지오코딩 후 (lat, lon) 반환.
    이미 값이 있거나 주소가 없거나 API 키가 없으면 그대로 반환.
    """
    if latitude is not None and longitude is not None:
        return latitude, longitude
    if not address or not str(address).strip() or not api_key:
        return latitude, longitude
    lat, lon = geocode_address(str(address), api_key)
    if lat is not None and lon is not None:
        return lat, lon
    return latitude, longitude
