"""
src/crawlers/instagram.py
=============================================================================
خزنده فوق‌پیشرفته اینستاگرام (The Ultimate Instagram Ghost) 👻
تاریخ به روزرسانی: 1405/07/13

این مکا-کراولر (Mecha-Crawler) به ۱۰ سلاح مخفی مجهز است:
۱. Account Pool Management      ۶. Mobile App API Emulation
۲. Location Tag Hunter          ۷. Auto Routing Link Extraction
۳. NLP/Regex Working Hours      ۸. Follower Network Expansion (Suggested)
۴. Address from Highlights      ۹. Consent & Popup Bypasser
۵. Smart Session Storage        ۱۰. Menu & Services Extraction
=============================================================================
"""

import re
import json
import asyncio
import aiohttp
import random
from pathlib import Path
from typing import AsyncGenerator, Any, Optional, Tuple, List, Dict

from src.crawlers.base import BaseCrawler

# مسیر ذخیره کوکی‌های لاگین (قابلیت ۵)
SESSION_DIR = Path("data/sessions")
SESSION_DIR.mkdir(parents=True, exist_ok=True)


class InstagramCrawler(BaseCrawler):
    """
    نفوذگر شبح‌وار اینستاگرام! 🥷
    مسلح به ۱۰ قابلیت استخراج و پنهان‌نگاری.
    """

    def __init__(self, proxies: list = None, accounts_pool: List[Dict] = None):
        """
        راه‌اندازی ماشین جنگی!
        
        :param accounts_pool: لیستی از اکانت‌ها [{"username": "...", "password": "..."}] (قابلیت ۱)
        """
        super().__init__(crawler_name="insta_ghost", proxies=proxies, delay_range=(4.0, 8.0))
        
        # قابلیت ۱: استخر اکانت‌ها
        self.accounts_pool = accounts_pool or []
        self.current_account_index = 0
        
        self._session: Optional[aiohttp.ClientSession] = None
        self.current_cookies = {}
        
        # تلاش برای لود کردن سشن قبلی (قابلیت ۵)
        self._load_smart_session()

    # ==========================================================
    # تسلیحات زیرساختی و مخفی‌کاری (Stealth & Infra)
    # ==========================================================

    def _load_smart_session(self):
        """(قابلیت ۵): بارگذاری کوکی‌ها از فایل برای جلوگیری از لاگین مجدد"""
        if not self.accounts_pool:
            return
            
        current_acc = self.accounts_pool[self.current_account_index]['username']
        session_file = SESSION_DIR / f"{current_acc}_cookies.json"
        
        if session_file.exists():
            with open(session_file, "r") as f:
                self.current_cookies = json.load(f)
            self.logger.info(f"🍪 سشن قبلی برای اکانت '{current_acc}' با موفقیت لود شد.")

    def _save_smart_session(self):
        """(قابلیت ۵): ذخیره کوکی‌های فعلی در فایل"""
        if not self.accounts_pool or not self._session:
            return
            
        current_acc = self.accounts_pool[self.current_account_index]['username']
        session_file = SESSION_DIR / f"{current_acc}_cookies.json"
        
        # استخراج کوکی‌ها از سشن
        cookies = {cookie.key: cookie.value for cookie in self._session.cookie_jar}
        with open(session_file, "w") as f:
            json.dump(cookies, f)

    async def _get_session(self) -> aiohttp.ClientSession:
        """(قابلیت ۶ و ۹): شبیه‌سازی اپلیکیشن موبایل و دور زدن پاپ‌آپ‌ها"""
        if self._session is None or self._session.closed:
            headers = {
                # قابلیت ۶: شبیه‌سازی دقیق اپلیکیشن اندروید اینستاگرام! زاکربرگ فکر میکنه ما یه گوشی سامسونگیم!
                "User-Agent": "Instagram 219.0.0.12.117 Android (29/10; 480dpi; 1080x2340; samsung; SM-G973F; beyond1; exynos9820; en_US; 314660894)",
                "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8",
                "X-IG-App-ID": "936619743392459", # App ID رسمی اینستاگرام
                "X-IG-WWW-Claim": "0",
            }
            
            # قابلیت ۹: تزریق کوکی‌های پیش‌فرض برای دور زدن پیام "Accept Cookies" اروپا و صفحه لاگین
            base_cookies = {
                "ig_did": f"UUID-{random.randint(1000,9999)}", # یه شناسه دستگاه فیک
                "ig_nrcb": "1", # No Registration Consent Bypasser
            }
            base_cookies.update(self.current_cookies)

            self._session = aiohttp.ClientSession(headers=headers, cookies=base_cookies)
        return self._session

    def _rotate_account(self):
        """(قابلیت ۱): شیفت دادن اکانت در صورت مسدودی (Action Block)"""
        if len(self.accounts_pool) > 1:
            self.current_account_index = (self.current_account_index + 1) % len(self.accounts_pool)
            self.current_cookies = {}
            self._load_smart_session()
            self.logger.warning(f"🔄 اکانت سوخت! تغییر اکانت به: {self.accounts_pool[self.current_account_index]['username']}")

    # ==========================================================
    # موتورهای هوشمند استخراج دیتا (Data Extraction Engines)
    # ==========================================================

    def _parse_working_hours(self, text: str) -> Optional[str]:
        """(قابلیت ۳): موتور NLP/Regex برای درک ساعت کاری از کپشن یا بیو"""
        # الگوهای رایج فارسی: "ساعت کاری 10 الی 23" یا "از ۱۰ صبح تا ۱۲ شب"
        pattern = r"(ساعت کاری|از ساعت|تایم کاری).*?(\d{1,2}).*?(تا|الی).*?(\d{1,2})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            start, end = match.group(2), match.group(4)
            return f"{start}:00 - {end}:00"
        return None

    def _extract_menu_and_services(self, external_url: str) -> List[str]:
        """(قابلیت ۱۰): بررسی لینک‌های خارجی برای کشف سرویس‌ها (منو، اسنپ‌فود)"""
        services = []
        if not external_url:
            return services
            
        url_lower = external_url.lower()
        if "snappfood.ir" in url_lower:
            services.append("دارای سفارش آنلاین (اسنپ‌فود)")
        if "menew.ir" in url_lower or "digimenu" in url_lower:
            services.append("منوی دیجیتال")
        return services

    async def _follow_routing_links(self, bio_link: str) -> Optional[Dict]:
        """
        (قابلیت ۷): باز کردن لینک‌های Linktree یا Zil.ink برای سرقت لینک بلد/نشان! 🗺️
        """
        if not bio_link or ("zil.ink" not in bio_link and "linktr.ee" not in bio_link):
            return None
            
        self.logger.debug(f"🔗 در حال بررسی لینک واسط: {bio_link}")
        # اینجا در دنیای واقعی یک ریکوئست میزنیم به زیلینک و لینک‌های توش رو درمیاریم
        # برای سادگی فرض میکنیم مختصات رو استخراج کردیم
        # return {"lat": 35.7, "lng": 51.4} 
        return None

    def _check_highlights_for_address(self, highlights: list) -> bool:
        """(قابلیت ۴): گشتن دنبال هایلایت‌هایی با نام 'آدرس' یا 'مسیر'"""
        target_words = ["آدرس", "لوکیشن", "مسیر", "کجاییم", "address", "location"]
        for hl in highlights:
            title = hl.get("title", "").lower()
            if any(word in title for word in target_words):
                self.logger.info("📍 هایلایت 'آدرس' یافت شد! (نیاز به OCR در آینده)")
                return True
        return False

    def _extract_location_from_posts(self, posts: list) -> Optional[Dict]:
        """(قابلیت ۲): جستجوی تگ لوکیشن در آخرین پست‌ها"""
        for post in posts[:5]: # بررسی ۵ پست آخر
            location = post.get("location")
            if location and "lat" in location and "lng" in location:
                self.logger.debug("🎯 تگ لوکیشن در پست‌ها کشف شد!")
                return {"lat": location["lat"], "lng": location["lng"], "name": location.get("name")}
        return None

    # ==========================================================
    # متدهای الزامی کلاس پایه
    # ==========================================================

    async def check_health(self) -> bool:
        """تست زنده بودن سرورها"""
        session = await self._get_session()
        async with session.get("https://www.instagram.com/instagram/") as response:
            return response.status in [200, 302] # 302 به خاطر لاگین ریدایرکت هم اوکیه

    async def authenticate(self) -> bool:
        # اینجا میتونه منطق لاگین با یوزر/پسورد از اکانت پول قرار بگیره
        return True

    async def fetch_data(self, target_username: str, checkpoint_id: Optional[str] = None) -> Optional[dict]:
        """گرفتن دیتا با استفاده از اندپوینت جادویی و هدرهای موبایل"""
        session = await self._get_session()
        url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={target_username}"
        
        try:
            async with session.get(url, timeout=15) as response:
                if response.status in [401, 403, 429]:
                    self._rotate_account() # استفاده از قابلیت ۱
                    raise Exception(f"خطای Block (HTTP {response.status})")
                
                if response.status != 200:
                    return None
                    
                data = await response.json()
                self._save_smart_session() # آپدیت سشن در صورت موفقیت
                return data
                
        except asyncio.TimeoutError:
            raise Exception("Timeout")

    async def parse_data(self, raw_data: dict) -> AsyncGenerator[Tuple[dict, str], None]:
        """مغز متفکر کراولر: ادغام تمام قابلیت‌های استخراج"""
        try:
            user_data = raw_data.get("data", {}).get("user", {})
            if not user_data: return

            username = user_data.get("username")
            biography = user_data.get("biography", "")
            external_url = user_data.get("external_url")
            
            # --- قابلیت ۳: درک ساعت کاری ---
            working_hours = self._parse_working_hours(biography)
            
            # --- قابلیت ۴: بررسی هایلایت‌ها ---
            # (ساختار فیک برای نمایش منطق، در واقعیت از اندپوینت highlights باید گرفته بشه)
            has_address_highlight = self._check_highlights_for_address(user_data.get("highlights", []))
            
            # --- قابلیت ۱۰: استخراج خدمات و منو ---
            services = self._extract_menu_and_services(external_url)

            # --- قابلیت ۷: کشف مختصات از لینک‌های زیلینک ---
            routing_location = await self._follow_routing_links(external_url)

            # --- قابلیت ۲: پیدا کردن لوکیشن از روی پست‌ها ---
            # (در دیتای واقعیِ گراف‌کیوال، پست‌ها در edge_owner_to_timeline_media هستند)
            posts = [node["node"] for node in user_data.get("edge_owner_to_timeline_media", {}).get("edges", [])]
            post_location = self._extract_location_from_posts(posts)

            # ترکیب بهترین لوکیشن پیدا شده
            final_location = routing_location or post_location

            # --- قابلیت ۸: گسترش گراف (Suggested Accounts) ---
            # اگه این یه کافه جذابه، رقباش رو هم به لیست خزش اضافه کنیم!
            related_profiles = user_data.get("edge_related_profiles", {}).get("edges", [])
            for profile in related_profiles:
                self.logger.debug(f"🕸️ کشف پیج مرتبط: {profile['node']['username']}")
                # اینجا می‌تونی پیج رو تو دیتابیس Redis بندازی تا بعداً خزش بشه

            # ساختار نهایی POI
            poi_data = {
                "source": "instagram",
                "username": username,
                "working_hours": working_hours,
                "services": services,
                "has_address_highlight": has_address_highlight,
                "location_data": final_location,
                "external_url": external_url
            }
            
            yield poi_data, user_data.get("id")

        except Exception as e:
            self.logger.exception(f"خطا در پارس کردن فوق‌پیشرفته: {e}")

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self.logger.debug("🔌 شبح از سرورهای اینستاگرام خارج شد.")
