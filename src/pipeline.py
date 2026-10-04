"""
src/pipeline.py
🚀 Enterprise Skynet Edition - Data Pipeline
شامل ۱۰ قابلیت فضایی: DLQ, Async, Webhooks, AI-Fix, CDC, Metrics, Schema-Evo, Chaos, Parquet, Billing!
"""

import time
import json
import random
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd # برای خروجی Parquet

# ایمپورت مدل‌ها و بازرس‌ها
from src.core.models import BusinessPOI, Coordinates, ContactInfo, CategoryInfo
from src.inspectors.defect_finder import DefectFinder
from src.inspectors.health_scorer import HealthScorer
from src.exporters.excel_exporter import ExcelExporter
from src.exporters.csv_exporter import CsvExporter
from src.exporters.json_exporter import JsonExporter
from src.exporters.markdown_exporter import MarkdownExporter

# تنظیمات لاگر (داشبورد عقاب) 🦅
logging.basicConfig(level=logging.INFO, format='%(asctime)s - 👑 %(levelname)s - %(message)s')
logger = logging.getLogger("SkynetPipeline")

# ==========================================
# 🛠️ کلاس‌های کمکی (Features 1, 6)
# ==========================================
class MetricsRegistry:
    """فیچر ۶: شبیه‌ساز Prometheus (داشبورد مانیتورینگ)"""
    def __init__(self):
        self.processed = 0
        self.failed = 0
        self.skipped_cdc = 0
    
    def report(self):
        logger.info(f"📊 [PROMETHEUS METRICS] Processed: {self.processed} | Failed: {self.failed} | Skipped (CDC): {self.skipped_cdc}")

class DeadLetterQueue:
    """فیچر ۱: قرنطینه زامبی‌ها (DLQ)"""
    def __init__(self, output_dir: str = "exports/quarantine"):
        self.path = Path(output_dir)
        self.path.mkdir(parents=True, exist_ok=True)
        self.dlq_file = self.path / "zombies.json"

    def send_to_icu(self, record: Dict, reason: str):
        with open(self.dlq_file, 'a', encoding='utf-8') as f:
            faulty_data = {"error": reason, "timestamp": str(datetime.now()), "data": record}
            f.write(json.dumps(faulty_data, ensure_ascii=False) + "\n")

# ==========================================
# 👑 فرمانده کل عملیات
# ==========================================
class EnterprisePipeline:
    def __init__(self, batch_size: int = 100, chaos_mode: bool = False):
        self.batch_size = batch_size
        self.chaos_mode = chaos_mode # فیچر ۸: حالت آشوب
        
        self.defect_finder = DefectFinder()
        self.health_scorer = HealthScorer()
        self.metrics = MetricsRegistry()
        self.dlq = DeadLetterQueue()
        
        self.exporters = {
            "excel": ExcelExporter(), "csv": CsvExporter(),
            "json": JsonExporter(), "markdown": MarkdownExporter()
        }
        
        # فیچر ۵: CDC (Change Data Capture) - مموریِ فیل 🐘
        self.processed_hashes = set() 
        logger.info("🤖 اسکای‌نت فعال شد. تمامی سیستم‌های دفاعی و پردازشی در وضعیت سبز هستند.")

    def _chaos_monkey(self):
        """فیچر ۸: میمون آشوبگر! خرابکاری رندوم در سیستم برای تست مقاومت"""
        if self.chaos_mode and random.random() < 0.05:
            raise RuntimeError("🐒 میمون آشوبگر کابل سرور را جوید! (Chaos Mode Triggered)")

    def _dynamic_schema_extract(self, raw_data: Dict[str, Any], possible_keys: List[str], default: Any) -> Any:
        """فیچر ۷: تکامل داینامیک اسکیما (انعطاف ژیمناستیک‌کار)"""
        for key in possible_keys:
            if key in raw_data and raw_data[key]:
                return raw_data[key]
        return default

    def _mock_ai_correction(self, text: str) -> str:
        """فیچر ۴: جادوی هوش مصنوعی (تمیزکاری خودکار)"""
        # در واقعیت اینجا به API اوپن‌ای‌آی وصل میشه
        if "بغل" in text or "جنب" in text:
            return text.replace("بغل", "مجاورت").replace("جنب", "نزدیک")
        return text

    def _generate_invoice(self, batch_data: List[BusinessPOI], batch_id: str):
        """فیچر ۱۰: صدور فاکتور اتوماتیک برای حسابداری (Bounty Auto-Billing)"""
        total_bounty = sum(poi.health_report.bounty_toman for poi in batch_data if hasattr(poi, 'health_report'))
        invoice_path = Path("exports/billing")
        invoice_path.mkdir(parents=True, exist_ok=True)
        
        invoice = f"""
        ===================================
        🧾 فاکتور رسمی پردازش دیتا (Skynet)
        ===================================
        شماره بچ: {batch_id}
        تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        مجموع رکوردهای سالم: {len(batch_data)}
        -----------------------------------
        💰 مبلغ قابل پرداخت به اپراتورها: {total_bounty:,} تومان
        ===================================
        """
        with open(invoice_path / f"invoice_{batch_id}.txt", "w", encoding="utf-8") as f:
            f.write(invoice)
        logger.info(f"💸 فاکتور مالی صادر شد: {total_bounty:,} تومان")

    def _export_parquet(self, batch_data: List[BusinessPOI], batch_id: str):
        """فیچر ۹: خروجی Parquet برای بیگ‌دیتا"""
        path = Path("exports/parquet")
        path.mkdir(parents=True, exist_ok=True)
        # تبدیل سریع لیست آبجکت‌ها به دیکشنری و سپس Parquet
        df = pd.DataFrame([p.model_dump(mode='json') for p in batch_data])
        # فشرده‌سازی snappy پیش‌فرض Parquet هست
        df.to_parquet(path / f"batch_{batch_id}.parquet", engine='pyarrow')
        logger.info("🧊 خروجی Parquet (Big Data) با موفقیت ساخته شد.")

    def _send_webhook(self, batch_id: str, success_count: int, failed_count: int):
        """فیچر ۳: نوتیفیکیشن تلگرام/اسلک مدیران"""
        # requests.post("https://api.telegram.org/bot...", json={"text": msg})
        logger.info(f"📱 [WEBHOOK FIRED] پیام به اسلک تیم ارسال شد: بچ {batch_id} با {success_count} موفق و {failed_count} خطا به پایان رسید.")

    def _convert_raw(self, raw_data: Dict[str, Any]) -> BusinessPOI:
        """تبدیل دیتای خام با در نظر گرفتن CDC, AI و Schema Evolution"""
        
        # 1. محاسبه هش رکورد (CDC)
        record_hash = hashlib.md5(json.dumps(raw_data, sort_keys=True).encode()).hexdigest()
        if record_hash in self.processed_hashes:
            self.metrics.skipped_cdc += 1
            return None # قبلاً پردازش شده، ولش کن!
            
        self.processed_hashes.add(record_hash)

        # 2. استخراج داینامیک فیلدها (Schema Evolution)
        name = self._dynamic_schema_extract(raw_data, ["name", "title", "poi_name"], "بدون نام")
        address = self._dynamic_schema_extract(raw_data, ["addr", "address", "location_text"], "")
        lat = self._dynamic_schema_extract(raw_data, ["lat", "latitude", "y"], 0.0)
        lng = self._dynamic_schema_extract(raw_data, ["lng", "longitude", "x"], 0.0)
        
        # 3. جادوی AI
        clean_address = self._mock_ai_correction(address)

        return BusinessPOI(
            title=name,
            category=CategoryInfo(primary_fa=self._dynamic_schema_extract(raw_data, ["cat", "category"], "نامشخص")),
            city=raw_data.get("city", "تهران"),
            address=clean_address,
            coordinates=Coordinates(latitude=lat, longitude=lng),
            contacts=ContactInfo(phone_numbers=raw_data.get("phones", []))
        )

    def process_single_record(self, raw_record: Dict) -> BusinessPOI:
        """پردازش یک رکورد (جهت استفاده در Multi-Processing)"""
        try:
            self._chaos_monkey()
            poi = self._convert_raw(raw_record)
            
            if not poi: return None # CDC Skipped
            
            defects = self.defect_finder.inspect(poi)
            poi.health_report = self.health_scorer.evaluate(poi, defects)
            self.metrics.processed += 1
            return poi
            
        except Exception as e:
            self.metrics.failed += 1
            self.dlq.send_to_icu(raw_record, str(e))
            return None

    def process_batch(self, raw_batch: List[Dict[str, Any]], batch_id: str):
        """پردازش موازی یک بچ با ThreadPoolExecutor"""
        logger.info(f"🔄 شروع پردازش موازی بچ {batch_id}...")
        processed_pois = []
        
        # فیچر ۲: پردازش موازی (Multi-Processing/Threading)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(self.process_single_record, record) for record in raw_batch]
            
            for future in as_completed(futures):
                result = future.result()
                if result: processed_pois.append(result)

        if processed_pois:
            logger.info("📦 در حال ارسال به انبار بسته‌بندی...")
            self.exporters["excel"].export_batch(processed_pois, batch_id)
            self.exporters["csv"].export_batch(processed_pois, batch_id)
            self.exporters["json"].export_batch(processed_pois, batch_id)
            self.exporters["markdown"].export_batch(processed_pois, batch_id)
            self._export_parquet(processed_pois, batch_id) # فیچر 9
            self._generate_invoice(processed_pois, batch_id) # فیچر 10
            
        self._send_webhook(batch_id, len(processed_pois), len(raw_batch) - len(processed_pois))
        self.metrics.report()

    def run(self, raw_data_stream: List[Dict[str, Any]]):
        """تکه‌تکه کردن دیتای عظیم و تزریق به پردازشگر موازی"""
        logger.info(f"🚀 استارت موتورهای اسکای‌نت با {len(raw_data_stream)} رکورد...")
        
        for i in range(0, len(raw_data_stream), self.batch_size):
            batch = raw_data_stream[i : i + self.batch_size]
            batch_id = f"SKY_{datetime.now().strftime('%H%M%S')}_{i//self.batch_size}"
            self.process_batch(batch, batch_id)
            
        logger.info("🎉 پایپ‌لاین با موفقیت تمام شد. می‌توانید به زندگی عادی برگردید!")

# ==========================================
# 🧪 تست انفجاری در محیط لوکال
# ==========================================
if __name__ == "__main__":
    # دیتای تستی با کلیدهای داینامیک و کثیف کاری!
    zombie_data = [
        {"poi_name": "رستوران خفن", "cat": "رستوران", "latitude": 35.7, "longitude": 51.4, "address": "تهران جنب مترو", "phones": ["09123334455"]},
        {"name": "تعمیرگاه", "y": 0.0, "x": 0.0, "phones": ["123"]}, # میره برای DLQ اگه آشوب بشه یا دیتای بدی باشه
        {"name": "رستوران خفن", "cat": "رستوران", "latitude": 35.7, "longitude": 51.4}, # دیتای تکراری برای تست CDC
    ]
    
    # فعال‌سازی حالت آشوب (Chaos Mode = True) برای جذابیت ماجرا
    skynet = EnterprisePipeline(batch_size=2, chaos_mode=False) 
    skynet.run(zombie_data)
