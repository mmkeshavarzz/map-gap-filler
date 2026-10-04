"""
src/refiners/address_parser.py
=============================================================================
پالایشگاه آدرس (Terminator Postman Edition) 🤖📬
تجهیزات اضافه شده (۱۰ قابلیت خفن): 
هوش مصنوعی، دیکشنری، شکارچی لندمارک، اعتبارسنج کد پستی، طبقه/واحد، 
تطبیق فازی، حذف نویز، تحلیل معکوس، دستیار مختصات، و امتیازدهی کیفیت! 🌟
=============================================================================
"""

import re
import difflib
import asyncio
from typing import Dict, Optional, Any

class AddressParser:
    """
    پستچی ترمیناتور! هیچ آدرسی از دستش قسر در نمیره. 🦾
    """

    def __init__(self):
        # 📚 ۲. فرهنگ لغات جغرافیایی (Gazetteer Dictionary) برای اصلاحات
        self.cities_db = ["تهران", "مشهد", "اصفهان", "شیراز", "تبریز", "کرج", "اهواز"]
        
        # 🔇 ۷. لیست کلمات نویز و تبلیغاتی (Noise Eraser)
        self.noise_words = [
            r"ارسال رایگان\s*(به سراسر کشور)?", 
            r"تخفیف ویژه", r"لینک در بیو", r"جهت هماهنگی", r"دایرکت پیام دهید", r"فروش آنلاین"
        ]

        # ⚙️ الگوهای کلاسیک و جدید
        self.patterns = {
            "province": r"(?:استان)\s+([آ-ی\s]+?)(?=\s+(?:شهر|شهرستان|بخش|روستا|خ|خیابان|م|میدان|بلوار|ک|کوچه|پلاک|،|-|$))",
            "city": r"(?:شهر|شهرستان)\s+([آ-ی\s]+?)(?=\s+(?:بخش|روستا|خ|خیابان|م|میدان|بلوار|ک|کوچه|پلاک|،|-|$))",
            "street": r"(?:خیابان|خ)\s+([آ-ی\d\s]+?)(?=\s+(?:میدان|م|بلوار|کوچه|ک|پلاک|پ|،|-|$))",
            "square": r"(?:میدان|میدون|م)\s+([آ-ی\d\s]+?)(?=\s+(?:خ|خیابان|بلوار|کوچه|ک|پلاک|پ|،|-|$))",
            "blv": r"(?:بلوار)\s+([آ-ی\d\s]+?)(?=\s+(?:خ|خیابان|میدان|م|کوچه|ک|پلاک|پ|،|-|$))",
            "alley": r"(?:کوچه|ک)\s+([آ-ی\d\s]+?)(?=\s+(?:پلاک|پ|طبقه|ط|واحد|،|-|$))",
            "plaque": r"(?:پلاک|پ|شماره)\s*(\d+|[۰-۹]+)",
            
            # 🏢 ۵. استخراج‌گر طبقه و واحد (Floor & Unit Extractor)
            "floor": r"(?:طبقه|ط)\s*(\d+|[۰-۹]+|همکف|اول|دوم|سوم|چهارم|پنجم)",
            "unit": r"(?:واحد|زنگ)\s*(\d+|[۰-۹]+)",
            
            # 🕌 ۳. شکارچی لندمارک (Landmark Extractor)
            "landmark": r"(?:جنب|روبروی|روبرو|پشت|نرسیده به|تقاطع|بالاتر از|پایین تر از)\s+([آ-ی\d\s]+?)(?=\s+(?:خ|کوچه|پلاک|،|-|$))"
        }

    def _remove_noise(self, text: str) -> str:
        """لیزر نابودگر نویزهای تبلیغاتی! 🔫"""
        for noise in self.noise_words:
            text = re.sub(noise, "", text)
        return text

    def _normalize_text(self, raw_address: str) -> str:
        """حمامِ متن + حذف نویز! 🛁"""
        if not raw_address:
            return ""

        text = raw_address.strip()
        text = self._remove_noise(text) # حذف تبلیغات
        
        # استانداردسازی حروف
        text = text.replace('ي', 'ی').replace('ك', 'ک').replace('ة', 'ه')
        
        # تبدیل اعداد عربی/فارسی به انگلیسی
        persian_nums, arabic_nums, english_nums = '۰۱۲۳۴۵۶۷۸۹', '٠١٢٣٤٥٦٧٨٩', '0123456789'
        trans_table = str.maketrans(persian_nums + arabic_nums, english_nums + english_nums)
        text = text.translate(trans_table)

        # حذف نیم‌فاصله‌ها و فاصله‌های تکراری
        text = re.sub(r'\u200c', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text

    def _fuzzy_match_city(self, city_name: str) -> str:
        """😵‍💫 ۶. تطبیق فازی (Fuzzy Matching) - اصلاح غلط املایی شهرهای معروف"""
        if not city_name: return city_name
        # اگه نوشته باشه "تهرون" یا "ولنجک"، نزدیک‌ترین رو پیدا می‌کنه
        matches = difflib.get_close_matches(city_name, self.cities_db, n=1, cutoff=0.7)
        return matches[0] if matches else city_name

    def _validate_postal_code(self, text: str) -> Optional[str]:
        """✉️ ۴. اعتبارسنج کد پستی (Postal Code Validator)"""
        # یه عدد ۱۰ رقمی که صفر اولش نباشه رو تو متن پیدا می‌کنه
        match = re.search(r'\b([1-9]\d{9})\b', text)
        if match:
            # اینجا میشه الگوریتم‌های پیچیده‌تر پست ایران رو هم پیاده کرد
            return match.group(1)
        return None

    def _calculate_score(self, parsed_data: Dict) -> int:
        """🌟 ۱۰. محاسبه‌گر امتیاز کیفیت دیتا (Quality Score) از ۰ تا ۱۰"""
        score = 0
        if parsed_data.get("city"): score += 2
        if parsed_data.get("street") or parsed_data.get("square") or parsed_data.get("boulevard"): score += 3
        if parsed_data.get("plaque"): score += 2
        if parsed_data.get("postal_code"): score += 2
        if parsed_data.get("landmark"): score += 1
        return min(score, 10) # سقفش ۱۰ئه!

    async def _ai_fallback_parser(self, raw_address: str) -> Dict:
        """🤖 ۱. موتور هوش مصنوعی (LLM-based NER) - واسه وقتی که Regex کم میاره!"""
        # اگر نمره آدرس خیلی کم بود، میفرستیمش برای AI (اینجا جای اتصال به API مثل GPT یا مدل لوکاله)
        # return await llm_client.ask(f"Extract address entities in JSON from: {raw_address}")
        return {"ai_note": "AI engine would parse this perfectly! 🧠 (API needed)"}

    async def geocode_address(self, clean_address: str) -> Dict[str, float]:
        """🌍 ۹. دستیار تبدیل به مختصات (API Geocoder)"""
        # جایگاه اتصال به API مپیکس یا نشان
        # async with aiohttp.ClientSession() as session:
        #    async with session.get(f"https://api.neshan.org/v4/geocoding?address={clean_address}") as resp: ...
        return {"lat": 35.6892, "lng": 51.3890, "mock": True} # مختصات فرضی تهران

    def _reverse_macro_micro_sort(self, parsed_data: Dict) -> str:
        """🔄 ۸. مسیریاب معکوس (Reverse Macro-Micro)"""
        # دیتای استخراج شده رو به ترتیب استاندارد (از بزرگ به کوچیک) می‌چینه و متن تمیز می‌سازه
        order = ["province", "city", "boulevard", "square", "street", "landmark", "alley", "plaque", "floor", "unit"]
        standard_address = []
        for key in order:
            if parsed_data.get(key):
                prefix = "پلاک " if key == "plaque" else "طبقه " if key == "floor" else "واحد " if key == "unit" else ""
                standard_address.append(f"{prefix}{parsed_data[key]}")
        
        return "، ".join(standard_address)

    async def parse(self, raw_address: str) -> Dict[str, Any]:
        """
        موتور اصلی ترمیناتور! ⚙️
        """
        clean_address = self._normalize_text(raw_address)
        
        parsed_data = {
            "raw_address": raw_address,
            "clean_address": clean_address,
            "province": None, "city": None, "square": None, "boulevard": None,
            "street": None, "landmark": None, "alley": None, "plaque": None,
            "floor": None, "unit": None, "postal_code": None,
            "standard_format": None,
            "quality_score": 0,
            "coords": None
        }

        # کالبدشکافی با Regex
        for key, pattern in self.patterns.items():
            match = re.search(pattern, clean_address)
            if match:
                val = match.group(1).strip().rstrip('،,-')
                
                # اعمال تطبیق فازی برای شهر
                if key == "city":
                    val = self._fuzzy_match_city(val)
                    
                parsed_data[key] = val

        # استخراج کد پستی
        parsed_data["postal_code"] = self._validate_postal_code(clean_address)

        # ساخت آدرس استاندارد معکوس
        parsed_data["standard_format"] = self._reverse_macro_micro_sort(parsed_data)

        # محاسبه نمره کیفیت
        parsed_data["quality_score"] = self._calculate_score(parsed_data)

        # اگه نمره خیلی افتضاح بود (کمتر از ۴)، از هوش مصنوعی کمک بگیر!
        if parsed_data["quality_score"] < 4:
            ai_data = await self._ai_fallback_parser(clean_address)
            parsed_data["ai_fallback"] = ai_data

        # به صورت آپشنال: گرفتن لوکیشن نقشه
        # اگه کیفیت آدرس خوب بود، بریم مختصاتش رو هم از API بگیریم
        if parsed_data["quality_score"] >= 7:
            parsed_data["coords"] = await self.geocode_address(parsed_data["standard_format"])

        return parsed_data

# === تست ترمیناتور! ===
if __name__ == "__main__":
    async def test():
        parser = AddressParser()
        # یه آدرس کثیف و پر از نویز و غلط املایی + لندمارک + کد پستی + تبلیغات!
        test_addr = " ارسال رایگان ! طهران، خ ولیعصر، جنب پارک ملت، کوچه بن بست اول، پ 12، طبقه دوم، واحد 4. کد پستی: 1967845321 لینک در بیو"
        
        print("آدرس خام:", test_addr)
        print("-" * 50)
        
        result = await parser.parse(test_addr)
        
        import json
        print(json.dumps(result, indent=4, ensure_ascii=False))

    # اجرای تست ناهمگام
    asyncio.run(test())
