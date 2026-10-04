import re
import requests
from typing import Dict, Any, List, Set
from collections import defaultdict

class DefectFinder:
    """
    🕵️‍♂️ کارآگاه ویژه و تمام‌عیار بررسی نواقص داده‌ها (CIA Edition)
    با ۱۰ قابلیت فوق‌پیشرفته برای شکار داده‌های کثیف، فیک و اسپم!
    """

    def __init__(self):
        # ⚙️ تنظیمات پایه
        self.phone_regex = re.compile(r'^(09\d{9}|0[1-8]\d{7,8})$')
        self.min_address_length = 10 
        self.iran_bounds = {"lat": (25.0, 40.0), "lng": (44.0, 64.0)}
        
        # 🗑️ لیست سیاه اسپم‌ها (Feature 4 & 7)
        self.spam_keywords = ["سایت شرط", "کازینو", "صیغه", "فالگیر", "تضمینی"]
        self.spam_phones = {"09120000000", "09350000000"} # تلفن‌های بلک‌لیست
        
        # 🧠 حافظه کوتاه مدت برای کشف تقلب‌های بین-رکوردی (Feature 9)
        self.phone_registry = defaultdict(int)
        self.location_registry = set()

    # ==========================================
    # 🕵️‍♂️ متدهای بازجویی (۱۰ قابلیت خفن)
    # ==========================================

    def _check_basic_phone(self, phone: str) -> str:
        """ بررسی اولیه شماره تماس """
        if not phone: return "MISSING_PHONE"
        clean_phone = re.sub(r'[\s\-+]', '', phone)
        if not self.phone_regex.match(clean_phone): return "INVALID_PHONE_FORMAT"
        return None

    def _check_phone_spam_and_duplication(self, phone: str) -> List[str]:
        """ 📞 Feature 7 & 9: لیست سیاه و تناسخ شماره تماس """
        defects = []
        clean_phone = re.sub(r'[\s\-+]', '', str(phone)) if phone else ""
        
        # Feature 7: Phone Spam Registry
        if clean_phone in self.spam_phones:
            defects.append("BLACKLISTED_SPAM_PHONE")
            
        # Feature 9: Cross-Entity Duplication (تست تناسخ)
        # اگه این شماره رو تو این بچ (Batch) بیشتر از ۳ بار دیدیم، یعنی یه ریگی به کفششه!
        if clean_phone:
            self.phone_registry[clean_phone] += 1
            if self.phone_registry[clean_phone] > 3:
                defects.append("SERIAL_PHONE_DUPLICATION")
                
        return defects

    def _check_keyword_stuffing_and_profanity(self, name: str) -> List[str]:
        """ 🏷️ Feature 4 & 8: فیلتر دهان‌شویه و کلاه‌بردار سئو """
        defects = []
        if not name: return ["MISSING_NAME"]
        
        # Feature 8: Keyword Stuffing (اگه اسمش بیشتر از ۶ کلمه است)
        if len(name.split()) > 6:
            defects.append("KEYWORD_STUFFING_NAME")
            
        # Feature 4: Profanity & Spam Filter
        if any(bad_word in name for bad_word in self.spam_keywords):
            defects.append("PROFANITY_OR_SPAM_DETECTED")
            
        # تشخیص اسم‌های کیبوردی (مثل asdasd)
        if re.search(r'(.)\1{4,}', name): # ۵ حرف تکراری پشت سر هم
            defects.append("GIBBERISH_NAME")
            
        return defects

    def _check_website_ping(self, website: str) -> str:
        """ 🌐 Feature 1: نبض‌سنج وب‌سایت (پینگ سریع) """
        if not website: return None
        if not website.startswith(("http://", "https://")): return "INVALID_WEBSITE_URL"
        
        # یه درخواست HEAD سبک میزنیم (تایم‌اوت ۲ ثانیه) که باتل‌نک نشه
        try:
            # در محیط واقعی می‌تونی اینو غیرهمزمان (Async) کنی که سرعت بچ‌ها نیاد پایین
            response = requests.head(website, timeout=2, allow_redirects=True)
            if response.status_code >= 400:
                return f"WEBSITE_DEAD_OR_BROKEN_HTTP_{response.status_code}"
        except requests.RequestException:
            return "WEBSITE_UNREACHABLE"
        return None

    def _check_business_hours(self, hours: str, category: str) -> str:
        """ 🕒 Feature 5: کارآگاه شب‌زنده‌دار (منطق ساعات کاری) """
        if not hours or not category: return None
        
        # اگه مهدکودک یا اداره دولتیه، ولی نوشته باز تا ۳ صبح!
        if category in ["مهدکودک", "مدرسه", "اداره"] and "03:00" in hours:
            return "LOGICAL_DEFECT_WEIRD_HOURS"
        return None

    def _check_fake_avatar(self, avatar_url: str) -> str:
        """ 🖼️ Feature 6: تشخیص چهره قلابی """
        if not avatar_url: return "MISSING_AVATAR"
        
        fake_keywords = ["default", "no_avatar", "placeholder", "blank"]
        if any(word in avatar_url.lower() for word in fake_keywords):
            return "FAKE_DEFAULT_AVATAR"
        return None

    def _check_nlp_context(self, description: str) -> str:
        """ 🧠 Feature 10: روانشناس متن (NLP ساده) """
        if not description: return "MISSING_DESCRIPTION"
        
        # اگه توضیحات کلا از ایموجی تشکیل شده باشه یا حروف بی‌معنی باشه
        emoji_count = len(re.findall(r'[^\w\s,\.\?!]', description))
        if emoji_count > 10 and len(description.split()) < 5:
            return "SPAMMY_DESCRIPTION_TOO_MANY_EMOJIS"
            
        return None

    def _check_geo_mismatch_and_collision(self, lat: float, lng: float, address: str) -> List[str]:
        """ 📍 Feature 2 & 3: دروغ‌سنج مکانی و رادار همسایه مزاحم """
        defects = []
        if lat is None or lng is None: return ["MISSING_LOCATION"]
            
        # بررسی مرزهای ایران
        if not (self.iran_bounds["lat"][0] <= lat <= self.iran_bounds["lat"][1]) or \
           not (self.iran_bounds["lng"][0] <= lng <= self.iran_bounds["lng"][1]):
            defects.append("SUSPICIOUS_LOCATION_OUT_OF_BOUNDS")
            return defects

        # Feature 3: Competitor Collision
        # برای بچ‌های ۱۰۰ تایی، این لوکیشن‌ها رو تو رم ذخیره می‌کنیم که روی هم نیفتن
        coord_tuple = (round(lat, 4), round(lng, 4)) # گرد کردن تا دقت حدود 10 متر
        if coord_tuple in self.location_registry:
            defects.append("EXACT_LOCATION_COLLISION_DETECTED")
        else:
            self.location_registry.add(coord_tuple)
            
        # Feature 2: Geo-Address Mismatch (شبیه‌سازی)
        # تو دنیای واقعی اینجا میتونی یه دیکشنری شهر به مختصات داشته باشی
        if address and "تهران" in address and lat < 34.0: 
            # عرض جغرافیایی زیر 34 دیگه تهران نیست!
            defects.append("GEO_ADDRESS_MISMATCH_NOT_IN_TEHRAN")

        return defects

    # ==========================================
    # 🚀 فرماندهی عملیات بازجویی
    # ==========================================

    def inspect_record(self, record: Dict[str, Any]) -> List[str]:
        """ گرفتن گریبان رکورد و لیست کردن تمام جرائم! """
        defects = []
        
        # استخراج فیلدها
        phone = record.get("phone")
        name = record.get("name", "")
        address = record.get("address", "")
        lat, lng = record.get("lat"), record.get("lng")
        website = record.get("website")
        
        # اجرای تست‌های پایه
        if err := self._check_basic_phone(phone): defects.append(err)
        if len(address.strip()) < self.min_address_length: defects.append("ADDRESS_TOO_SHORT")
            
        # اجرای ۱۰ قابلیت پیشرفته
        defects.extend(self._check_phone_spam_and_duplication(phone))
        defects.extend(self._check_keyword_stuffing_and_profanity(name))
        defects.extend(self._check_geo_mismatch_and_collision(lat, lng, address))
        
        if err := self._check_business_hours(record.get("hours"), record.get("category")): defects.append(err)
        if err := self._check_fake_avatar(record.get("avatar_url")): defects.append(err)
        if err := self._check_nlp_context(record.get("description")): defects.append(err)
        
        # پینگ وب‌سایت رو میذاریم آخر که اگه بقیه چیزا اوکی بود، وقتمون رو سر نت تلف کنیم
        # راهنما: اگه دیدی سرعت بچ (Batch) کند شد، این خط رو کامنت کن!
        if err := self._check_website_ping(website): defects.append(err)
            
        return defects


# --- مثال اجرای تستی مچ‌گیری ---
if __name__ == "__main__":
    inspector = DefectFinder()
    
    super_shady_business = {
        "name": "لوله بازکنی تخلیه چاه ارزان فوری شبانه‌روزی تضمینی", # Keyword Stuffing + Spam
        "phone": "09120000000", # Blacklisted Spam
        "address": "تهران، خیابان ولیعصر", # Geo Mismatch (lat says otherwise)
        "lat": 29.61, "lng": 52.53, # مختصات شیرازه ولی نوشته تهران!
        "website": "https://this-site-definitely-does-not-exist-123.com", # Dead URL
        "category": "مدرسه", 
        "hours": "03:00 - 05:00", # Weird hours
        "avatar_url": "http://img.com/default_avatar.png", # Fake Avatar
        "description": "🔥🔥🔥🚀🚀🚀💥💥💥" # NLP Spam
    }
    
    crimes = inspector.inspect_record(super_shady_business)
    print("🚨 لیست اتهامات مجرم:")
    for crime in crimes:
        print(f" ❌ {crime}")
