"""
Agent Tools — 出行决策 Agent 的高德地图工具集

私有模块（以 _ 开头），不会暴露成 HTTP 路由。
所有 Key 只从环境变量 AMAP_API_KEY 读取，绝不硬编码。
"""

import json
import math
import os
from typing import Annotated

import requests
from agents import function_tool

AMAP_BASE = "https://restapi.amap.com/v3"
REQUEST_TIMEOUT = 12


# ========== 内部工具函数（不暴露给 LLM） ==========
def _api_key() -> str:
    return (os.getenv("AMAP_API_KEY") or "").strip()


def _amap_get(path: str, params: dict) -> dict:
    """调用高德 Web 服务接口，统一错误处理。成功返回原始 dict，失败返回 {"_error": ...}。"""
    key = _api_key()
    if not key:
        return {"_error": "服务端没有配置 AMAP_API_KEY 环境变量，地图能力不可用"}

    query = dict(params)
    query["key"] = key
    query.setdefault("output", "json")

    try:
        resp = requests.get(f"{AMAP_BASE}{path}", params=query, timeout=REQUEST_TIMEOUT)
        data = resp.json()
    except requests.Timeout:
        return {"_error": "高德接口请求超时，请稍后重试"}
    except requests.RequestException as exc:
        return {"_error": f"高德接口网络错误: {type(exc).__name__}"}
    except ValueError:
        return {"_error": "高德接口返回了非 JSON 内容，可能是 Key 无效或配额用尽"}

    if str(data.get("status")) != "1":
        return {
            "_error": f"高德接口返回错误: {data.get('info')}",
            "infocode": data.get("infocode"),
        }
    return data


def _split_location(raw: str) -> tuple[float, float]:
    """把高德的 "lng,lat" 字符串拆成浮点坐标。"""
    lng_str, lat_str = str(raw).split(",")[:2]
    return float(lng_str), float(lat_str)


def _haversine_meters(lng1: float, lat1: float, lng2: float, lat2: float) -> int:
    """两点间球面直线距离（米）。"""
    radius = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return int(round(2 * radius * math.asin(math.sqrt(a))))


def _as_text(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False)


# ========== 工具 1: 地点解析 ==========
@function_tool
def geocode_location(
    address: Annotated[str, "用户提到的地点，例如「红莲南路地铁站」「西单大悦城」"],
    city: Annotated[str, "城市名，例如「北京」。用户没说城市时传空字符串"] = "",
) -> str:
    """把中文地点名解析成经纬度坐标。查询附近商场或门店之前，必须先用这个工具拿到起点坐标。"""
    params: dict = {"address": address}
    if city:
        params["city"] = city

    data = _amap_get("/geocode/geo", params)
    if "_error" in data:
        return _as_text(data)

    geocodes = data.get("geocodes") or []
    if not geocodes:
        return _as_text({
            "found": False,
            "message": f"高德无法解析「{address}」的坐标，需要用户补充更具体的地址或城市名",
        })

    best = geocodes[0]
    lng, lat = _split_location(best.get("location", ""))

    # 高德在「只给到市级」时 city 字段可能是空数组，回退到 province
    city_value = best.get("city")
    if not isinstance(city_value, str) or not city_value:
        city_value = best.get("province")

    return _as_text({
        "found": True,
        "input": address,
        "formatted_address": best.get("formatted_address"),
        "city": city_value,
        "district": best.get("district"),
        "precision": best.get("level"),
        "longitude": lng,
        "latitude": lat,
    })


# ========== 工具 2: 周边商场搜索 ==========
@function_tool
def search_malls_nearby(
    longitude: Annotated[float, "起点经度，直接使用 geocode_location 返回值里的 longitude"],
    latitude: Annotated[float, "起点纬度，直接使用 geocode_location 返回值里的 latitude"],
    radius_meters: Annotated[int, "搜索半径，单位米，默认 3000，最大 50000"] = 3000,
    keyword: Annotated[str, "要搜索的场所类型，默认「购物中心」；用户说商场时就用默认值"] = "购物中心",
) -> str:
    """以某个坐标为中心搜索附近的商场，返回商场名称、地址和距离起点的直线距离。"""
    radius = max(200, min(int(radius_meters), 50000))
    data = _amap_get("/place/around", {
        "location": f"{float(longitude):.6f},{float(latitude):.6f}",
        "radius": radius,
        "keywords": keyword,
        "sortrule": "distance",
        "offset": 20,
        "page": 1,
        "extensions": "base",
    })
    if "_error" in data:
        return _as_text(data)

    pois = data.get("pois") or []
    results = []
    for poi in pois:
        raw_loc = poi.get("location")
        if not raw_loc:
            continue
        try:
            lng, lat = _split_location(raw_loc)
        except (ValueError, AttributeError):
            continue
        results.append({
            "name": poi.get("name"),
            "address": poi.get("address") if isinstance(poi.get("address"), str) else "",
            "distance_meters": int(poi["distance"]) if str(poi.get("distance", "")).isdigit()
            else _haversine_meters(float(longitude), float(latitude), lng, lat),
            "longitude": lng,
            "latitude": lat,
        })

    results.sort(key=lambda item: item["distance_meters"])
    return _as_text({
        "origin": {"longitude": float(longitude), "latitude": float(latitude)},
        "radius_meters": radius,
        "count": len(results),
        "malls": results,
    })


# ========== 工具 3: 品牌门店搜索 ==========
@function_tool
def search_brand_stores(
    brand_name: Annotated[str, "要查找的品牌名，例如「倍轻松」，用用户原话里的品牌"],
    longitude: Annotated[float, "起点经度，使用 geocode_location 返回的 longitude"],
    latitude: Annotated[float, "起点纬度，使用 geocode_location 返回的 latitude"],
    radius_meters: Annotated[int, "搜索半径，单位米，默认 3000，可放到 50000"] = 3000,
) -> str:
    """搜索某个品牌在起点附近的实体门店，返回门店名称、所在地址、距离起点多远。地址里通常含商场名，可用于判断门店在哪家商场。"""
    radius = max(200, min(int(radius_meters), 50000))
    data = _amap_get("/place/around", {
        "location": f"{float(longitude):.6f},{float(latitude):.6f}",
        "radius": radius,
        "keywords": brand_name,
        "sortrule": "distance",
        "offset": 20,
        "page": 1,
        "extensions": "base",
    })
    if "_error" in data:
        return _as_text(data)

    pois = data.get("pois") or []
    stores = []
    for poi in pois:
        raw_loc = poi.get("location")
        if not raw_loc:
            continue
        try:
            lng, lat = _split_location(raw_loc)
        except (ValueError, AttributeError):
            continue
        stores.append({
            "name": poi.get("name"),
            "address": poi.get("address") if isinstance(poi.get("address"), str) else "",
            "category": poi.get("type"),
            "distance_meters": int(poi["distance"]) if str(poi.get("distance", "")).isdigit()
            else _haversine_meters(float(longitude), float(latitude), lng, lat),
            "longitude": lng,
            "latitude": lat,
        })

    stores.sort(key=lambda item: item["distance_meters"])
    return _as_text({
        "brand": brand_name,
        "origin": {"longitude": float(longitude), "latitude": float(latitude)},
        "radius_meters": radius,
        "count": len(stores),
        "stores": stores,
    })


# ========== 工具 4: 两点距离 ==========
@function_tool
def distance_between(
    origin_longitude: Annotated[float, "第一个点的经度"],
    origin_latitude: Annotated[float, "第一个点的纬度"],
    target_longitude: Annotated[float, "第二个点的经度"],
    target_latitude: Annotated[float, "第二个点的纬度"],
) -> str:
    """计算两个坐标之间的直线距离（米）。用于判断某家门店是否就在某家商场里，或比较哪个商场更近。"""
    meters = _haversine_meters(
        float(origin_longitude), float(origin_latitude),
        float(target_longitude), float(target_latitude),
    )
    return _as_text({
        "distance_meters": meters,
        "distance_text": f"{meters} 米" if meters < 1000 else f"{meters / 1000:.2f} 公里",
    })
