import datetime
from typing import List, Dict, Any

class HealthScorer:
    """
    💯 سیستم امتیازدهی سلامت داده (Ultimate Cyborg Edition)
    مجهز به ۱۰ موتور پردازشی برای پیش‌بینی کیفیت، قیمت‌گذاری اصلاح، و مسیردهی هوشمند!
    """

    def __init__(self):
        # ⚖️ جدول جریمه‌های پایه (Penalty Chart)
        self.base_penalties = {
            "MISSING_LOCATION": 50, "SUSPICIOUS_LOCATION_OUT_OF_BOUNDS": 60,
            "EXACT_LOCATION_COLLISION_DETECTED": 40, "MISSING_PHONE": 40,
            "BLACKLISTED_SPAM_PHONE": 80, "PROFANITY_OR_SPAM_DETECTED": 90,
            "MISSING_WEBSITE": 10, "INVALID_WEBSITE_URL": 15,
            "MISSING_AVATAR": 5, "ADDRESS_TOO_SHORT": 15
        }

        # 1️⃣ Feature 1: Dynamic Category Weighting (وزن‌دهی داینامیک بیزینس)
        # راهنما: اگه خواستی سخت‌گیری روی اصناف رو عوض کنی اینجا رو تغییر بده
        self.category_multipliers = {
            "IT": {"MISSING_WEBSITE": 3.0, "MISSING_AVATAR": 2.0},      # آی‌تی بدون سایت؟ فاجعه! (۳ برابر جریمه)
            "نانوایی": {"MISSING_WEBSITE": 0.0, "MISSING_AVATAR": 0.5}, # نانوا سایت نمی‌خواد (جریمه صفر)
            "رستوران": {"MISSING_AVATAR": 2.0, "MISSING_LOCATION": 1.5} # رستوران بدون عکس و لوکیشن نابوده
        }

        # 2️⃣ Feature 2: Source Trust Multiplier (ضریب اعتبار منبع)
        self.source_trust = {
            "official_api": 1.1,  # دیتای رسمی؟ 10% نمره بیشتر!
            "web_crawler": 1.0,   # خنثی
            "telegram_bot": 0.8,  # دیتای تلگرام همیشه بوداره (20% افت نمره)
            "user_submit": 0.7    # دیتای تولید کاربر (UGC) به شدت غیرقابل اعتماده
        }

        # 🔟 Feature 10: Historical Moving Average (حافظه سیستم)
        self.score_history = [] 

    # ==========================================
    # ⚙️ موتورهای پردازشی ۱۰ گانه
    # ==========================================

    def _calculate_temporal_decay(self, months_old: int) -> int:
        """ 5️⃣ Feature 5: Temporal Decay (پوسیدگی زمانی) """
        # هر ماه که از عمر دیتا بگذره و آپدیت نشه، ۲ نمره ازش کم می‌شه (حداکثر ۴۰ نمره)
        decay = min(40, months_old * 2)
        return decay

    def _calculate_seo_index(self, defects: List[str], record: Dict[str, Any]) -> int:
        """ 3️⃣ Feature 3: SEO-Readiness Index (آمادگی برای موتورهای جستجو) """
        seo_score = 100
        if "MISSING_WEBSITE" in defects: seo_score -= 30
        if "MISSING_DESCRIPTION" in defects: seo_score -= 20
        if "KEYWORD_STUFFING_NAME" in defects: seo_score -= 40 # گوگل از کیبورد استافینگ متنفره!
        if not record.get("avatar_url"): seo_score -= 10
        return max(0, seo_score)

    def _calculate_bounty(self, final_score: float) -> int:
        """ 4️⃣ Feature 4: Bounty Calculator (تعیین دستمزد برای اپراتور اصلاح) """
        if final_score >= 90: return 0 # دیتا تمیزه، پاداش نداره
        if final_score < 30: return 0  # دیتا زباله‌ست، ارزش وقت گذاشتن نداره!
        # برای دیتای متوسط، بر اساس میزان خرابی پول می‌دیم (مثلاً مکس ۵۰۰۰ تومن)
        return int((100 - final_score) * 50) 

    def _can_auto_fix(self, defects: List[str]) -> bool:
        """ 6️⃣ Feature 6: Auto-Fix Predictor (پیش‌بینی قابلیت خوددرمانی) """
        # ارورهایی که فقط با یه ریجکس یا اسکریپت ساده حل میشن
        auto_fixable_errors = {"INVALID_PHONE_FORMAT", "ADDRESS_TOO_SHORT", "INVALID_WEBSITE_URL"}
        # اگه حتی یک ارور غیرقابل تعمیر (مثل لوکیشن فیک) داشت، فالس میشه
        return all(d in auto_fixable_errors for d in defects) and len(defects) > 0

    def _generate_badges(self, defects: List[str]) -> str:
        """ 7️⃣ Feature 7: Visual Dashboard Badges (بج‌های بصری داشبورد) """
        badges = []
        badges.append("📍❌" if "MISSING_LOCATION" in defects else "📍✅")
        badges.append("📞❌" if any("PHONE" in d for d in defects) else "📞✅")
        badges.append("🌐❌" if "MISSING_WEBSITE" in defects else "🌐✅")
        return " | ".join(badges)

    def _check_consistency_bonus(self, record: Dict[str, Any]) -> int:
        """ 8️⃣ Feature 8: Consistency Bonus (پاداش هماهنگی آدرس و تلفن) """
        bonus = 0
        phone = str(record.get("phone", ""))
        address = str(record.get("address", ""))
        # اگه پیش‌شماره تهران بود و کلمه تهران هم تو آدرس بود = ۱۰ امتیاز جایزه!
        if phone.startswith("021") and "تهران" in address:
            bonus += 10
        return bonus

    def _determine_routing(self, tier: str) -> str:
        """ 9️⃣ Feature 9: VIP Exporter Routing (مسیردهی به فایل خروجی مناسب) """
        routes = {
            "PLATINUM 💎": "exports/json/map_ready_vip.json",
            "GOLD 🥇": "exports/excel/good_records.xlsx",
            "SILVER 🥈": "exports/csv/human_review_needed.csv",
            "TRASH 🗑️": "exports/csv/trash_bin.csv"
        }
        return routes.get(tier, "exports/csv/uncategorized.csv")

    def _determine_tier(self, score: float) -> str:
        if score >= 90: return "PLATINUM 💎"
        elif score >= 70: return "GOLD 🥇"
        elif score >= 40: return "SILVER 🥈"
        else: return "TRASH 🗑️"

    # ==========================================
    # 🚀 هسته اصلی قضاوت (The Brain)
    # ==========================================

    def evaluate(self, record: Dict[str, Any], defects: List[str], source: str = "web_crawler", months_old: int = 0) -> Dict[str, Any]:
        
        category = record.get("category", "عمومی")
        score = 100.0
        applied_penalties = {}

        # ۱. اعمال جریمه‌ها + منطق داینامیک اصناف (Feature 1)
        for defect in defects:
            base_penalty = self.base_penalties.get(defect, 10) # دیفالت 10
            # بررسی اینکه آیا برای این صنف خاص، این ارور ضریب متفاوتی داره یا نه؟
            cat_multiplier = self.category_multipliers.get(category, {}).get(defect, 1.0)
            
            final_penalty = base_penalty * cat_multiplier
            score -= final_penalty
            if final_penalty > 0:
                applied_penalties[defect] = final_penalty

        # ۲. اعمال پوسیدگی زمانی (Feature 5)
        decay = self._calculate_temporal_decay(months_old)
        score -= decay

        # ۳. اعمال ضریب اعتماد منبع (Feature 2)
        trust_multiplier = self.source_trust.get(source, 1.0)
        score = score * trust_multiplier

        # ۴. پاداش هماهنگی (Feature 8)
        score += self._check_consistency_bonus(record)

        # ۵. نرمال‌سازی نمره (بین ۰ تا ۱۰۰)
        final_score = max(0.0, min(100.0, round(score, 1)))
        
        # ذخیره در تاریخچه برای معدل‌گیری (Feature 10)
        self.score_history.append(final_score)

        # ۶. محاسبه سایر فیچرها
        tier = self._determine_tier(final_score)
        
        return {
            "record_id": record.get("id", "UNKNOWN"),
            "health_score": final_score,
            "tier": tier,
            "seo_readiness_index": f"{self._calculate_seo_index(defects, record)}/100", # Feature 3
            "bounty_toman": self._calculate_bounty(final_score),                        # Feature 4
            "can_be_auto_fixed": self._can_auto_fix(defects),                           # Feature 6
            "dashboard_badges": self._generate_badges(defects),                         # Feature 7
            "exporter_route": self._determine_routing(tier),                            # Feature 9
            "details": {
                "penalties": applied_penalties,
                "decay_applied": decay,
                "trust_multiplier": trust_multiplier
            }
        }

    def get_historical_average(self) -> float:
        """ 🔟 دریافت معدل کیفیت کل بچ (Batch) """
        if not self.score_history: return 0.0
        return round(sum(self.score_history) / len(self.score_history), 2)


# --- تست درایو (آزمایش سیستم با دو دیتای متفاوت) ---
if __name__ == "__main__":
    scorer = HealthScorer()
    
    # 1️⃣ دیتای اول: یه نانوایی از تلگرام که ۱ سال پیش ثبت شده و سایت نداره
    nanvaei = {"id": "N-101", "phone": "02177777777", "address": "تهران، تهرانپارس", "category": "نانوایی"}
    defects_1 = ["MISSING_WEBSITE", "ADDRESS_TOO_SHORT"]
    
    # 2️⃣ دیتای دوم: یه شرکت آی‌تی از API رسمی که سایت نداره!
    it_company = {"id": "IT-202", "phone": "09121111111", "address": "کرج، مهرشهر", "category": "IT"}
    defects_2 = ["MISSING_WEBSITE", "MISSING_AVATAR"]

    print("🥖 گزارش نانوایی (تلگرام - قدیمی):")
    rep1 = scorer.evaluate(nanvaei, defects_1, source="telegram_bot", months_old=12)
    for k, v in rep1.items(): print(f"  {k}: {v}")
    
    print("\n💻 گزارش شرکت IT (رسمی - جدید):")
    rep2 = scorer.evaluate(it_company, defects_2, source="official_api", months_old=0)
    for k, v in rep2.items(): print(f"  {k}: {v}")
    
    print(f"\n📈 معدل کیفیت کل سیستم تا این لحظه (Moving Average): {scorer.get_historical_average()}/100")
