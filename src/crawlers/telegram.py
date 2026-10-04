"""
src/crawlers/telegram.py
=============================================================================
خزنده تلگرام (Telegram Web-Preview Omni-Scraper) 🥷✈️
ارث‌بری شده از BaseCrawler ناهمگام.

وظیفه:
استخراج اطلاعات کانال‌ها و گروه‌های عمومی تلگرام از طریق نسخه وب (بدون نیاز به لاگین).
مجهز به ۶ موتور استخراج پیشرفته (تاریخچه، قیمت، فوروارد، نقشه‌یاب، کراس‌پلتفرم، بسترسازی OCR).
=============================================================================
"""

import re
import asyncio
import aiohttp
from typing import AsyncGenerator, Any, Optional, Tuple, List

# وارد کردن کلاس پایه
from src.crawlers.base import BaseCrawler

# برای قابلیت OCR (در صورت نیاز به فعال‌سازی، باید tesseract نصب باشد)
try:
    import pytesseract
    from PIL import Image
    import io
    OCR_ENABLED = True
except ImportError:
    OCR_ENABLED = False


class TelegramCrawler(BaseCrawler):
    """
    جاسوس موشک‌های کاغذی، ارتقایافته به نینجای وب! 🥷🛩️
    استخراج دیتای کانال‌های تلگرامی از طریق t.me/s/ با بالاترین توان پردازش متن.
    """

    def __init__(self, proxies: list = None):
        super().__init__(crawler_name="tele_ninja", proxies=proxies, delay_range=(2.0, 5.0))
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """ساخت سشن برای ارتباط با تلگرام با ماسکِ یک مرورگر واقعی 🎭"""
        if self._session is None or self._session.closed:
            headers = self._get_random_headers()
            headers.update({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
                "Cache-Control": "no-cache"
            })
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    async def check_health(self) -> bool:
        """تست زنده بودن سرورهای وب تلگرام 🩺"""
        try:
            session = GAPGPTMASKTOKEN82hce0cje3xX0X self._get_session()
            proxy = self.proxies[self.current_proxy_index] if self.proxies else None
            
            self.logger.debug("🩺 در حال بررسی ارتباط با t.me ...")
            async with session.get("https://t.me/telegram", proxy=proxy, timeout=10) as response:
                if response.status == 200:
                    self.logger.info("✅ تلگرام در دسترس است (بدون نیاز به MTProto).")
                    return True
                return False
        except Exception as e:
            self.logger.error(f"💀 قطعی ارتباط با تلگرام: {e}")
            return False

    async def authenticate(self) -> bool:
        self.logger.info("🔓 خزش تلگرام در حالت عمومی (Public Web Preview) آغاز شد.")
        return True

    async def fetch_data(self, target_username: str, checkpoint_id: Optional[str] = None) -> Optional[str]:
        """
        دریافت سورس HTML کانال تلگرام. 🤫
        """
        session = GAPGPTMASKTOKEN82hce0cje3xX1X self._get_session()
        proxy = self.proxies[self.current_proxy_index] if self.proxies else None
        url = f"https://t.me/s/{target_username}"
        
        try:
            async with session.get(url, proxy=proxy, timeout=15) as response:
                if response.status == 404:
                    self.logger.warning(f"❌ کانال {target_username} پیدا نشد یا پرایوت است.")
                    return None
                    
                if response.status == 200:
                    html_data = GAPGPTMASKTOKEN82hce0cje3xX2X response.text()
                    return html_data
                else:
                    self.logger.warning(f"⚠️ خطای HTTP {response.status} از سرور.")
                    return None
                    
        except asyncio.TimeoutError:
            self.logger.error("⏳ تایم‌اوت در دریافت اطلاعات!")
            raise Exception("Timeout")

    async def _download_and_ocr(self, image_url: str, session: aiohttp.ClientSession, proxy: str) -> str:
        """قابلیت ۱۰ (ارتقا یافته): استخراج متن از بنرهای عکس دار 🖼️"""
        if not OCR_ENABLED:
            return ""
        try:
            async with session.get(image_url, proxy=proxy, timeout=10) as resp:
                if resp.status == 200:
                    image_data = await resp.read()
                    img = Image.open(io.BytesIO(image_data))
                    text = pytesseract.image_to_string(img, lang='fas+eng')
                    return text
        except Exception as e:
            self.logger.debug(f"خطا در پردازش تصویر OCR: {e}")
        return ""

    async def parse_data(self, html_data: str) -> AsyncGenerator[Tuple[dict, str], None]:
        """
        کالبدشکافی HTML با قدرت ۶ قابلیت ترکیبی! 🕵️‍♂️🔬
        """
        try:
            # ۱. استخراج اطلاعات پایه (نام، بیو، آیدی)
            title = (re.search(r'<meta property="og:title" content="(.*?)">', html_data) or re.search('', '')).group(1) or "نامشخص"
            description = (re.search(r'<meta property="og:description" content="(.*?)">', html_data) or re.search('', '')).group(1) or ""
            channel_id = (re.search(r't\.me/i/userpic/.*?/(.*?)\.jpg', html_data) or re.search('', '')).group(1) or "unknown_id"

            # ۲. تحلیل‌گر تاریخچه پیام‌ها (History Scraper) 📜
            # استخراج تمام پیام‌های رندر شده در پیش‌نمایش وب
            messages_raw = re.findall(r'<div class="tgme_widget_message_text.*?>(.*?)</div>', html_data, re.DOTALL)
            # پاکسازی تگ‌های HTML از پیام‌ها
            clean_messages = [re.sub(r'<[^>]+>', ' ', msg).strip() for msg in messages_raw]
            full_text = description + " ".join(clean_messages)

            # ۳. استخراج شماره تماس (شبیه‌ساز VCard روی متن) 📇
            phone_pattern = r"(09\d{9}|0[1-9]{2}\d{8}|\+989\d{9})"
            phones_found = list(set(re.findall(phone_pattern, full_text.replace(" ", "").replace("-", ""))))

            # ۴. مسیریاب پلتفرم‌های متقاطع (Cross-Platform) 🤝
            insta_pattern = r'instagram\.com/([a-zA-Z0-9_.]+)'
            insta_links = list(set(re.findall(insta_pattern, full_text)))

            # ۵. شکارچی پیام‌های Location (نسخه مبتنی بر لینک مسیریاب‌ها) 📍
            map_pattern = r'(https?://(?:goo\.gl/maps|maps\.app\.goo\.gl|neshan\.org/maps|balad\.ir)[^\s"\'<]+)'
            map_links = list(set(re.findall(map_pattern, html_data)))

            # ۶. هوش مصنوعی استخراج قیمت 💰
            price_pattern = r'(\d{1,3}(?:,\d{3})+|\d{4,})\s*(هزار\s*تومان|تومان|Toman|تومن)'
            prices_found = list(set([f"{p[0]} {p[1]}" for p in re.findall(price_pattern, full_text)]))

            # ۷. ردیاب پیام‌های فورواردی (Forward Tracer) 🔗
            forward_pattern = r'<a class="tgme_widget_message_forwarded_from_name" href="https://t\.me/([^"]+)"'
            forwards = list(set(re.findall(forward_pattern, html_data)))

            # ۸. استخراج بنرهای تبلیغاتی برای OCR (اختیاری) 🖼️
            # پیدا کردن لینک تصاویر بک‌گراند پیام‌ها
            img_pattern = r"background-image:url\('([^']+)'\)"
            images_found = re.findall(img_pattern, html_data)
            ocr_texts = []
            if OCR_ENABLED and images_found:
                session = GAPGPTMASKTOKEN82hce0cje3xX3X self._get_session()
                proxy = self.proxies[self.current_proxy_index] if self.proxies else None
                # فقط اولین عکس رو برای تست OCR می‌خونیم تا منابع سرور درگیر نشه
                ocr_text = await self._download_and_ocr(images_found[0], session, proxy)
                if ocr_text:
                    ocr_texts.append(ocr_text)

            # ساخت دیکشنری نهایی دیتای بیزینس
            poi_data = {
                "source": "telegram_web",
                "source_id": channel_id,
                "name": title,
                "description": description,
                "extracted_phones": phones_found,
                "cross_platforms": {"instagram": insta_links},
                "map_links": map_links,
                "pricing_data": prices_found[:5], # ۵ قیمت اول
                "forwarded_sources": forwards,
                "ocr_findings": ocr_texts,
                "admin_mentions": list(set(re.findall(r"@([a-zA-Z0-9_]{5,32})", full_text))),
            }

            self.logger.debug(f"🎯 اطلاعات کانال شکار شد: {title} | شماره‌ها: {len(phones_found)} | لوکیشن: {len(map_links)}")
            
            yield poi_data, channel_id

        except Exception as e:
            self.logger.error(f"❌ خطا در پارس کردن دیتای تلگرام: {e}")

    async def close(self):
        """بستن کانکشن‌ها با احترام 🔌"""
        if self._session and not self._session.closed:
            GAPGPTMASKTOKEN82hce0cje3xX4X self._session.close()
            self.logger.debug("🔌 سشن تلگرام بسته شد. شب بخیر!")
