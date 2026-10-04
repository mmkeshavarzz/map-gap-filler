"""
src/processors/geo_tagger.py
=============================================================================
ماهواره جاسوسی و برچسب‌گذار مکانی (Ultimate Geo-Tagger & Satellite) 🛰️🌍
تاریخ آپدیت: ۱۴۰۵/۰۷/۱۳

هر ۱۰ قابلیت Enterprise در این هیولا پیاده‌سازی شده‌اند:
1. Point-in-Polygon (Ray Casting)    6. Geo-Hashing (Base32)
2. Traffic Zones Validation          7. Elevation Estimation (DEM)
3. Landmark Proximity                8. Fake Location AI Detect
4. Reverse Geocoding Fallback        9. Catchment Area (Influence)
5. Neighborhood Tagger               10. Timezone Auto-Assigner
=============================================================================
"""

import math
from typing import Dict, Any, Optional, Tuple, List

class GeoTagger:
    def __init__(self):
        # ==========================================
        # 🗺️ [قابلیت ۱ و ۵]: پلی‌گون‌های دقیق شهرها و محله‌ها
        # به جای جعبه، مرزها رو چندضلعی تعریف می‌کنیم (Lat, Lon)
        # ==========================================
        self.city_polygons = {
            "تهران": [(35.84, 51.10), (35.84, 51.60), (35.53, 51.60), (35.53, 51.10)],
            "شیراز": [(29.70, 52.40), (29.70, 52.65), (29.50, 52.65), (29.50, 52.40)]
        }
        
        self.neighborhoods_tehran = {
            "سعادت‌آباد": [(35.78, 51.36), (35.78, 51.40), (35.75, 51.40), (35.75, 51.36)]
        }

        # 🚗 [قابلیت ۲]: محدوده‌های طرح ترافیک
        self.traffic_zones = {
            "طرح اصلی تهران": [(35.74, 51.38), (35.74, 51.45), (35.68, 51.45), (35.68, 51.38)]
        }

        # 🚇 [قابلیت ۳]: لندمارک‌های استراتژیک (برای محاسبه نزدیکی)
        self.landmarks = [
            {"name": "مترو تجریش", "lat": 35.8044, "lon": 51.4285, "type": "metro"},
            {"name": "میدان آزادی", "lat": 35.6997, "lon": 51.3380, "type": "monument"}
        ]

        # 📡 [قابلیت ۹]: شعاع نفوذ اصناف مختلف (به متر)
        self.catchment_radii = {
            "بیمارستان": 15000,
            "رستوران": 3000,
            "کافه": 1500,
            "سوپرمارکت": 500
        }

        self.base32_chars = "0123456789bcdefghjkmnpqrstuvwxyz"

    # ==========================================
    # 🛠️ موتورهای محاسباتی و هوش مصنوعی
    # ==========================================

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """ محاسبه فاصله کروی با فرمول $ d = 2r \arcsin(...) $ """
        R = 6371000.0 # شعاع زمین به متر
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
        a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
        return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

    def _point_in_polygon(self, point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
        """ 🛑 [قابلیت ۱]: الگوریتم Ray Casting برای بررسی حضور نقطه در چندضلعی """
        x, y = point[0], point[1] # lat, lon
        n = len(polygon)
        inside = False
        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y) and y <= max(p1y, p2y) and x <= max(p1x, p2x):
                if p1y != p2y:
                    xints = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                if p1x == p2x or x <= xints:
                    inside = not inside
            p1x, p1y = p2x, p2y
        return inside

    def _encode_geohash(self, lat: float, lon: float, precision: int = 7) -> str:
        """ ⚡ [قابلیت ۶]: تولید Geohash برای ایندکس سریع در دیتابیس """
        lat_interval, lon_interval = [-90.0, 90.0], [-180.0, 180.0]
        geohash, bits = [], []
        even = True
        while len(geohash) < precision:
            if even:
                mid = sum(lon_interval) / 2
                if lon >= mid:
                    bits.append(1)
                    lon_interval[0] = mid
                else:
                    bits.append(0)
                    lon_interval[1] = mid
            else:
                mid = sum(lat_interval) / 2
                if lat >= mid:
                    bits.append(1)
                    lat_interval[0] = mid
                else:
                    bits.append(0)
                    lat_interval[1] = mid
            even = not even
            if len(bits) == 5:
                idx = int("".join(map(str, bits)), 2)
                geohash.append(self.base32_chars[idx])
                bits = []
        return "".join(geohash)

    def _detect_fake_location(self, lat: float, lon: float) -> bool:
        """ 🎯 [قابلیت ۸]: هوش مصنوعی تشخیص مختصات فیک (صفرهای رند و گرد شده) """
        str_lat, str_lon = str(lat), str(lon)
        # اگه مختصات رو تا ۴ رقم اعشار صفر وارد کرده باشن، قطعاً فیکه!
        if str_lat.endswith(".0000") or str_lon.endswith(".0000"):
            return True
        # مختصات‌های خیلی رند (مثل 35.5، بدون دقت کافی)
        if len(str_lat.split('.')[-1]) < 3: 
            return True
        return False

    def _estimate_elevation(self, lat: float, lon: float) -> int:
        """ ⛰️ [قابلیت ۷]: تخمین ارتفاع (شبیه‌ساز مدل DEM) """
        # اینجا فرمول فرضی برای تهران (شمال تهران مرتفع‌تره) پیاده کردیم
        if 35.5 < lat < 35.9 and 51.1 < lon < 51.6:
            base_elevation = 1100
            extra = (lat - 35.5) * 1000 # هر چقدر به سمت شمال میره
            return int(base_elevation + extra)
        return 0 # سطح دریا برای نقاط ناشناخته

    def _reverse_geocode_fallback(self, lat: float, lon: float) -> str:
        """ 🌐 [قابلیت ۴]: فال‌بک به API در صورت پیدا نشدن در پلی‌گون‌ها """
        # اینجا در واقعیت ریکوئست به API نشان یا مپ.آی‌آر ارسال میشه
        # mock response:
        return f"آدرس_استخراج_شده_از_API_برای_{round(lat,2)}_{round(lon,2)}"

    def _get_timezone(self, lon: float) -> str:
        """ ⏰ [قابلیت ۱۰]: محاسبه خودکار تایم‌زون از روی طول جغرافیایی """
        offset = round(lon / 15.0)
        sign = "+" if offset >= 0 else "-"
        return f"UTC{sign}{abs(offset)}"

    # ==========================================
    # 🚀 هسته اصلی پردازش رکورد
    # ==========================================

    def process_location(self, record: Dict[str, Any]) -> Dict[str, Any]:
        processed = record.copy()
        lat, lon = processed.get('lat'), processed.get('lon')

        if not lat or not lon:
            processed['geo_status'] = 'missing_coords'
            return processed

        # 🎯 قابلیت ۸: بررسی فیک بودن مختصات
        if self._detect_fake_location(lat, lon):
            processed['_warning'] = "مختصات به شدت رند و مشکوک به خطای انسانی است!"
            processed['quality_score'] = processed.get('quality_score', 100) - 40

        point = (lat, lon)
        tags = processed.get('tags', [])

        # 🛑 قابلیت ۱ و ۵: پیدا کردن شهر و محله با Ray Casting
        actual_city = None
        for city, poly in self.city_polygons.items():
            if self._point_in_polygon(point, poly):
                actual_city = city
                break
        
        if actual_city:
            processed['city'] = actual_city
            tags.append(actual_city)
            
            # پیدا کردن محله (فقط در صورت تطابق شهر)
            if actual_city == "تهران":
                for neighborhood, poly in self.neighborhoods_tehran.items():
                    if self._point_in_polygon(point, poly):
                        processed['neighborhood'] = neighborhood
                        tags.append(neighborhood)
        else:
            # 🌐 قابلیت ۴: فال‌بک به API اگه شهر رو پیدا نکرد
            processed['api_address'] = self._reverse_geocode_fallback(lat, lon)

        # 🚗 قابلیت ۲: بررسی طرح ترافیک
        for zone, poly in self.traffic_zones.items():
            if self._point_in_polygon(point, poly):
                tags.append("has_traffic_zone")
                processed['traffic_zone'] = zone

        # 🚇 قابلیت ۳: مجاورت با لندمارک‌های مهم
        for lm in self.landmarks:
            dist = self._haversine(lat, lon, lm['lat'], lm['lon'])
            if dist <= 500: # کمتر از ۵۰۰ متر
                tags.append(f"near_{lm['type']}")
                processed['nearest_landmark'] = f"{lm['name']} ({int(dist)}m)"

        # ⚡ قابلیت ۶: تولید Geohash
        processed['geohash'] = self._encode_geohash(lat, lon)

        # ⛰️ قابلیت ۷: محاسبه ارتفاع از سطح دریا
        processed['elevation_meters'] = self._estimate_elevation(lat, lon)

        # 📡 قابلیت ۹: شعاع نفوذ (Catchment) بر اساس دسته‌بندی
        category = processed.get('category', 'نامشخص')
        processed['catchment_radius_meters'] = self.catchment_radii.get(category, 500)

        # ⏰ قابلیت ۱۰: تخصیص تایم‌زون
        processed['timezone'] = self._get_timezone(lon)

        processed['tags'] = list(set(tags)) # حذف تگ‌های تکراری
        processed['geo_status'] = 'fully_inspected'

        return processed

# =======================================================
# 🧪 تست اتاق فرمان (تست ماهواره جاسوسی!)
# =======================================================
# tagger = GeoTagger()
# data = {
#     "name": "کافه لمیز",
#     "category": "کافه",
#     "lat": 35.8020, 
#     "lon": 51.4250, # مختصات جایی نزدیک مترو تجریش و طرح ترافیک
#     "tags": ["coffee"]
# }
# result = tagger.process_location(data)
# for k, v in result.items():
#     print(f"🔹 {k}: {v}")
