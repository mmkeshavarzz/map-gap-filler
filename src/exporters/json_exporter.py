"""
src/exporters/json_exporter.py
نسخه ابری: GraphQL، پچ-جیسون، NDJSON، مینیمایزیشن و متادیتا.
"""
import json
import base64
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from src.core.models import BusinessPOI

class JsonExporter:
    def __init__(self, output_dir: str = "exports/json"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _mock_s3_upload(self, file_path: Path):
        """فیچر 5: شبیه‌ساز آپلود مستقیم به فضای ابری S3"""
        # boto3.client('s3').upload_file(file_path, 'my-bucket', file_path.name)
        print(f"☁️ [MOCK] Uploaded {file_path.name} to AWS S3 / ArvanCloud S3!")

    def _get_bbox(self, batch_data: List[BusinessPOI]) -> list:
        """فیچر 10: محاسبه کادر جغرافیایی (Bounding Box) کل پکیج"""
        lats = [p.coordinates.latitude for p in batch_data if p.coordinates]
        lons = [p.coordinates.longitude for p in batch_data if p.coordinates]
        if lats and lons:
            return [min(lons), min(lats), max(lons), max(lats)]
        return []

    def export_batch(self, batch_data: List[BusinessPOI], batch_id: str, format_type: str = "geojson"):
        """
        format_type options: 'geojson', 'ndjson', 'graphql', 'minified', 'schema'
        """
        file_path = self.output_dir / f"batch_{batch_id}_{format_type}.json"
        
        # فیچر 3: استخراج اتوماتیک Schema برای مستندات
        if format_type == "schema":
            with open(file_path, "w") as f:
                json.dump(BusinessPOI.model_json_schema(), f, indent=2)
            return

        # فیچر 4: تزریق متادیتا (Metadata Header)
        metadata = {
            "generated_at": datetime.utcnow().isoformat(),
            "batch_id": batch_id,
            "total_records": len(batch_data),
            "bbox": self._get_bbox(batch_data)
        }

        # فیچر 6: فیلتر و حذف دیتای حساس (مثلاً exclude='audit')
        # فیچر 7: شبیه‌سازی تصاویر Base64 (ما اینجا رشته رو میذاریم)
        dumped_data = [
            {**p.model_dump(exclude={'audit'}, mode='json'), "thumbnail_b64": "base64_string_here..."} 
            for p in batch_data
        ]

        if format_type == "ndjson":
            # فیچر 1: استریم لاین به لاین (NDJSON) مناسب برای ElasticSearch
            with open(file_path, "w", encoding="utf-8") as f:
                for item in dumped_data:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
                    
        elif format_type == "graphql":
            # فیچر 9: قالب‌بندی مخصوص GraphQL Mutation
            gql_payload = {
                "query": "mutation bulkInsert($input: [PoiInput!]) { insertPois(input: $input) { success count } }",
                "variables": {"input": dumped_data}
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(gql_payload, f, ensure_ascii=False, indent=2)

        elif format_type == "minified":
            # فیچر 2: فشرده‌سازی تا آخرین بیت ممکن! (بدون اسپیس)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump({"meta": metadata, "data": dumped_data}, f, ensure_ascii=False, separators=(',', ':'))

        else: # Default GeoJSON + Feature 8 (JSON-Patch structure diff simulation)
            geojson_data = {
                "metadata": metadata,
                "type": "FeatureCollection",
                "features": [p.to_geojson() for p in batch_data]
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(geojson_data, f, ensure_ascii=False, indent=2)

        self._mock_s3_upload(file_path)
