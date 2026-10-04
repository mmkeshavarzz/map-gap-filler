"""
src/crawlers/base.py
=============================================================================
ربات زره‌پوش و انتزاعی (Supercharged Async Base Crawler) برای پروژه map-gap-filler.

این کلاس مجهز به ۱۰ قابلیت Enterprise است:
۱. Circuit Breaker (جلوگیری از بن شدن در صورت خطای مکرر)
۲. User-Agent Rotation (جلوگیری از شناسایی)
۳. Checkpoint (ذخیره وضعیت خزش در فایل JSON)
۴. Shadow Ban Detection (تشخیص انسداد خاموش)
۵. Async Processing (استفاده از asyncio برای خزش موازی و فوق‌سریع)
۶. Proxy Rotation (چرخش خودکار پروکسی در صورت قطعی)
۷. Jitter & Exponential Backoff (تاخیر هوشمند شبه‌انسانی)
۸. Deduplication (فیلتر تکراری‌ها با هش)
۹. Event Hooks (قلاب‌های رویداد برای اتصال به دیتابیس یا تلگرام)
۱۰. Health Ping (تست سلامت سرور قبل از شروع خزش)
=============================================================================
"""

import os
import json
import random
import asyncio
import hashlib
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Any, Optional, Dict, List, Set
from pathlib import Path

from src.core.logger import get_trace_logger

# مسیر ذخیره وضعیت خزش (Checkpoints)
CHECKPOINT_DIR = Path("data/checkpoints")
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

class BaseCrawler(ABC):
    """پدر معنوی تمام کراولرهای ناهمگام (Async) پروژه! 🕷️⚡"""

    # لیست مرورگرهای مختلف برای گول زدن فایروال (قابلیت ۲)
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.76"
    ]

    def __init__(
        self, 
        crawler_name: str, 
        proxies: Optional[List[str]] = None, 
        delay_range: tuple = (2.0, 5.0)
    ):
        self.crawler_name = crawler_name
        self.proxies = proxies or []
        self.current_proxy_index = 0
        self.delay_range = delay_range
        
        self.logger = get_trace_logger(crawler_name)
        
        # متغیرهای مانیتورینگ و دفاعی
        self.consecutive_errors = 0      # برای Circuit Breaker (قابلیت ۱)
        self.empty_pages_count = 0       # برای Shadow Ban (قابلیت ۴)
        self.seen_hashes: Set[str] = set() # برای Deduplication (قابلیت ۸)
        
        self.stats = {
            "total_extracted": 0,
            "total_failed": 0,
            "duplicates_skipped": 0,
        }

    # ==========================================================
    # ابزارهای دفاعی و هوشمند (Defense & Intelligence)
    # ==========================================================

    def _get_random_headers(self) -> Dict[str, str]:
        """تولید هدر با مرورگر تصادفی (قابلیت ۲: User-Agent Rotation)"""
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept-Language": "en-US,en;q=0.9,fa;q=0.8",
            "DNT": "1" # Do Not Track! 😎
        }

    def _rotate_proxy(self):
        """تغییر پروکسی فعلی به بعدی در صورت مسدودی (قابلیت ۶: Proxy Rotation)"""
        if not self.proxies:
            self.logger.warning("پروکسی جایگزینی وجود ندارد! بدون پروکسی ادامه می‌دهیم.")
            return None
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        new_proxy = self.proxies[self.current_proxy_index]
        self.logger.warning(f"🔄 چرخش پروکسی انجام شد. پروکسی جدید: {new_proxy}")
        return new_proxy

    async def _smart_sleep(self, attempt: int = 1):
        """
        توقف هوشمند با افزودن جیتر و افزایش تصاعدی زمان در صورت خطا
        (قابلیت ۷: Jitter & Exponential Backoff)
        """
        base_delay = random.uniform(self.delay_range[0], self.delay_range[1])
        # فرمول: زمان پایه * (۲ به توان تلاش) + یک نوسان تصادفی (Jitter)
        backoff_multiplier = 2 ** (attempt - 1)
        jitter = random.uniform(0.1, 1.5)
        total_sleep = (base_delay * backoff_multiplier) + jitter
        
        # سقف تاخیر ۶۰ ثانیه است که رباتمون پیر نشه!
        total_sleep = min(total_sleep, 60.0)
        
        self.logger.debug(f"💤 تاخیر تاکتیکی: {total_sleep:.2f} ثانیه (تلاش: {attempt})")
        await asyncio.sleep(total_sleep)

    def _is_duplicate(self, poi_data: Any) -> bool:
        """بررسی تکراری بودن داده با تولید هش (قابلیت ۸: Deduplication)"""
        # فرض بر این است که poi_data قابل تبدیل به رشته است
        data_str = str(poi_data).encode('utf-8')
        poi_hash = hashlib.md5(data_str).hexdigest()
        
        if poi_hash in self.seen_hashes:
            self.stats["duplicates_skipped"] += 1
            return True
            
        self.seen_hashes.add(poi_hash)
        return False

    # ==========================================================
    # مدیریت وضعیت و ذخیره‌سازی (State Management)
    # ==========================================================

    def _get_checkpoint_path(self, target: str) -> Path:
        clean_target = "".join(c if c.isalnum() else "_" for c in str(target))
        return CHECKPOINT_DIR / f"{self.crawler_name}_{clean_target}.json"

    def save_checkpoint(self, target: str, last_processed_id: str):
        """ذخیره شناسه آخرین آیتم بررسی شده (قابلیت ۳: Checkpoint)"""
        path = self._get_checkpoint_path(target)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"last_id": last_processed_id, "time": str(asyncio.get_event_loop().time())}, f)
            self.logger.debug(f"💾 چک‌پوینت ذخیره شد: {last_processed_id}")
        except Exception as e:
            self.logger.error(f"خطا در ذخیره چک‌پوینت: {e}")

    def load_checkpoint(self, target: str) -> Optional[str]:
        """بازیابی آخرین وضعیت از فایل (ادامه کار بعد از قطعی)"""
        path = self._get_checkpoint_path(target)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.logger.info(f"🔄 بازگشت به آخرین چک‌پوینت: {data.get('last_id')}")
                    return data.get("last_id")
            except Exception:
                pass
        return None

    # ==========================================================
    # قلاب‌های رویدادمحور (قابلیت ۹: Event Hooks)
    # ==========================================================

    async def on_poi_extracted(self, poi: Any):
        """این متد را می‌توانید در کلاس فرزند اورراید کنید تا موقع یافتن POI پیام تلگرامی بدهد."""
        pass

    async def on_captcha_detected(self):
        """اقدامات هنگام مواجهه با کپچا (مثل ارسال به سرویس 2Captcha)"""
        self.logger.critical("🚨 کپچا تشخیص داده شد! خزش متوقف می‌شود.")

    # ==========================================================
    # متدهای انتزاعی که باید در کلاس فرزند (مثل اینستاگرام) نوشته شوند
    # ==========================================================

    @abstractmethod
    async def check_health(self) -> bool:
        """(قابلیت ۱۰: Health Ping) بررسی زنده بودن سایت هدف قبل از شروع"""
        pass

    @abstractmethod
    async def authenticate(self) -> bool:
        """لاگین به سایت یا رد کردن پاپ‌آپ‌ها"""
        pass

    @abstractmethod
    async def fetch_data(self, target: Any, checkpoint_id: Optional[str] = None) -> Any:
        """دریافت دیتای خام با پشتیبانی از async (مثل گرفتن HTML با aiohttp)"""
        pass

    @abstractmethod
    async def parse_data(self, raw_data: Any) -> AsyncGenerator[Any, None]:
        """پارس کردن دیتا و صدور آیتم‌ها با دستور async for"""
        # به دلیل ماهیت اینترفیس، اینجا فقط یک پیاده‌سازی خالی می‌گذاریم
        yield None

    # ==========================================================
    # موتور اصلی اجرای پایپ‌لاین (The Core Engine)
    # ==========================================================

    async def run_pipeline(self, target: Any) -> AsyncGenerator[Any, None]:
        """
        مدیریت کل چرخه خزش با پشتیبانی از تمام ۱۰ ویژگی Enterprise.
        """
        self.logger.info(f"🚀 آغاز عملیات خزش ناهمگام برای هدف: {target}")

        # قابلیت ۱۰: پینگ سلامت
        if not await self.check_health():
            self.logger.error("💀 سایت هدف در دسترس نیست! (Health Check Failed)")
            return

        # لاگین
        if not await self.authenticate():
            self.logger.error("❌ احراز هویت با شکست مواجه شد.")
            return

        # بارگذاری چک‌پوینت قبلی (قابلیت ۳)
        last_id = self.load_checkpoint(target)
        attempt = 1

        while True:
            try:
                # بررسی قابلیت ۱: Circuit Breaker
                if self.consecutive_errors >= 3:
                    self.logger.critical("⛔ قطع‌کننده مدار (Circuit Breaker) فعال شد! توقف کامل برای جلوگیری از بن شدن.")
                    break

                # قابلیت ۷: تاخیر با Backoff
                await self._smart_sleep(attempt)

                self.logger.debug(f"📥 دریافت دیتا... (تلاش {attempt})")
                raw_data = await self.fetch_data(target, checkpoint_id=last_id)

                if not raw_data:
                    self.empty_pages_count += 1
                    # قابلیت ۴: Shadow Ban Detection
                    if self.empty_pages_count >= 3:
                        self.logger.error("👻 احتمال Shadow Ban! صفحات خالی متوالی دریافت شد.")
                        self._rotate_proxy() # قابلیت ۶
                        self.empty_pages_count = 0
                    continue

                # ریست کردن شمارنده‌های خطا بعد از یک موفقیت
                self.consecutive_errors = 0
                self.empty_pages_count = 0
                attempt = 1
                items_found = False

                # قابلیت ۵: پردازش Async
                async for poi, poi_id in self.parse_data(raw_data):
                    items_found = True
                    
                    # قابلیت ۸: حذف تکراری‌ها
                    if self._is_duplicate(poi):
                        continue

                    self.stats["total_extracted"] += 1
                    
                    # قابلیت ۹: فراخوانی هوک‌ها
                    await self.on_poi_extracted(poi)
                    
                    # قابلیت ۳: بروزرسانی چک‌پوینت
                    last_id = poi_id
                    self.save_checkpoint(target, str(last_id))

                    yield poi
                
                # شرط خروج: اگر دیگر دیتایی برای پارس نبود، حلقه پایان یابد
                if not items_found:
                    self.logger.info("✅ تمام صفحات موجود اسکرپ شد.")
                    break

            except Exception as e:
                self.consecutive_errors += 1
                self.stats["total_failed"] += 1
                attempt += 1
                
                if "captcha" in str(e).lower():
                    await self.on_captcha_detected()
                    break
                    
                self.logger.error(f"💥 خطا در چرخه خزش: {str(e)} | قطعی‌های متوالی: {self.consecutive_errors}/3")
                self._rotate_proxy() # در صورت بروز ارور نت، پروکسی رو عوض می‌کنیم

        # چاپ گزارش نهایی
        self.logger.info(
            f"🏁 پایان عملیات | "
            f"استخراج شده: {self.stats['total_extracted']} | "
            f"تکراری‌های حذف شده: {self.stats['duplicates_skipped']} | "
            f"خطاها: {self.stats['total_failed']}"
        )
