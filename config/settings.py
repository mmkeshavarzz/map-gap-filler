import os
from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# اینجا داریم مسیر روت (اصلی) پروژه رو پیدا می‌کنیم. 
# با این کار دیگه نیازی نیست آدرس‌دهی دستی (مثل "C:/Users/...") بدیم!
# هرجای سرور یا سیستم عامل که پروژه رو بذاری، خودش آدرسو می‌فهمه. 🧠
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    """
    🎛️ کلاس مرکزی تنظیمات پروژه MapGapEngine.
    تمام متغیرها از فایل .env در ریشه پروژه خوانده می‌شوند.
    """
    
    # --- 🌍 تنظیمات عمومی ---
    ENVIRONMENT: str = Field(default="development", description="وضعیت محیط: development یا production")
    DEBUG: bool = Field(default=True, description="فعال بودن حالت دیباگ")

    # --- 🔑 تنظیمات تلگرام (Telethon) ---
    # این دو مورد اجباری (Required) هستند. علامت سه نقطه (...) یعنی نمیشه خالیش گذاشت!
    TELEGRAM_API_ID: int = Field(..., description="Telegram API ID (Get from my.telegram.org)")
    # از SecretStr استفاده کردیم تا اگه یه وقت لاگ گرفتیم، پسورد رو تو لاگ چاپ نکنه و سانسورش کنه (***) 🕵️‍♂️
    TELEGRAM_API_HASH: SecretStr = Field(..., description="Telegram API Hash")

    # --- 🗺️ تنظیمات API نقشه‌ها ---
    NESHAN_API_KEY: SecretStr | None = Field(default=None, description="کلید API نشان (برای استعلام و ژئوکدینگ)")
    GOOGLE_MAPS_API_KEY: SecretStr | None = Field(default=None, description="کلید API گوگل (اختیاری برای فازهای بعدی)")

    # --- 📁 مسیرها (Paths) ---
    # تعریف مسیرهای استاندارد بر اساس BASE_DIR
    DATA_DIR: Path = Field(default=BASE_DIR / "data", description="پوشه دیتابیس و داده‌های خام")
    EXPORTS_DIR: Path = Field(default=BASE_DIR / "exports", description="پوشه خروجی نهایی شهرها")
    CITIES_CONFIG_PATH: Path = Field(default=BASE_DIR / "config" / "cities.json", description="فایل تنظیمات شهرها")
    DB_PATH: Path = Field(default=BASE_DIR / "data" / "global_history.db", description="مسیر دیتابیس ضد-تکرار")

    # --- ⏱️ تنظیمات خزنده‌ها و محدودیت‌ها (Rate Limits) ---
    REQUEST_TIMEOUT: int = Field(default=10, description="حداکثر زمان انتظار برای پاسخگویی سایت‌ها (ثانیه)")
    MAX_RETRIES: int = Field(default=3, description="تعداد دفعات تلاش مجدد در صورت قطعی اینترنت")
    CRAWL_INTERVAL_HOURS: int = Field(default=6, description="فاصله زمانی بین هر بار اجرای کامل خزنده")

    # کانفیگِ خود Pydantic برای نحوه خوندن فایل .env
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore" # اگه تو فایل .env متغیری بود که اینجا تعریف نکردیم، گیر نده و ازش بگذر
    )

# در نهایت یک نمونه (Instance) از کلاس می‌سازیم.
# بقیه فایل‌های پروژه فقط باید همین متغیر `settings` رو ایمپورت کنن.
settings = Settings()

# ------------- راهنمای استفاده برای سایر فایل‌ها -------------
# from config.settings import settings
# print(settings.TELEGRAM_API_ID)
# print(settings.DB_PATH)
