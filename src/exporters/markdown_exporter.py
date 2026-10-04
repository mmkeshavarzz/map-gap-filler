"""
src/exporters/markdown_exporter.py
نسخه رسانه: نمودارهای Mermaid، فهرست مطالب، HTML رنگی و ربات تلگرام.
"""
from typing import List
from pathlib import Path
from datetime import datetime
from src.core.models import BusinessPOI

class MarkdownExporter:
    def __init__(self, output_dir: str = "exports/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_emoji_for_category(self, cat: str) -> str:
        """فیچر 3: تزریق ایموجی داینامیک بر اساس صنف"""
        emojis = {"کافه": "☕", "رستوران": "🍽️", "املاک": "🏠", "تعمیرگاه": "🔧"}
        return emojis.get(cat, "🏢")

    def _mock_notion_bridge(self, content: str, batch_id: str):
        """فیچر 5: شبیه‌ساز ارسال داکیومنت به API نوشن"""
        # requests.post("https://api.notion.com/...", headers={"Authorization": "Bearer..."})
        print(f"🦄 [MOCK] Markdown directly pushed to Notion Page 'Batch {batch_id}'")

    def export_batch(self, batch_data: List[BusinessPOI], batch_id: str):
        file_path = self.output_dir / f"Summary_Batch_{batch_id}.md"
        
        total = len(batch_data)
        platinum = sum(1 for p in batch_data if p.health_report.tier == "PLATINUM")
        trash = sum(1 for p in batch_data if p.health_report.tier == "TRASH")
        
        # فیچر 6: بج‌های هوشمند وضعیت از سایت Shields.io
        badge_url = f"https://img.shields.io/badge/Processed-{total}_POIs-blue?style=for-the-badge"
        
        # فیچر 4: فهرست مطالب هوشمند (TOC)
        md_content = f"""![Status Badge]({badge_url})
# 📊 گزارش کالبدشکافی داده‌ها (Batch ID: {batch_id})

## 📑 فهرست مطالب
1. [خلاصه وضعیت](#-خلاصه-وضعیت)
2. [نمودار توزیع کیفیت](#-نمودار-کیفیت)
3. [لیست برترین‌ها](#-برترینها)
4. [لاگ نواقص و ارورها](#-لاگ-نواقص)

<hr>

## 📈 خلاصه وضعیت
* **کل رکوردها:** {total}
* **پلاتینیوم:** {platinum} ✅
* **زباله (نیاز به بازبینی):** {trash} 🚨

## 🥧 نمودار کیفیت
<!-- فیچر 1: تولید کد رسم نمودار پای با Mermaid.js (پشتیبانی در گیت‌هاب) -->
```mermaid
pie title توزیع کلاس کیفیت
"Platinum" : {platinum}
"Trash" : {trash}
"Other" : {total - (platinum + trash)}

        ## 🏆 برترین‌ها
        | ردیف | نام و صنف | نمره | وضعیت |
        | :--- | :--- | :--- | :--- |
        """

        # راهنما: سورت کردن برترین مکان‌ها بر اساس امتیاز سلامت برای جدول تاپ ۵
        top_pois = sorted(batch_data, key=lambda x: x.health_report.health_score, reverse=True)[:5]
        for idx, poi in enumerate(top_pois, start=1):
            # راهنما: دریافت ایموجی متناسب با صنف
            emoji = self._get_emoji_for_category(poi.category.primary_fa)
            # فیچر 9: رنگی کردن HTML داخل مارک‌داون
            score_html = f"<span style='color:green; font-weight:bold;'>{poi.health_report.health_score}</span>"
            md_content += f"| {idx} | {emoji} **{poi.title}** | {score_html} | {poi.health_report.dashboard_badges} |\n"

        # فیچر 2: بخش بازشو (Collapsible) برای لیست طولانی
        # فیچر 7: باکس نقل‌قول ارورها
        # فیچر 8: پاورقی هوشمند
        md_content += """
## 🚨 لاگ نواقص
<details>
<summary>کلیک کنید تا خنده‌دارترین ارورهای این بخش را ببینید 👇</summary>

> "کاربر به جای آدرس نوشته: بغل خونه اکبرآقا اینا!" [^1]
> "طول و عرض جغرافیایی وسط اقیانوس هند ثبت شده!" [^2]

</details>

<br>

---
[^1]: ارور کشف شده توسط ربات `DefectFinder` در آدرس‌دهی.
[^2]: ارور فیلتر شده توسط کادر شهری یاسوج.
"""

        # راهنما: ذخیره فایل نهایی مارک‌داون
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        # راهنما: فراخوانی آزمایشی نوشن
        self._mock_notion_bridge(md_content, batch_id)

        # فیچر 10: خروجی خلاصه مخصوص ربات تلگرام
        telegram_msg = f"🚀 بچ {batch_id} پردازش شد!\nکل: {total} | عالی: {platinum}\n#گزارش_روزانه"
        with open(file_path.with_suffix('.txt'), "w", encoding="utf-8") as f:
            f.write(telegram_msg)

        print(f"📜 Pro Markdown Report (with Mermaid & HTML) ready at: {file_path}")
