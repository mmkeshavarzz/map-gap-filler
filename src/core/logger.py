"""
src/core/logger.py
=============================================================================
موتور پیشرفته ثبت وقایع و مانیتورینگ سیستم (Enterprise Logging & Telemetry Engine)
برای پروژه map-gap-filler (طراحی شده بر اساس سند معماری map-gap-filler.md - لایه Core).

این ماژول مجهز به تمام ۱۰ قابلیت پیشرفته است:
۱. تبدیل خودکار تاریخ به جلالی (شمسی) بدون نیاز به پکیج‌های حجیم
۲. ماسک‌سازی و سانسور خودکار داده‌های محرمانه (Sanitizer: API Key, Passwords, Phones)
۳. دکوراتور اندازه‌گیری دقیق زمان اجرای توابع و مصرف منابع (@log_execution_time)
۴. سینک اختصاصی ارسال هشدارهای فاجعه‌بار (CRITICAL/ERROR) به وب‌هوک (بله / دیسکورد / تلگرام)
۵. ردیاب همبستگی (Trace-ID / Correlation ID) برای پیگیری سرنوشت هر کسب‌وکار در پایپ‌لاین
۶. ثبت وضعیت مصرف حافظه RAM سیستم در هر پیام دیباگ
۷. مکانیزم دامپ باینری و HTML (Dump Logger) برای ذخیره صفحات خطا و کپچا در دیسک
۸. بررسی هوشمند فضای ذخیره‌سازی دیسک و چرخش امن (Disk Safety Guard)
۹. سازگاری بومی با دستورات خطای گیت‌هاب اکشنز (GitHub Actions Workflow Commands ::error::)
۱۰. هماهنگی با نوارهای پیشرفت TQDM برای جلوگیری از به‌هم‌ریختگی ترمینال
=============================================================================
"""

import os
import sys
import re
import json
import time
import shutil
import uuid
import datetime
import functools
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Callable
from loguru import logger

# تلاش برای استخراج تنظیمات سیستم؛ در صورت عدم وجود، مقادیر پیش‌فرض جایگزین می‌شود
try:
    from config.settings import settings
    LOG_LEVEL = "DEBUG" if getattr(settings, "DEBUG", False) else "INFO"
    BASE_DIR = getattr(settings, "BASE_DIR", Path(__file__).resolve().parent.parent.parent)
    WEBHOOK_ALERT_URL = getattr(settings, "WEBHOOK_URL", None)
except Exception:
    LOG_LEVEL = "INFO"
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    WEBHOOK_ALERT_URL = None

LOGS_DIR = BASE_DIR / "logs"
DUMPS_DIR = LOGS_DIR / "dumps"

# تضمین ایجاد پوشه‌های ضروری
LOGS_DIR.mkdir(parents=True, exist_ok=True)
DUMPS_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# قابلیت ۱: مبدل اختصاصی و سبک تاریخ میلادی به هجری شمسی (جلالی)
# =============================================================================
def gregorian_to_jalali(gy: int, gm: int, gd: int):
    """
    الگوریتم دقیق ریاضی برای تبدیل تاریخ میلادی به جلالی بدون نیاز به کتابخانه بیرونی.
    """
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy if gm > 2 else gy - 1
    days = (365 * gy) + ((gy2 + 4) // 4) - ((gy2 + 100) // 100) + ((gy2 + 400) // 400) - 80 + gd + g_d_m[gm - 1]
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd


def get_current_jalali_str() -> str:
    """دریافت رشته تاریخ و ساعت شمسی جاری با فرمت YYYY/MM/DD HH:MM:SS."""
    now = datetime.datetime.now()
    jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
    return f"{jy:04d}/{jm:02d}/{jd:02d} {now.strftime('%H:%M:%S')}"


# =============================================================================
# قابلیت ۲: ماسک‌سازی و سانسور خودکار داده‌های حساس (Sanitizer)
# =============================================================================
SENSITIVE_PATTERNS = [
    # ماسک کردن کلیدهای توکن و پسورد: token=xyz -> token=***
    (re.compile(r'(?i)(api[_-]?key|token|secret|password|passwd|auth)=([^\s&,]+)'), r'\1=********'),
    # ماسک کردن ساختار پروکسی یوزردار: http://user:pass@host:port -> http://user:***@host:port
    (re.compile(r'(://[^:]+:)([^@]+)(@)'), r'\1********\3'),
    # ماسک کردن شماره تلفن همراه ایران: 09171234567 -> 0917***4567
    (re.compile(r'(09\d{2})\d{4}(\d{3})'), r'\1****\2'),
]

def sanitize_message(text: str) -> str:
    """پایش و سانسور امنیتی تمام رشته‌های حساس قبل از چاپ یا ذخیره در فایل."""
    sanitized = text
    for pattern, repl in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(repl, sanitized)
    return sanitized


# =============================================================================
# قابلیت ۶: بررسی سبک و سریع میزان مصرف RAM
# =============================================================================
def get_memory_usage_mb() -> float:
    """استخراج میزان مصرف رم پردازه فعلی (به مگابایت) بدون سربار سنگین."""
    try:
        import resource
        # در سیستم‌های بر پایه یونیکس / لینوکس / مک
        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return usage / 1024.0 if sys.platform != 'darwin' else usage / (1024.0 * 1024.0)
    except Exception:
        # در صورت اجرا روی ویندوز بدون ماژول resource
        return 0.0


# =============================================================================
# قابلیت ۸: محافظ فضای خالی دیسک (Disk Space Guard)
# =============================================================================
def check_disk_space_healthy(min_free_mb: int = 100) -> bool:
    """بررسی اینکه آیا حداقل ۱۰۰ مگابایت فضای خالی برای نوشتن لاگ‌ها وجود دارد؟"""
    try:
        total, used, free = shutil.disk_usage(LOGS_DIR)
        return (free / (1024 * 1024)) > min_free_mb
    except Exception:
        return True


# =============================================================================
# قابلیت ۴: ارسال لاگ‌های بحرانی به وب‌هوک آلارم
# =============================================================================
def _send_webhook_alert(record):
    """ارسال اطلاعات خطاهای CRITICAL و ERROR به وب‌هوک تنظیم‌شده."""
    if not WEBHOOK_ALERT_URL or record["level"].no < 40:  # سطح 40 یعنی ERROR به بالا
        return

    payload = {
        "text": (
            f"🚨 *هشدار سیستم مانیتورینگ یاسوج*\n"
            f"📅 تاریخ: `{get_current_jalali_str()}`\n"
            f"⚠️ سطح: `{record['level'].name}`\n"
            f"📍 ماژول: `{record['name']}:{record['line']}`\n"
            f"💬 پیام: {sanitize_message(record['message'])}\n"
            f"🆔 Trace-ID: `{record['extra'].get('trace_id', 'None')}`"
        )
    }

    try:
        req = urllib.request.Request(
            WEBHOOK_ALERT_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=3)
    except Exception:
        pass  # جلوگیری از بلاک شدن لاگر در صورت قطعی اینترنت


# =============================================================================
# فرمت‌کننده‌های خروجی (Console + JSON)
# =============================================================================
def _console_formatter(record: Dict[str, Any]) -> str:
    """
    فرمت سفارشی برای کنسول با تاریخ شمسی، حافظه رم، دستورات گیت‌هاب (قابلیت ۹)
    و هماهنگ با TQDM (قابلیت ۱۰).
    """
    # اعمال سانسور روی پیام
    record["message"] = sanitize_message(record["message"])
    jalali_time = get_current_jalali_str()
    ram_mb = get_memory_usage_mb()
    trace_id = record["extra"].get("trace_id", "-")

    # قابلیت ۹: هماهنگی با گیت‌هاب اکشنز (در صورتی که داخل CI/CD اجرا شود)
    prefix = ""
    if os.getenv("GITHUB_ACTIONS") == "true":
        if record["level"].name == "ERROR":
            prefix = f"::error file={record['file'].path},line={record['line']}::"
        elif record["level"].name == "WARNING":
            prefix = f"::warning file={record['file'].path},line={record['line']}::"

    # قالب خروجی رنگی شیک
    return (
        f"{prefix}<green>[{jalali_time}]</green> "
        f"<level>{record['level'].name: <7}</level> | "
        f"<magenta>RAM:{ram_mb:.0f}MB</magenta> | "
        f"<yellow>[{trace_id}]</yellow> | "
        f"<cyan>{record['name']}:{record['function']}:{record['line']}</cyan> - "
        f"<level>{record['message']}</level>\n"
    )


def _json_formatter(record: Dict[str, Any]) -> str:
    """فرمت ذخیره ساختاریافته JSON Lines با تمام متادیتاها."""
    if not check_disk_space_healthy():
        return ""  # توقف ثبت در صورت پر شدن هارد برای نجات سرور

    sanitized_msg = sanitize_message(record["message"])
    log_entry = {
        "jalali_time": get_current_jalali_str(),
        "utc_timestamp": record["time"].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        "level": record["level"].name,
        "trace_id": record["extra"].get("trace_id", None),
        "city": record["extra"].get("city", "یاسوج"),
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
        "ram_mb": round(get_memory_usage_mb(), 2),
        "message": sanitized_msg,
        "extra": record["extra"]
    }

    if record["exception"]:
        log_entry["exception"] = {
            "type": record["exception"].type.__name__ if record["exception"].type else "Exception",
            "value": sanitize_message(str(record["exception"].value)),
            "has_traceback": record["exception"].traceback is not None
        }

    return json.dumps(log_entry, ensure_ascii=False) + "\n"


# =============================================================================
# قابلیت ۱۰: سینک سازگار با نوار پیشرفت tqdm
# =============================================================================
def _tqdm_compatible_write(message):
    """جلوگیری از شکسته شدن خطوط نوار پیشرفت هنگام چاپ همزمان لاگ."""
    try:
        from tqdm import tqdm
        tqdm.write(message, end="")
    except ImportError:
        sys.stderr.write(message)


# =============================================================================
# هسته راه‌اندازی سیستم لاگر
# =============================================================================
def setup_logger():
    """راه‌اندازی زنجیره سینک‌های لاگور با تمام امکانات دفاعی و آماری."""
    logger.remove()

    # ۱. سینک کنسول هماهنگ با TQDM و گیت‌هاب اکشنز
    logger.add(
        _tqdm_compatible_write,
        level=LOG_LEVEL,
        format=_console_formatter,
        colorize=True,
        enqueue=True
    )

    # ۲. سینک فایل روزانه با فرمت استاندارد و قابلیت چرخش خودکار
    logger.add(
        LOGS_DIR / "app_{time:YYYY-MM-DD}.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="00:00",
        retention="14 days",
        compression="zip",
        encoding="utf-8",
        enqueue=True
    )

    # ۳. سینک فایل خطاهای مهلک JSON Lines
    logger.add(
        LOGS_DIR / "errors_{time:YYYY-MM-DD}.jsonl",
        level="ERROR",
        format=_json_formatter,
        rotation="10 MB",
        retention="30 days",
        encoding="utf-8",
        enqueue=True
    )

    # ۴. سینک وب‌هوک اخطار آنی
    if WEBHOOK_ALERT_URL:
        logger.add(_send_webhook_alert, level="ERROR", enqueue=True)

    return logger.bind(trace_id="SYSTEM", city="یاسوج")


app_logger = setup_logger()


# =============================================================================
# قابلیت ۵: مدیریت Trace-ID و تولید لاگر متصل به یک فرایند
# =============================================================================
def get_trace_logger(poi_name_or_id: Optional[str] = None, city_name: str = "یاسوج"):
    """
    ایجاد یک لاگر متصل به یک شناسه رهگیری (Trace ID).
    به کمک این لاگر می‌توانید تمام لاگ‌های مربوط به یک بیزینس خاص را ردیابی کنید.
    """
    short_uuid = uuid.uuid4().hex[:8]
    trace_id = f"{poi_name_or_id[:10]}_{short_uuid}" if poi_name_or_id else f"REQ_{short_uuid}"
    return app_logger.bind(trace_id=trace_id, city=city_name)


# =============================================================================
# قابلیت ۳: دکوراتور اندازه‌گیری زمان اجرای توابع (@log_execution_time)
# =============================================================================
def log_execution_time(action_name: Optional[str] = None):
    """
    دکوراتور محاسبه‌گر زمان اجرای توابع استخراج، پارس یا وب‌اسکرپینگ به میلی‌ثانیه.
    
    مثال استفاده:
    @log_execution_time("استعلام موقعیت از نشان")
    def query_neshan_api(lat, lon):
        ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tag = action_name or func.__name__
            start_time = time.perf_counter()
            app_logger.debug(f"⏳ شروع عملیات: '{tag}'")
            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                app_logger.info(f"✅ پایان عملیات: '{tag}' در {elapsed_ms:.1f} میلی‌ثانیه")
                return result
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                app_logger.error(f"❌ شکست عملیات: '{tag}' پس از {elapsed_ms:.1f} میلی‌ثانیه | خطا: {exc}")
                raise exc
        return wrapper
    return decorator


# =============================================================================
# قابلیت ۷: لاگر دامپ باینری / متنی (Dump Logger)
# =============================================================================
def dump_response_debug(identifier: str, content: Any, extension: str = "html") -> Path:
    """
    ذخیره محتوای خام پاسخ سرور، کپچا یا ساختار JSON خراب‌شده برای دیباگ آفلاین.
    فایل ذخیره‌شده را در لاگ با آدرس دقیق گزارش می‌دهد.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', identifier)
    file_path = DUMPS_DIR / f"dump_{clean_id}_{timestamp}.{extension}"

    try:
        if isinstance(content, bytes):
            with open(file_path, "wb") as f:
                f.write(content)
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(str(content))
        app_logger.warning(f"📸 دامپ خطایابی ذخیره شد در: {file_path}")
        return file_path
    except Exception as e:
        app_logger.error(f"خطا در ایجاد دامپ دیباگ: {e}")
        return file_path
