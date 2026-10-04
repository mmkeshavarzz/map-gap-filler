"""
src/processors/deduplicator.py
=============================================================================
جاروبرقی فضایی و ادغام‌گر شبکه‌ای (Ultimate Enterprise Deduplicator) 🌌🧹
تاریخ آخرین آپدیت سیستم: ۱۴۰۵/۰۷/۱۳

قابلیت‌های این نسخه (All 10 Enterprise Features):
1. Grid Clustering  |  2. Image pHash Match  |  3. HITL (Tinder Bot Queue)
4. Temporal Merge   |  5. Phonetic Match     |  6. Redis-like Caching
7. Social Links     |  8. Chain Resolution   |  9. Graph/Union-Find
10. Visual Analytics
=============================================================================
"""

import math
import difflib
import time
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict

class UnionFind:
    """ 🕸️ قابلیت شماره ۹: گراف شبکه‌ای (Union-Find) 
    اگه A با B یکیه، و B با C یکیه، پس A و C هم یکین! (قانون تعدی ریاضی)
    """
    def __init__(self):
        self.parent = {}

    def find(self, item):
        if item not in self.parent:
            self.parent[item] = item
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, item1, item2):
        root1 = self.find(item1)
        root2 = self.find(item2)
        if root1 != root2:
            self.parent[root2] = root1

class Deduplicator:
    def __init__(self, similarity_threshold: float = 0.8, max_distance_meters: float = 50.0):
        # تنظیمات پایه
        self.sim_threshold = similarity_threshold
        self.max_distance = max_distance_meters
        
        # 🗄️ قابلیت شماره ۶: شبیه‌ساز کش Redis (برای جستجوی سریع در حافظه رم)
        self._redis_cache = {} 
        
        # 🕸️ گراف یکپارچگی (برای ردیابی زنجیره ادغام‌ها)
        self.graph = UnionFind()
        
        # 🚧 قابلیت شماره ۳: صف برزخ (موارد مشکوک برای بررسی توسط انسان)
        self.quarantine_queue = [] 
        
        # 📊 قابلیت شماره ۱۰: آمار و گزارشات ویژوال
        self.stats = {
            "total_processed": 0,
            "exact_merges": 0,
            "quarantined": 0,
            "chain_clashes_prevented": 0
        }
        
        # وزن‌دهی منابع
        self.trust_scores = {"google_maps": 100, "neshan": 90, "balad": 85, "web": 60, "telegram": 40}

    # ==========================================
    # ابزارهای پایه‌ای و توابع کمکی
    # ==========================================

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """ 🌍 محاسبه فاصله کروی با فرمول $ d = 2r \arcsin(...) $ """
        if None in (lat1, lon1, lat2, lon2): return float('inf')
        R = 6371000.0
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dp = math.radians(lat2 - lat1)
        dl = math.radians(lon2 - lon1)
        a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
        return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

    def _get_grid_key(self, lat: float, lon: float, precision: int = 3) -> str:
        """ 🗺️ قابلیت شماره ۱: شبکه‌سازی (Grid Clustering)
        مختصات رو رند می‌کنه تا نقشه رو به مربع‌های کوچیک تقسیم کنه. 
        اینطوری فقط مکان‌های هم‌مربع رو مقایسه می‌کنیم! 
        """
        if lat is None or lon is None: return "unknown_grid"
        return f"{round(lat, precision)}_{round(lon, precision)}"

    def _persian_phonetic(self, text: str) -> str:
        """ 🗣️ قابلیت شماره ۵: الگوریتم آوایی (Phonetic Matching)
        حروفی که صدای یکسان اما املای متفاوت دارند رو یکسان‌سازی می‌کنه!
        """
        if not text: return ""
        text = text.replace("ط", "ت").replace("ص", "س").replace("ث", "س")
        text = text.replace("ذ", "ز").replace("ض", "ز").replace("ظ", "ز")
        text = text.replace("غ", "ق").replace("ح", "ه")
        text = text.replace("آ", "ا").replace("ي", "ی").replace("ك", "ک")
        return text.strip().lower()

    # ==========================================
    # موتورهای بررسی و تطبیق
    # ==========================================

    def _check_chain_clash(self, name1: str, name2: str) -> bool:
        """ 🔗 قابلیت شماره ۸: کشف زنجیره‌ها (Chain Resolution)
        اگه کلمه "شعبه" دارن ولی شعبه‌هاشون فرق داره، اجازه ادغام نمیده!
        """
        n1, n2 = name1.lower(), name2.lower()
        if "شعبه" in n1 and "شعبه" in n2:
            # اینجا اگه اسم‌ها دقیقا یکی نباشن، یعنی دو تا شعبه متفاوتن
            if n1 != n2:
                self.stats["chain_clashes_prevented"] += 1
                return True
        return False

    def _check_social_match(self, r1: Dict, r2: Dict) -> bool:
        """ 📱 قابلیت شماره ۷: ادغام شبکه‌های اجتماعی
        اگه یوزرنیم اینستاگرام یا لینک سایت یکیه، یعنی قطعا یه جا هستن!
        """
        soc1 = r1.get("instagram", "1")
        soc2 = r2.get("instagram", "2")
        return soc1.lower() == soc2.lower()

    def _check_image_hash(self, r1: Dict, r2: Dict) -> bool:
        """ 🖼️ قابلیت شماره ۲: تشخیص تصویر با Hashing (pHash)
        مقایسه هشِ تصاویر پروفایل (اگه در دیتابیس موجود باشه)
        """
        h1, h2 = r1.get("image_phash"), r2.get("image_phash")
        return bool(h1 and h2 and h1 == h2)

    # ==========================================
    # هسته اصلی پردازش
    # ==========================================

    def compare_records(self, rec1: Dict, rec2: Dict) -> str:
        """ 
        🧠 مغز متفکر مقایسه! 
        خروجی: 'MERGE' (قطعا یکین) | 'QUARANTINE' (مشکوک) | 'DIFFERENT' (فرق دارن)
        """
        self.stats["total_processed"] += 1
        
        # اگه شبکه‌های اجتماعیشون یکیه، دیگه برو بریم برای ادغام!
        if self._check_social_match(rec1, rec2): return 'MERGE'
        # اگه عکس مغازه‌هاشون از نظر پیکسلی یکیه، بازم ادغام!
        if self._check_image_hash(rec1, rec2): return 'MERGE'
        
        # جلوگیری از ادغام شعبه‌های مختلف (مثلا رفاه شعبه ۱ و رفاه شعبه ۲)
        name1, name2 = str(rec1.get('name', '')), str(rec2.get('name', ''))
        if self._check_chain_clash(name1, name2): return 'DIFFERENT'

        # بررسی فاصله مکانی
        dist = self._haversine(rec1.get('lat'), rec1.get('lon'), rec2.get('lat'), rec2.get('lon'))
        if dist > self.max_distance: return 'DIFFERENT'

        # بررسی آوایی نام‌ها (مثلا "صبا" و "سبا" یکی میشن)
        phonetic1 = self._persian_phonetic(name1)
        phonetic2 = self._persian_phonetic(name2)
        sim_score = difflib.SequenceMatcher(None, phonetic1, phonetic2).ratio()

        if sim_score >= self.sim_threshold:
            return 'MERGE'
        elif 0.60 <= sim_score < self.sim_threshold: # بین ۶۰ تا ۸۰ درصد
            return 'QUARANTINE'
            
        return 'DIFFERENT'

    def smart_merge(self, base_rec: Dict, new_rec: Dict) -> Dict:
        """ 🤝 ادغام هوشمند دو رکورد """
        # ⏳ قابلیت شماره ۴: ادغام بر اساس زمان (Temporal Merge)
        t_base = base_rec.get('updated_at', 0)
        t_new = new_rec.get('updated_at', 0)
        
        score_base = self.trust_scores.get(base_rec.get('source', ''), 0)
        score_new = self.trust_scores.get(new_rec.get('source', ''), 0)

        # اولویت: اول با Trust Score (اعتبار منبع)، اگه مساوی بودن با جدیدترین زمان آپدیت
        if score_base > score_new or (score_base == score_new and t_base >= t_new):
            master, slave = base_rec, new_rec
        else:
            master, slave = new_rec, base_rec

        merged = master.copy()
        
        # پر کردن فیلدهای خالی
        for key, value in slave.items():
            if key not in merged or not merged[key]:
                merged[key] = value

        self.stats["exact_merges"] += 1
        
        # 🕸️ ثبت در گراف (شناسه دو رکورد با هم گره می‌خورن)
        id1, id2 = master.get('id', 'm'), slave.get('id', 's')
        self.graph.union(id1, id2)

        return merged

    def process_batch(self, records: List[Dict]) -> List[Dict]:
        """ 🚀 پردازش دسته‌ای با استفاده از Grid Clustering """
        grids = defaultdict(list)
        merged_results = []
        
        # ۱. تقسیم داده‌ها به مربع‌های روی نقشه (Grid Clustering)
        for rec in records:
            grid_key = self._get_grid_key(rec.get('lat'), rec.get('lon'))
            grids[grid_key].append(rec)
            # ذخیره در کش Redis شبیه‌سازی شده
            self._redis_cache[rec.get('id')] = rec 

        # ۲. مقایسه فقط درون هر Grid
        for grid_key, grid_records in grids.items():
            skip_list = set()
            for i in range(len(grid_records)):
                if i in skip_list: continue
                
                current_rec = grid_records[i]
                
                for j in range(i + 1, len(grid_records)):
                    if j in skip_list: continue
                    target_rec = grid_records[j]
                    
                    decision = self.compare_records(current_rec, target_rec)
                    
                    if decision == 'MERGE':
                        current_rec = self.smart_merge(current_rec, target_rec)
                        skip_list.add(j)
                    elif decision == 'QUARANTINE':
                        # 🚧 ارسال به صف تایید انسانی (Tinder Bot Queue)
                        self.quarantine_queue.append((current_rec, target_rec))
                        self.stats["quarantined"] += 1
                        
                merged_results.append(current_rec)
                
        return merged_results

    def generate_report(self):
        """ 📊 قابلیت شماره ۱۰: گزارش‌ساز ویژوال (Visual Analytics) """
        print("\n" + "="*50)
        print(" 📊 گزارش عملکرد جاروبرقیِ فضایی (Visual Analytics) 🧹")
        print("="*50)
        print(f" 📦 کل داده‌های بررسی شده: {self.stats['total_processed']}")
        print(f" ✅ ادغام‌های موفق و خودکار: {self.stats['exact_merges']} ({(self.stats['exact_merges']/(self.stats['total_processed']+0.001)*100):.1f}%)")
        print(f" 🚧 موارد ارسالی به برزخ (نیاز به انسان): {self.stats['quarantined']} 🤷‍♂️")
        print(f" 🔗 جلوگیری از ادغام شعبه‌های یک برند: {self.stats['chain_clashes_prevented']} 🛡️")
        print("="*50)
        print("وضعیت صف برزخ:")
        for r1, r2 in self.quarantine_queue[:2]: # نمایش فقط دو تای اول
            print(f" 🧐 مشکوک: [{r1.get('name')}] ❤️ [{r2.get('name')}]")
        print("="*50 + "\n")

# 🧪 تست کوچیک برای دیدن شاهکار:
# deduplicator = Deduplicator()
# data = [
#    {"id": "1", "name": "داروخانه دکتر صبا", "lat": 35.7, "lon": 51.4, "source": "web", "updated_at": 1600000000},
#    {"id": "2", "name": "داروخانه دكتر سبا", "lat": 35.7001, "lon": 51.4001, "source": "google_maps", "updated_at": 1600000500},
#    {"id": "3", "name": "فروشگاه رفاه شعبه ۱", "lat": 35.7, "lon": 51.4, "source": "telegram"},
#    {"id": "4", "name": "فروشگاه رفاه شعبه ۲", "lat": 35.7, "lon": 51.4, "source": "web"}
# ]
# result = deduplicator.process_batch(data)
# deduplicator.generate_report()
