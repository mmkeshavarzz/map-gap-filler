"""
src/core/models.py
ماژول پیشرفته و جامع مدل‌های داده‌ای Pydantic برای اعتبارسنجی نقاط مورد علاقه (POI).
طراحی‌شده بر اساس استانداردهای Enterprise-grade و سند معماری map-gap-filler.md.
"""

from datetime import datetime
from enum import Enum
import hashlib
import re
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field, field_validator, model_validator


# ==========================================
# 0. ابزار کمکی نرمال‌سازی متون فارسی (پیشنهاد ۴)
# ==========================================
def clean_persian_text(text: Optional[str]) -> str:
    """
    پاکسازی و استانداردسازی حروف فارسی:
    - تبدیل ي و ك عربی به ی و ک فارسی
    - حذف تنوین‌ها و اعراب زائد
    - اصلاح فاصله‌های مکرر و نیم‌فاصله‌ها
    """
    if not text:
        return ""
    
    # جدول تبدیل کاراکترهای عربی و ارقام به معادل فارسی
    translation_table = str.maketrans({
        "ي": "ی",
        "ك": "ک",
        "ة": "ه",
        "٠": "۰", "١": "۱", "٢": "۲", "٣": "۳", "٤": "۴",
        "٥": "۵", "٦": "۶", "٧": "۷", "٨": "۸", "٩": "۹",
        "•": "", "…": "...", "ـ": ""  # حذف کشیدگی حروف
    })
    cleaned = text.translate(translation_table)
    
    # حذف اعراب عربی (فتحه، ضمه، کسره، تنوین و ...)
    cleaned = re.sub(r"[\u064B-\u065F\u0670]", "", cleaned)
    
    # تمیزکاری فاصله‌های پی‌درپی و تب‌ها
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


# ==========================================
# 1. دسته‌بندی هوشمند دو زبانه (پیشنهاد ۱۰)
# ==========================================
CATEGORY_TAXONOMY: Dict[str, Dict[str, str]] = {
    "کافه": {"en": "cafe", "osm": "amenity=cafe"},
    "رستوران": {"en": "restaurant", "osm": "amenity=restaurant"},
    "کبابی": {"en": "kebab_restaurant", "osm": "amenity=restaurant;cuisine=kebab"},
    "فست فود": {"en": "fast_food", "osm": "amenity=fast_food"},
    "املاک": {"en": "real_estate_agency", "osm": "office=estate_agent"},
    "پوشاک": {"en": "clothing_store", "osm": "shop=clothes"},
    "سوپرمارکت": {"en": "supermarket", "osm": "shop=supermarket"},
    "داروخانه": {"en": "pharmacy", "osm": "amenity=pharmacy"},
    "نانوایی": {"en": "bakery", "osm": "shop=bakery"},
    "هتل": {"en": "hotel", "osm": "tourism=hotel"},
    "تعمیرگاه": {"en": "car_repair", "osm": "shop=car_repair"},
    "سایر": {"en": "point_of_interest", "osm": "amenity=place_of_business"}
}


class BusinessCategory(BaseModel):
    """مدل دسته‌بندی دو زبانه کسب‌وکار سازگار با استانداردهای گوگل مپ و OpenStreetMap."""
    primary_fa: str = Field(..., description="دسته‌بندی اصلی فارسی (مثلاً رستوران)")
    english_name: str = Field("point_of_interest", description="معادل انگلیسی گوگل")
    osm_tag: str = Field("amenity=place_of_business", description="برچسب استاندارد نقشه باز جهانی")

    @model_validator(mode="before")
    @classmethod
    def resolve_category(cls, data: Any) -> Any:
        if isinstance(data, str):
            cleaned = clean_persian_text(data)
            mapping = CATEGORY_TAXONOMY.get(cleaned, CATEGORY_TAXONOMY["سایر"])
            return {
                "primary_fa": cleaned,
                "english_name": mapping["en"],
                "osm_tag": mapping["osm"]
            }
        return data

# ==========================================
# سازگاری با پایپ‌لاین (Alias)
# ==========================================
CategoryInfo = BusinessCategory


# ==========================================
# 2. وضعیت و تاریخچه استعلام در نقشه‌ها (پیشنهاد ۹)
# ==========================================
class AuditStatus(str, Enum):
    NOT_REGISTERED = "not_registered"
    ALREADY_EXISTS = "already_exists"
    NEEDS_REVIEW = "needs_review"
    UNKNOWN = "unknown"


class SourcePlatform(str, Enum):
    INSTAGRAM = "instagram"
    TELEGRAM = "telegram"
    WEB = "web"
    MANUAL = "manual"


class AuditHistoryEntry(BaseModel):
    """ثبت لاگ تاریخی تغییر وضعیت کسب‌وکار روی نقشه‌ها."""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="زمان رویداد")
    platform: str = Field("neshan", description="نام سرویس نقشه (neshan یا google)")
    previous_status: AuditStatus = AuditStatus.UNKNOWN
    new_status: AuditStatus
    note: Optional[str] = Field(None, description="توضیحات تکمیلی یا علت تغییر وضعیت")


# ==========================================
# 3. مختصات و اعتبارسنجی یاسوج (پیشنهاد ۳)
# ==========================================

# راهنما: کادر جغرافیایی یاسوج بیرون کلاس تعریف شده تا پایدنتیک به عنوان فیلد داده‌ای بهش گیر نده
YASUJ_BOUNDING_BOX = {
    "min_lat": 30.5500, "max_lat": 30.7500,
    "min_lon": 51.5000, "max_lon": 51.7200
}

class Coordinates(BaseModel):
    """مختصات جغرافیایی به فرمت WGS84. مجهز به کادر جغرافیایی (Bounding Box) بافت شهری یاسوج."""
    latitude: float = Field(..., description="عرض جغرافیایی")
    longitude: float = Field(..., description="طول جغرافیایی")
    is_in_yasuj_box: bool = Field(True, description="آیا مختصات قطعاً درون کادر شهری یاسوج است؟")

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        if not (24.0 <= v <= 40.0):
            raise ValueError(f"عرض جغرافیایی {v} خارج از فلات ایران است!")
        return round(v, 6)

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        if not (44.0 <= v <= 64.0):
            raise ValueError(f"طول جغرافیایی {v} خارج از فلات ایران است!")
        return round(v, 6)

    @model_validator(mode="after")
    def check_yasuj_boundaries(self) -> "Coordinates":
        # راهنما: مستقیماً از متغیر Bounding Box تعریف شده در بالا استفاده می‌کند
        in_lat = YASUJ_BOUNDING_BOX["min_lat"] <= self.latitude <= YASUJ_BOUNDING_BOX["max_lat"]
        in_lon = YASUJ_BOUNDING_BOX["min_lon"] <= self.longitude <= YASUJ_BOUNDING_BOX["max_lon"]
        self.is_in_yasuj_box = bool(in_lat and in_lon)
        return self


# ==========================================
# 4. ساعات کاری هفتگی (پیشنهاد ۱)
# ==========================================
class WorkingHours(BaseModel):
    saturday: Optional[str] = Field("09:00-22:00", description="شنبه")
    sunday: Optional[str] = Field("09:00-22:00", description="یک‌شنبه")
    monday: Optional[str] = Field("09:00-22:00", description="دوشنبه")
    tuesday: Optional[str] = Field("09:00-22:00", description="سه‌شنبه")
    wednesday: Optional[str] = Field("09:00-22:00", description="چهارشنبه")
    thursday: Optional[str] = Field("09:00-22:00", description="پنج‌شنبه")
    friday: Optional[str] = Field("تعطیل", description="جمعه")
    description_notes: Optional[str] = Field(None, description="توضیحات خاص")


# ==========================================
# 5. امکانات رفاهی و خدمات (پیشنهاد ۷)
# ==========================================
class Facilities(BaseModel):
    has_pos_terminal: bool = Field(True, description="دارای دستگاه پوز")
    has_parking: bool = Field(False, description="پارکینگ اختصاصی")
    has_delivery: bool = Field(False, description="سرویس بیرون‌بر")
    has_free_wifi: bool = Field(False, description="وای‌فای رایگان")
    accepts_online_reservations: bool = Field(False, description="رزرو آنلاین")
    outdoor_seating: bool = Field(False, description="فضای نشستن باز")
    extra_tags: List[str] = Field(default_factory=list)


# ==========================================
# 6. تفکیک ریزامتیازهای کیفیت داده (پیشنهاد ۵)
# ==========================================
class ConfidenceBreakdown(BaseModel):
    has_valid_phone: float = Field(0.0)
    has_precise_coordinates: float = Field(0.0)
    has_rich_address: float = Field(0.0)
    has_media: float = Field(0.0)
    has_working_hours: float = Field(0.0)
    total_score: float = Field(0.0, ge=0.0, le=1.0)


# ==========================================
# 7. اطلاعات ارتباطی و تماس
# ==========================================
class ContactInfo(BaseModel):
    phone_numbers: List[str] = Field(default_factory=list, description="تلفن‌های معتبر")
    instagram_id: Optional[str] = Field(None, description="آیدی پیج")
    telegram_id: Optional[str] = Field(None, description="یوزرنیم تلگرام")
    website: Optional[str] = Field(None, description="وب‌سایت رسمی")

    @field_validator("phone_numbers")
    @classmethod
    def normalize_phones(cls, numbers: List[str]) -> List[str]:
        cleaned_list = []
        fa_to_en = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

        for num in numbers:
            num = num.translate(fa_to_en)
            digits = re.sub(r"\D", "", num)

            if digits.startswith("98") and len(digits) == 12:
                digits = "0" + digits[2:]
            elif digits.startswith("0098") and len(digits) == 14:
                digits = "0" + digits[4:]

            if len(digits) == 11 and (digits.startswith("09") or digits.startswith("074")):
                if digits not in cleaned_list:
                    cleaned_list.append(digits)
            elif len(digits) == 8 and not digits.startswith("0"):
                yasuj_phone = f"074{digits}"
                if yasuj_phone not in cleaned_list:
                    cleaned_list.append(yasuj_phone)

        return cleaned_list

    @field_validator("instagram_id", "telegram_id")
    @classmethod
    def sanitize_social_id(cls, v: Optional[str]) -> Optional[str]:
        if v:
            cleaned = v.strip().lstrip("@").lower()
            return cleaned if cleaned else None
        return None


# ==========================================
# 8. نتایج ممیزی روی نقشه‌ها (Audit Meta)
# ==========================================
class AuditResult(BaseModel):
    neshan_status: AuditStatus = AuditStatus.UNKNOWN
    neshan_matched_title: Optional[str] = None
    neshan_distance_meters: Optional[float] = None
    neshan_confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    
    google_status: AuditStatus = AuditStatus.UNKNOWN
    last_audited_at: Optional[datetime] = None
    history: List[AuditHistoryEntry] = Field(default_factory=list)

    def record_change(self, platform: str, new_status: AuditStatus, note: Optional[str] = None):
        prev = self.neshan_status if platform == "neshan" else self.google_status
        self.history.append(
            AuditHistoryEntry(
                platform=platform,
                previous_status=prev,
                new_status=new_status,
                note=note
            )
        )
        if platform == "neshan":
            self.neshan_status = new_status
        else:
            self.google_status = new_status
        self.last_audited_at = datetime.utcnow()

# ==========================================
# 🚨🔥 NEW: 8.5. گزارش سلامت سایبورگ (Data Health Report)
# ==========================================
class DataHealthReport(BaseModel):
    """
    پرونده پزشکی دیتا که توسط HealthScorer و DefectFinder پر می‌شود.
    """
    health_score: float = Field(100.0, description="نمره سلامت از 0 تا 100")
    tier: str = Field("UNKNOWN", description="کلاس کیفیت: PLATINUM, GOLD, SILVER, TRASH")
    defects: List[str] = Field(default_factory=list, description="لیست جرائم و نواقص رکورد")
    seo_readiness_index: str = Field("100/100", description="شاخص آمادگی سئو")
    bounty_toman: int = Field(0, description="پاداش نقدی برای اصلاح انسانی (به تومان)")
    can_be_auto_fixed: bool = Field(False, description="آیا اسکریپت می‌تواند نواقص را خودکار حل کند؟")
    dashboard_badges: str = Field("📍✅ | 📞✅ | 🌐✅", description="بج‌های بصری داشبورد")
    exporter_route: str = Field("exports/csv/uncategorized.csv", description="مسیر فایل خروجی مناسب این کلاس")


# ==========================================
# 9. مدل جامع و غول‌پیکر BusinessPOI 
# ==========================================
class BusinessPOI(BaseModel):
    """
    ستون فقرات اصلی پروژه map-gap-filler.
    """
    id: Optional[str] = Field(None, description="شناسه یکتا؛ در صورت خالی بودن خودکار تولید می‌شود")
    title: str = Field(..., min_length=2, max_length=150, description="نام پالایش‌شده کسب‌وکار")
    category: BusinessCategory = Field(default_factory=lambda: BusinessCategory.model_validate("سایر"))
    
    city: str = Field("یاسوج", description="نام شهر به فارسی استاندارد")
    province: str = Field("کهگیلویه و بویراحمد", description="استان مقصد")
    address: str = Field(..., min_length=5, description="آدرس متنی دقیق")
    
    coordinates: Optional[Coordinates] = None
    contacts: ContactInfo = Field(default_factory=ContactInfo)
    
    image_urls: List[str] = Field(default_factory=list, description="لینک عکس‌ها")
    working_hours: WorkingHours = Field(default_factory=WorkingHours)
    facilities: Facilities = Field(default_factory=Facilities)
    
    source_platform: SourcePlatform = Field(..., description="پلتفرم اولیه استخراج")
    source_url: Optional[str] = Field(None, description="لینک پست مبدا")
    raw_text: Optional[str] = Field(None, description="متن دست‌نخورده")
    
    audit: AuditResult = Field(default_factory=AuditResult)
    confidence_breakdown: ConfidenceBreakdown = Field(default_factory=ConfidenceBreakdown)
    confidence_score: float = Field(0.0, ge=0.0, le=1.0, description="نمره کل اعتبار رکورد")
    
    # 🚨 فیلد جدید: پرونده سلامت (تزریق قابلیت‌های جدید)
    health_report: DataHealthReport = Field(default_factory=DataHealthReport, description="گزارش صادر شده توسط قاضی!")

    created_at_jalali: Optional[str] = Field(None, description="تاریخ شمسی استخراج")
    discovered_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("title", "address", mode="before")
    @classmethod
    def apply_persian_cleanup(cls, v: Any) -> str:
        return clean_persian_text(str(v))

    @model_validator(mode="after")
    def post_processing(self) -> "BusinessPOI":
        if not self.id:
            first_phone = self.contacts.phone_numbers[0] if self.contacts.phone_numbers else ""
            raw_seed = f"{self.title.strip().lower()}_{self.city.strip().lower()}_{first_phone}"
            self.id = hashlib.sha256(raw_seed.encode("utf-8")).hexdigest()[:16]

        c_score = 0.0
        cb = self.confidence_breakdown

        if self.contacts.phone_numbers:
            cb.has_valid_phone = 0.25
            c_score += 0.25

        if self.coordinates:
            cb.has_precise_coordinates = 0.35 if self.coordinates.is_in_yasuj_box else 0.15
            c_score += cb.has_precise_coordinates

        if len(self.address) >= 15:
            cb.has_rich_address = 0.15
            c_score += 0.15

        if self.image_urls:
            cb.has_media = 0.15
            c_score += 0.15

        if self.working_hours and self.working_hours.saturday:
            cb.has_working_hours = 0.10
            c_score += 0.10

        cb.total_score = round(min(c_score, 1.0), 2)
        self.confidence_score = cb.total_score
        return self

    def to_geojson(self) -> Dict[str, Any]:
        """تبدیل مستقیم این کسب‌وکار به آبجکت استاندارد GeoJSON Feature."""
        geometry = None
        if self.coordinates:
            geometry = {
                "type": "Point",
                "coordinates": [self.coordinates.longitude, self.coordinates.latitude]
            }

        return {
            "type": "Feature",
            "id": self.id,
            "geometry": geometry,
            "properties": {
                "title": self.title,
                "category_fa": self.category.primary_fa,
                "category_en": self.category.english_name,
                "osm_tag": self.category.osm_tag,
                "city": self.city,
                "province": self.province,
                "address": self.address,
                "phones": self.contacts.phone_numbers,
                "instagram": self.contacts.instagram_id,
                "audit_status_neshan": self.audit.neshan_status.value,
                "confidence_score": self.confidence_score,
                
                # 🚨 تزریق دیتای پزشکی به خروجی نقشه!
                "health_tier": self.health_report.tier,
                "health_score": self.health_report.health_score,
                "dashboard_badges": self.health_report.dashboard_badges,
                
                "facilities": self.facilities.model_dump(),
                "working_hours": self.working_hours.model_dump(),
                "images_count": len(self.image_urls)
            }
        }

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
