"""
src/core/exceptions.py
=============================================================================
سیستم فوق‌پیشرفته مدیریت خطاهای موتور جستجوی map-gap-filler.
مبتنی بر معماری پروژه (map-gap-filler.md) - لایه Core.

شامل:
- ۱۰ ارتقای استراتژیک (شمارنده متریک‌ها، دکوراتور Retry، لاگ رنگی، وب‌هوک، تجمیع‌کننده)
- دسته‌بندی سلسله‌مراتبی و ماژولار خطاهای خزشگرها، نقشه‌ها و داده‌ها
=============================================================================
"""

import sys
import time
import json
import random
import functools
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List, Callable, Type
from collections import Counter


# =============================================================================
# قابلیت ۶: سیستم آمارگیر و متریک خطاها (Error Counter & Metrics)
# =============================================================================
class ErrorMetricsTracker:
    """
    آمارگیر سراسری برای ثبت تعداد و انواع خطاهای رخ‌داده در طول اجرای برنامه.
    بدون نیاز به دیتابیس، در حافظه رم شمرده می‌شود تا در انتهای ران گزارش دهد.
    """
    _counter: Counter = Counter()

    @classmethod
    def record(cls, error_code: str) -> None:
        """افزایش یک واحدی شمارنده برای یک کد خطای مشخص."""
        cls._counter[error_code] += 1

    @classmethod
    def get_metrics(cls) -> Dict[str, int]:
        """دریافت دیکشنری کامل آمار خطاها."""
        return dict(cls._counter)

    @classmethod
    def reset(cls) -> None:
        """صفر کردن کنتورها برای ران بعدی."""
        cls._counter.clear()


# =============================================================================
# ۱. کلاس پایه‌ی تمام خطاهای پروژه (Base Core Exception)
# =============================================================================
class MapGapFillerError(Exception):
    """
    کلاس مادر برای تمام خطاهای درون این پروژه.
    هر استثنایی که در این سیستم تعریف می‌شود، از این کلاس ارث می‌برد.
    """
    def __init__(
        self,
        message: str,
        error_code: str = "GENERIC_ERROR",
        details: Optional[Dict[str, Any]] = None,
        severity: str = "WARNING"  # مقادیر ممکن: INFO, WARNING, ERROR, CRITICAL
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.severity = severity
        self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        # ثبت خودکار در سیستم متریک (پیشنهاد ۶)
        ErrorMetricsTracker.record(self.error_code)

        super().__init__(f"[{self.error_code}] {self.message}")

    def to_dict(self) -> Dict[str, Any]:
        """تبدیل جزئیات خطا به دیکشنری تمیز برای لاگر و JSON."""
        return {
            "timestamp": self.timestamp,
            "error_code": self.error_code,
            "severity": self.severity,
            "message": self.message,
            "details": self.details
        }

    # -------------------------------------------------------------------------
    # قابلیت ۳: خروجی لاگ رنگی ANSI برای ترمینال
    # -------------------------------------------------------------------------
    def to_colored_log(self) -> str:
        """
        خروجی رنگی جذاب برای نمایش در کنسول لینوکس، ویندوز و گیت‌هاب اکشنز.
        از کدهای استاندارد ANSI بدون نیاز به پکیج جانبی استفاده می‌کند.
        """
        colors = {
            "INFO": "\033[94m",      # آبی
            "WARNING": "\033[93m",   # زرد
            "ERROR": "\033[91m",     # قرمز روشن
            "CRITICAL": "\033[41m\033[97m",  # پس‌زمینه قرمز با نوشته سفید
            "RESET": "\033[0m"       # ریست رنگ
        }
        color = colors.get(self.severity, colors["WARNING"])
        reset = colors["RESET"]
        return f"{color}[{self.severity}] [{self.timestamp}] {self.error_code}: {self.message}{reset}"

    # -------------------------------------------------------------------------
    # قابلیت ۲: ارسال آلارم خطا به وب‌هوک بله / تلگرام
    # -------------------------------------------------------------------------
    def send_alert(self, webhook_url: Optional[str] = None) -> bool:
        """
        ارسال اخطار فوری خطا به وب‌هوک تلگرام، بله یا دیسکورد.
        اگر URL داده نشود، کاری انجام نمی‌دهد (امن در محیط لوکال).
        """
        if not webhook_url:
            return False

        payload = {
            "text": f"🚨 *هشدار نقشه یاسوج (Map-Gap-Filler)* 🚨\n"
                    f"⏰ *زمان:* `{self.timestamp}`\n"
                    f"⚠️ *نوع خطا:* `{self.error_code}`\n"
                    f"🛑 *سطح اهمیت:* `{self.severity}`\n"
                    f"📝 *پیام:* {self.message}\n"
                    f"🔍 *جزئیات:* `{json.dumps(self.details, ensure_ascii=False)}`"
        }

        try:
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status in [200, 204]
        except Exception:
            # نمی‌گذاریم شکست در ارسال آلرت، کل سیستم را متوقف کند!
            return False


# =============================================================================
# ۲. خطاهای لایه خزش و جمع‌آوری داده (Crawlers & Social Networks)
# =============================================================================
class CrawlerError(MapGapFillerError):
    """خطای عمومی در سطح خزنده‌ها (اینستاگرام، تلگرام، وب)."""
    def __init__(self, message: str, platform: str, details: Optional[Dict[str, Any]] = None, severity: str = "ERROR"):
        self.platform = platform
        details = details or {}
        details["platform"] = platform
        super().__init__(
            message=message,
            error_code=f"{platform.upper()}_CRAWLER_ERROR",
            details=details,
            severity=severity
        )


class RateLimitExceededError(CrawlerError):
    """محدودیت نرخ ریکوئست (مثلاً پاسخ ۴۲۹ از اینستاگرام یا نشان)."""
    def __init__(self, platform: str, retry_after: int = 60, message: Optional[str] = None):
        self.retry_after = retry_after
        msg = message or f"محدودیت درخواست در {platform}! نیاز به {retry_after} ثانیه استراحت."
        super().__init__(
            message=msg,
            platform=platform,
            details={"retry_after_seconds": retry_after},
            severity="WARNING"
        )


class AccountBlockedOrChallengedError(CrawlerError):
    """اکانت اسکرپر وارد بن، ساسپند یا چالش اعتبارسنجی شده است."""
    def __init__(self, platform: str, account_id: str, message: str = "اکانت اسکرپر مسدود یا با چالش روبرو شد!"):
        super().__init__(
            message=f"{message} (شناسه اکانت: {account_id})",
            platform=platform,
            details={"account_id": account_id},
            severity="CRITICAL"
        )


# قابلیت ۴: استثنای کپچا و چالش تصویری
class CaptchaRequiredError(CrawlerError):
    """
    وقتی تارگت (اینستاگرام/گوگل) کپچای تصویری یا پازل نشان می‌دهد.
    می‌توان مسیر ذخیره اسکرین‌شات یا حل‌کننده خودکار را در آن ذخیره کرد.
    """
    def __init__(self, platform: str, captcha_image_path: Optional[str] = None, captcha_type: str = "image_puzzle"):
        self.captcha_image_path = captcha_image_path
        self.captcha_type = captcha_type
        super().__init__(
            message=f"تارگت {platform} چالش کپچا ({captcha_type}) درخواست کرده است!",
            platform=platform,
            details={"captcha_type": captcha_type, "image_path": captcha_image_path},
            severity="CRITICAL"
        )


# قابلیت ۵: خطای سشن تلگرام
class TelegramSessionRevokedError(CrawlerError):
    """منقضی، ریست یا باطل شدن فایل سشن (session.) در Telethon/Pyrogram."""
    def __init__(self, session_name: str, message: str = "سشن تلگرام باطل شده و نیاز به لاگین مجدد دارد."):
        self.session_name = session_name
        super().__init__(
            message=f"{message} (سشن: {session_name})",
            platform="telegram",
            details={"session_name": session_name},
            severity="CRITICAL"
        )


# قابلیت ۷: استثنای محتوای فیک و نامربوط (اسپم)
class SpamOrIrrelevantContentError(CrawlerError):
    """
    برای زمان‌هایی که پست/پیج بررسی‌شده هیچ ربطی به کسب‌وکار یاسوج ندارد
    (مثلاً فروش ارز دیجیتال، شوخی‌های اینترنتی یا تبلیغات سراسری بدون مکان فیزیکی).
    """
    def __init__(self, post_url: str, detected_keywords: List[str], reason: str = "محتوای اسپم یا خارج از حوزه بیزینس یاسوج"):
        self.post_url = post_url
        self.detected_keywords = detected_keywords
        super().__init__(
            message=f"محتوا اسپم تشخیص داده شد: {post_url} (علت: {reason})",
            platform="content_filter",
            details={"url": post_url, "keywords": detected_keywords, "reason": reason},
            severity="INFO"
        )


# =============================================================================
# ۳. خطاهای شبکه، پروکسی و اینترنت (Network & Infrastructure)
# =============================================================================
class ProxyConnectionError(CrawlerError):
    """خطای قطعی، تایم‌اوت یا رد شدن اتصال از سمت سرور پروکسی."""
    def __init__(self, proxy_url: str, original_error: Optional[str] = None):
        # پاکسازی اطلاعات هویتی و پسورد از پروکسی برای لاگ امن
        safe_proxy = proxy_url.split("@")[-1] if "@" in proxy_url else proxy_url
        super().__init__(
            message=f"خطا در برقراری ارتباط با پروکسی: {safe_proxy}",
            platform="proxy_network",
            details={"proxy": safe_proxy, "reason": str(original_error)},
            severity="ERROR"
        )


# قابلیت ۸: استثنای قطعی سراسری اینترنت و مشکل DNS
class NetworkDnsResolutionError(MapGapFillerError):
    """
    وقتی نام دامنه (مثل api.neshan.org یا instagram.com) ریزالو نمی‌شود؛
    نشان‌دهنده قطعی اینترنت سرور یا اختلال شدید در DNS / فیلترینگ است.
    """
    def __init__(self, domain: str, original_error: Optional[str] = None):
        self.domain = domain
        super().__init__(
            message=f"خطای عدم دسترسی DNS به دامنه '{domain}'. ارتباط اینترنت یا سرور را بررسی کنید.",
            error_code="DNS_RESOLUTION_FAILURE",
            details={"domain": domain, "raw_error": str(original_error)},
            severity="CRITICAL"
        )


# =============================================================================
# ۴. خطاهای لایه ممیزی نقشه (Auditors - Neshan / OSM)
# =============================================================================
class AuditorError(MapGapFillerError):
    """خطای پایه در استعلام نقشه‌ها (نشان / اوپن‌استریت‌مپ)."""
    def __init__(self, service: str, message: str, status_code: Optional[int] = None):
        self.service = service
        self.status_code = status_code
        super().__init__(
            message=f"خطا در ممیزی نقشه {service}: {message}",
            error_code=f"{service.upper()}_AUDIT_ERROR",
            details={"service": service, "http_status": status_code},
            severity="ERROR"
        )


class NeshanQuotaExceededError(AuditorError):
    """هنگامی که سقف مجاز روزانه توکن نشان (Rate limit / Quota) به پایان می‌رسد."""
    def __init__(self, message: str = "سقف درخواست‌های مجاز روزانه کلید API نشان تکمیل شد!"):
        super().__init__(service="neshan", message=message, status_code=429)


class NeshanAuthError(AuditorError):
    """کلید API نشان نامعتبر است یا در تنظیمات .env جا افتاده است."""
    def __init__(self, message: str = "کلید NESHAN_API_KEY نامعتبر یا تعریف‌نشده است!"):
        super().__init__(service="neshan", message=message, status_code=401)


# =============================================================================
# ۵. خطاهای اعتبارسنجی داده و حجم خروجی (Validation & Payload)
# =============================================================================
class POIValidationError(MapGapFillerError):
    """خطای مربوط به عدم تایید ساختار کسب‌وکار توسط مدل Pydantic."""
    def __init__(self, field_name: str, invalid_value: Any, reason: str):
        self.field_name = field_name
        self.invalid_value = invalid_value
        super().__init__(
            message=f"فیلد '{field_name}' با مقدار '{invalid_value}' نامعتبر است: {reason}",
            error_code="POI_VALIDATION_ERROR",
            details={"field": field_name, "value": str(invalid_value), "reason": reason},
            severity="WARNING"
        )


class OutOfCityBoundsError(POIValidationError):
    """وقتی مختصات کشف‌شده، کیلومترها با محدوده Bounding Box یاسوج تضاد دارد!"""
    def __init__(self, lat: float, lon: float, city: str = "یاسوج"):
        super().__init__(
            field_name="coordinates",
            invalid_value=f"lat={lat}, lon={lon}",
            reason=f"نقطه استخراج‌شده بیرون از محدوده مجاز شهری {city} قرار دارد!"
        )


class DuplicatePOIError(MapGapFillerError):
    """کسب‌وکار کشف‌شده قبلاً با هش یکسان استخراج شده است."""
    def __init__(self, poi_id: str, title: str):
        super().__init__(
            message=f"کسب‌وکار تکراری نادیده گرفته شد: '{title}' (هش: {poi_id})",
            error_code="DUPLICATE_POI_SKIPPED",
            details={"poi_id": poi_id, "title": title},
            severity="INFO"
        )


# قابلیت ۹: خطای سقف حجم خروجی
class PayloadTooLargeError(MapGapFillerError):
    """
    وقتی خروجی تجمیعی GeoJSON یا لاگ‌ها از حد نصاب تعیین‌شده
    (مثلاً محدودیت حجم فایل گیت‌هاب یا حافظه رم) فراتر برود.
    """
    def __init__(self, current_size_mb: float, max_allowed_mb: float):
        self.current_size_mb = current_size_mb
        self.max_allowed_mb = max_allowed_mb
        super().__init__(
            message=f"حجم بسته دیتای خروجی ({current_size_mb:.2f} MB) از سقف مجاز ({max_allowed_mb:.2f} MB) فراتر رفت!",
            error_code="PAYLOAD_TOO_LARGE",
            details={"current_mb": current_size_mb, "max_mb": max_allowed_mb},
            severity="ERROR"
        )


# =============================================================================
# قابلیت ۱: دکوراتور تلاش مجدد خودکار (@retry_on_exception)
# =============================================================================
def retry_on_exception(
    max_retries: int = 3,
    base_delay: float = 2.0,
    backoff_factor: float = 2.0,
    allowed_exceptions: tuple = (ProxyConnectionError, RateLimitExceededError, NetworkDnsResolutionError)
):
    """
    دکوراتور پایتونی فوق‌العاده کاربردی برای توابع حساس شبکه.
    اگر تابع با خطاهای تعریف‌شده در allowed_exceptions مواجه شود،
    به صورت Exponential Backoff با چاشنی تاخیر تصادفی (Jitter) چند بار تلاش مجدد می‌کند.
    
    مثال استفاده:
    @retry_on_exception(max_retries=3, base_delay=3.0)
    def fetch_instagram_post(url):
        ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_retries:
                try:
                    return func(*args, **kwargs)
                except allowed_exceptions as exc:
                    attempts += 1
                    if attempts >= max_retries:
                        # اگر تمام شانس‌ها سوخت، خطا بالا بیاید تا تصمیم نهایی گرفته شود
                        raise exc
                    
                    # محاسبه خواب نمایی + جیتر تصادفی برای گمراه کردن الگوریتم‌های آنتی‌ربات
                    sleep_time = (base_delay * (backoff_factor ** (attempts - 1))) + random.uniform(0.5, 1.5)
                    
                    # اگر خطا از نوع ریت‌لیمیت بود و زمان دقیق پیشنهاد داده بود، آن را ملاک قرار می‌دهیم
                    if isinstance(exc, RateLimitExceededError) and exc.retry_after > 0:
                        sleep_time = exc.retry_after
                        
                    print(
                        f"\033[93m[تلاش مجدد {attempts}/{max_retries}]\033[0m "
                        f"خطای '{exc.__class__.__name__}' رخ داد. خواب به مدت {sleep_time:.1f} ثانیه..."
                    )
                    time.sleep(sleep_time)
        return wrapper
    return decorator


# =============================================================================
# قابلیت ۱۰: کلاس تجمیع‌کننده خطاهای پایپ‌لاین (ExceptionGroupCollector)
# =============================================================================
class ExceptionGroupCollector:
    """
    سیستم جمع‌آوری و خلاصه‌سازی خطاها در انتهای پایپ‌لاین روزانه.
    خطاهای خرد را ضبط می‌کند تا در پایان، یک گزارش Markdown شکیل و مرتب تولید کند.
    """
    def __init__(self):
        self._errors: List[MapGapFillerError] = []

    def collect(self, error: MapGapFillerError) -> None:
        """اضافه کردن یک خطا به سبد خطاهای اجرای فعلی."""
        self._errors.append(error)

    @property
    def total_count(self) -> int:
        """تعداد کل خطاهای ضبط‌شده."""
        return len(self._errors)

    def generate_markdown_report(self, city_name: str = "یاسوج") -> str:
        """تولید گزارش مانیتورینگ خطاهای روزانه به زبان مارک‌داون."""
        metrics = ErrorMetricsTracker.get_metrics()
        
        md_lines = [
            f"# 📊 گزارش وضعیت خطاهای پایپ‌لاین ({city_name})",
            f"**زمان تولید:** `{time.strftime('%Y-%m-%d %H:%M:%S')}`  ",
            f"**تعداد کل خطاهای رهگیری‌شده:** `{self.total_count}`\n",
            "## 📈 آمار تفکیکی کد خطاها",
            "| کد خطا (Error Code) | تعداد تکرار |",
            "| :--- | :--- |"
        ]

        if not metrics:
            md_lines.append("| *بدون خطا (اجرای بی‌نقص!)* | 0 |")
        else:
            for code, count in sorted(metrics.items(), key=lambda x: x[1], reverse=True):
                md_lines.append(f"| `{code}` | {count} |")

        md_lines.append("\n## 🔍 جزئیات آخرین خطاهای بحرانی")
        critical_errors = [e for e in self._errors if getattr(e, "severity", "") in ["ERROR", "CRITICAL"]][-10:]
        
        if not critical_errors:
            md_lines.append("> 🟢 هیچ خطای بحرانی یا فلج‌کننده‌ای در این اجرا رخ نداده است.")
        else:
            for err in critical_errors:
                md_lines.append(f"- **[{err.timestamp}] `{err.error_code}`:** {err.message}")

        return "\n".join(md_lines)
