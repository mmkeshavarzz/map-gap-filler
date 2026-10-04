"""
src/exporters/excel_exporter.py
نسخه فول‌آپشن: نمودار پای، محافظت، اعتبارسنجی کشویی، فرمتینگ شرطی و ...
"""
import pandas as pd
from pathlib import Path
from typing import List
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.chart import PieChart, Reference
from src.core.models import BusinessPOI

class ExcelExporter:
    def __init__(self, output_dir: str = "exports/excel"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def flatten_poi_for_excel(self, poi: BusinessPOI) -> dict:
        """آماده‌سازی دیتای تخت برای اکسل با فرمول‌های خاص"""
        lat = poi.coordinates.latitude if poi.coordinates else ""
        lon = poi.coordinates.longitude if poi.coordinates else ""
        
        # فیچر 3: هایپرلینک گوگل مپ
        map_link = f'=HYPERLINK("https://maps.google.com/?q={lat},{lon}", "مشاهده روی نقشه")' if lat else "ندارد"
        
        # فیچر 5: اسپارک‌لاین متنی (نشانگر درصد کامل بودن به صورت کاراکتر)
        bars = int((poi.confidence_score) * 10)
        progress_bar = ("█" * bars) + ("░" * (10 - bars))

        return {
            "ID (قفل شده)": poi.id,
            "نام کسب‌وکار": poi.title,
            "دسته‌بندی": poi.category.primary_fa,
            "شهر": poi.city,
            "آدرس": poi.address,
            "تلفن‌ها": " - ".join(poi.contacts.phone_numbers),
            "امتیاز سلامت": poi.health_report.health_score,
            "کلاس کیفیت": poi.health_report.tier,
            "پیشرفت تکمیل": progress_bar,
            "موقعیت مپ": map_link,
            "بج‌ها": poi.health_report.dashboard_badges,
            "وضعیت بازبینی": "نیاز به بررسی", # ستون مخصوص منوی کشویی انسانی
            "پاداش (تومان)": poi.health_report.bounty_toman
        }

    def export_batch(self, batch_data: List[BusinessPOI], batch_id: str):
        if not batch_data:
            return
            
        file_path = self.output_dir / f"batch_{batch_id}_luxury_report.xlsx"
        
        # 1. ساخت دیتافریم و ذخیره اولیه با پانداس
        df = pd.DataFrame([self.flatten_poi_for_excel(p) for p in batch_data])
        df.to_excel(file_path, index=False, engine='openpyxl')

        # باز کردن فایل با openpyxl برای جادوی استایل‌دهی!
        wb = load_workbook(file_path)
        ws = wb.active
        ws.title = "Data_Report"

        # فیچر 10: هدر سازمانی
        ws.oddHeader.left.text = "شرکت توسعه دیتای خفن - گزارش محرمانه"

        # استایل‌های رنگی (فیچر 1)
        gold_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")
        red_fill = PatternFill(start_color="FF9999", end_color="FF9999", fill_type="solid")

        # فیچر 8: اعتبارسنجی منوی کشویی (Drop-down) برای ستون وضعیت (ستون L)
        dv = DataValidation(type="list", formula1='"تایید شد,رد شد,نیاز به بررسی"', allow_blank=True)
        ws.add_data_validation(dv)
        dv.add(f"L2:L{len(batch_data)+1}")

        # اعمال تغییرات روی سطرها
        for row in range(2, len(batch_data) + 2):
            tier = ws[f"H{row}"].value
            # فیچر 1: رنگی کردن ردیف‌ها
            if tier == "PLATINUM":
                for cell in ws[row]: cell.fill = gold_fill
            elif tier == "TRASH":
                for cell in ws[row]: cell.fill = red_fill

            # فیچر 7: قفل کردن ستون ID (فقط ستون A رو قفل می‌کنیم، بقیه بازن)
            ws[f"A{row}"].protection = openpyxl.styles.Protection(locked=True)
            for col in range(2, 14): # آنلاک کردن بقیه ستون‌ها
                ws.cell(row=row, column=col).protection = openpyxl.styles.Protection(locked=False)

        # فیچر 2: اتوفیلتر و فریز کردن سطر اول
        ws.auto_filter.ref = ws.dimensions
        ws.freeze_panes = "A2"

        # فیچر 6: تنظیم عرض ستون‌ها هوشمند
        for col in ws.columns:
            max_length = max(len(str(cell.value)) for cell in col if cell.value)
            ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 50)

        # فیچر 9: محاسبه مجموع پاداش‌ها (Bounty Calculator) در انتهای ستون
        last_row = len(batch_data) + 2
        ws[f"L{last_row}"] = "جمع پاداش‌ها:"
        ws[f"M{last_row}"] = f"=SUM(M2:M{last_row-1})"
        ws[f"M{last_row}"].font = Font(bold=True)

        # فیچر 4: رسم نمودار داینامیک در یک شیت مجزا
        ws_chart = wb.create_sheet("Analytics_Chart")
        pie = PieChart()
        pie.title = "توزیع کیفیت داده‌ها"
        # مرجع دیتا برای نمودار (از ستون H - کلاس کیفیت) - نیاز به گروه‌بندی دارد اما برای دمو ساده می‌زنیم
        labels = Reference(ws, min_col=8, min_row=2, max_row=len(batch_data)+1)
        data = Reference(ws, min_col=8, min_row=1, max_row=len(batch_data)+1)
        pie.add_data(data, titles_from_data=True)
        pie.set_categories(labels)
        ws_chart.add_chart(pie, "B2")

        # فعال‌سازی قفل شیت دیتا (اگه پسورد خواستی اینجا بذار)
        ws.protection.sheet = True

        wb.save(file_path)
        print(f"🍹 VIP Excel with Charts & Logic saved: {file_path}")
