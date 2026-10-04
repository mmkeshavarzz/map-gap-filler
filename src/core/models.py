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
    # اگر صنف جدیدی پیدا کردی، کافیه یه سطر جدید اینجا اضافه کنی
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
# 2. وضعیت و تاریخچه استعلام در نقشه‌ها (پیشنهاد ۹)
# ==========================================
class AuditStatus(str, Enum):
    NOT_REGISTERED = "not_registered"  # غایب در نقشه (مهم‌ترین طعمه!)
    ALREADY_EXISTS = "already_exists"  # قبلاً توسط دیگران ثبت شده
    NEEDS_REVIEW = "needs_review"      # شباهت اسمی مشکوک؛ نیازمند بازبینی اپراتور
    UNKNOWN = "unknown"                # تازه استخراج‌شده و در صف بررسی


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
class Coordinates(BaseModel):
    """
    مختصات جغرافیایی به فرمت WGS84.
    مجهز به کادر جغرافیایی (Bounding Box) بافت شهری یاسوج.
    """
    latitude: float = Field(..., description="عرض جغرافیایی")
    longitude: float = Field(..., description="طول جغرافیایی")
    is_in_yasuj_box: bool = Field(True, description="آیا مختصات قطعاً درون کادر شهری یاسوج است؟")

    # محدوده چهارگوشه شهر یاسوج (میتونی در صورت نیاز شعاع رو از اینجا بازتر کنی)
    YASUJ_BOUNDING_BOX = {
        "min_lat": 30.5500,
        "max_lat": 30.7500,
        "min_lon": 51.5000,
        "max_lon": 51.7200
    }

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
        """بررسی اینکه آیا نقطه در محدوده یاسوج قرار گرفته است یا نه."""
        in_lat = self.YASUJ_BOUNDING_BOX["min_lat"] <= self.latitude <= self.YASUJ_BOUNDING_BOX["max_lat"]
        in_lon = self.YASUJ_BOUNDING_BOX["min_lon"] <= self.longitude <= self.YASUJ_BOUNDING_BOX["max_lon"]
        self.is_in_yasuj_box = bool(in_lat and in_lon)
        return self


# ==========================================
# 4. ساعات کاری هفتگی (پیشنهاد ۱)
# ==========================================
class WorkingHours(BaseModel):
    """
    ساعات کاری کسب‌وکار در طول هفته.
    فرمت پیشنهادی برای بازه‌ها: '09:00-14:00,16:30-22:30' یا 'تعطیل'
    """
    saturday: Optional[str] = Field("09:00-22:00", description="شنبه")
    sunday: Optional[str] = Field("09:00-22:00", description="یک‌شنبه")
    monday: Optional[str] = Field("09:00-22:00", description="دوشنبه")
    tuesday: Optional[str] = Field("09:00-22:00", description="سه‌شنبه")
    wednesday: Optional[str] = Field("09:00-22:00", description="چهارشنبه")
    thursday: Optional[str] = Field("09:00-22:00", description="پنج‌شنبه")
    friday: Optional[str] = Field("تعطیل", description="جمعه")
    description_notes: Optional[str] = Field(None, description="توضیحات خاص مانند ایام سوگواری یا شیفت ظهر")


# ==========================================
# 5. امکانات رفاهی و خدمات (پیشنهاد ۷)
# ==========================================
class Facilities(BaseModel):
    """امکانات و ویژگی‌های فروشگاه/کسب‌وکار برای غنی‌سازی دیتابیس نقشه."""
    has_pos_terminal: bool = Field(True, description="دارای دستگاه پوز/کارت‌خوان")
    has_parking: bool = Field(False, description="پارکینگ اختصاصی یا جای پارک آسان")
    has_delivery: bool = Field(False, description="سرویس بیرون‌بر یا ارسال با پیک")
    has_free_wifi: bool = Field(False, description="اینترنت وای‌فای رایگان")
    accepts_online_reservations: bool = Field(False, description="امکان رزرو نوبت آنلاین")
    outdoor_seating: bool = Field(False, description="فضای نشستن در محیط باز")
    extra_tags: List[str] = Field(default_factory=list, description="تگ‌های خاص مانند 'مناسب کودکان'")


# ==========================================
# 6. تفکیک ریزامتیازهای کیفیت داده (پیشنهاد ۵)
# ==========================================
class ConfidenceBreakdown(BaseModel):
    """
    شفاف‌سازی امتیاز اعتماد کل به رکورد داده (بین ۰ تا ۱).
    به تفکیک فاکتورهای حیاتی نقشه.
    """
    has_valid_phone: float = Field(0.0, description="سهم اعتبارسنجی تلفن ثابت یا همراه")
    has_precise_coordinates: float = Field(0.0, description="سهم دقت لوکیشن و قرارگیری در یاسوج")
    has_rich_address: float = Field(0.0, description="سهم آدرس متنی دقیق")
    has_media: float = Field(0.0, description="سهم وجود عکس معتبر از تابلو یا محیط")
    has_working_hours: float = Field(0.0, description="سهم داشتن ساعات کاری")
    total_score: float = Field(0.0, ge=0.0, le=1.0, description="امتیاز تجمعی نهایی")


# ==========================================
# 7. اطلاعات ارتباطی و تماس
# ==========================================
class ContactInfo(BaseModel):
    """اطلاعات ارتباطی همراه با استانداردسازی کامل شماره‌ها."""
    phone_numbers: List[str] = Field(default_factory=list, description="تلفن‌های معتبر ۱۰ رقمی یا موبایل")
    instagram_id: Optional[str] = Field(None, description="آیدی پیج بدون کاراکتر @")
    telegram_id: Optional[str] = Field(None, description="یوزرنیم یا کانال تلگرام")
    website: Optional[str] = Field(None, description="وب‌سایت رسمی کسب‌وکار")

    @field_validator("phone_numbers")
    @classmethod
    def normalize_phones(cls, numbers: List[str]) -> List[str]:
        cleaned_list = []
        fa_to_en = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

        for num in numbers:
            num = num.translate(fa_to_en)
            digits = re.sub(r"\D", "", num)

            # اصلاح پیشوندهای بین‌المللی
            if digits.startswith("98") and len(digits) == 12:
                digits = "0" + digits[2:]
            elif digits.startswith("0098") and len(digits) == 14:
                digits = "0" + digits[4:]

            # شماره ۱۱ رقمی همراه یا شماره ثابت استانی با کد یاسوج (074)
            if len(digits) == 11 and (digits.startswith("09") or digits.startswith("074")):
                if digits not in cleaned_list:
                    cleaned_list.append(digits)
            # اگر شماره محلی ۸ رقمی بدون پیش‌شماره وارد شده بود
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
    """ارزیابی وضعیت رکورد در نشان و گوگل و بایگانی تاریخچه آن."""
    neshan_status: AuditStatus = AuditStatus.UNKNOWN
    neshan_matched_title: Optional[str] = None
    neshan_distance_meters: Optional[float] = None
    neshan_confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    
    google_status: AuditStatus = AuditStatus.UNKNOWN
    last_audited_at: Optional[datetime] = None
    history: List[AuditHistoryEntry] = Field(default_factory=list, description="تاریخچه کامل تغییر وضعیت‌ها")

    def record_change(self, platform: str, new_status: AuditStatus, note: Optional[str] = None):
        """متد کمکی برای اضافه کردن سریع یک رویداد به تاریخچه."""
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
# 9. مدل جامع و غول‌پیکر BusinessPOI (ادغام کامل هر ۱۰ پیشنهاد)
# ==========================================
class BusinessPOI(BaseModel):
    """
    ستون فقرات اصلی پروژه map-gap-filler.
    شامل تمام ۱۰ قابلیت هوشمند: هش خودکار، GeoJSON، امتیاز تفکیکی، ساعات کاری، مدیا و ...
    """
    id: Optional[str] = Field(None, description="شناسه یکتا؛ در صورت خالی بودن خودکار با هش SHA256 تولید می‌شود")
    title: str = Field(..., min_length=2, max_length=150, description="نام پالایش‌شده کسب‌وکار")
    category: BusinessCategory = Field(default_factory=lambda: BusinessCategory.model_validate("سایر"))
    
    city: str = Field("یاسوج", description="نام شهر به فارسی استاندارد")
    province: str = Field("کهگیلویه و بویراحمد", description="استان مقصد")
    address: str = Field(..., min_length=5, description="آدرس متنی دقیق")
    
    coordinates: Optional[Coordinates] = None
    contacts: ContactInfo = Field(default_factory=ContactInfo)
    
    # پیشنهاد ۶: تصاویر ویترین، تابلو، و منو
    image_urls: List[str] = Field(default_factory=list, description="لینک عکس‌های تابلو یا فضای مغازه")
    
    # پیشنهاد ۱: ساعات کاری
    working_hours: WorkingHours = Field(default_factory=WorkingHours)
    
    # پیشنهاد ۷: امکانات و خدمات رفاهی
    facilities: Facilities = Field(default_factory=Facilities)
    
    # خاستگاه استخراج داده
    source_platform: SourcePlatform = Field(..., description="پلتفرم اولیه استخراج")
    source_url: Optional[str] = Field(None, description="لینک پست، پروفایل یا پیام مبدا")
    raw_text: Optional[str] = Field(None, description="متن دست‌نخورده جهت ردیابی کراولر")
    
    # بررسی روی نقشه‌ها
    audit: AuditResult = Field(default_factory=AuditResult)
    
    # پیشنهاد ۵: تفکیک امتیاز اعتبار
    confidence_breakdown: ConfidenceBreakdown = Field(default_factory=ConfidenceBreakdown)
    confidence_score: float = Field(0.0, ge=0.0, le=1.0, description="نمره کل اعتبار رکورد")
    
    # متادیتای زمانی
    created_at_jalali: Optional[str] = Field(None, description="تاریخ شمسی استخراج")
    discovered_at: datetime = Field(default_factory=datetime.utcnow)

    # پیشنهاد ۴: پاکسازی خودکار ی/ک و علائم در عنوان و آدرس
    @field_validator("title", "address", mode="before")
    @classmethod
    def apply_persian_cleanup(cls, v: Any) -> str:
        return clean_persian_text(str(v))

    # پیشنهاد ۲: تولید خودکار ID هش‌شده یکتا بر مبنای SHA-256
    # و پیشنهاد ۵: محاسبه امتیاز کیفیت کل
    @model_validator(mode="after")
    def post_processing(self) -> "BusinessPOI":
        # ۱. ساخت هش یکتا در صورت عدم وجود
        if not self.id:
            first_phone = self.contacts.phone_numbers[0] if self.contacts.phone_numbers else ""
            raw_seed = f"{self.title.strip().lower()}_{self.city.strip().lower()}_{first_phone}"
            self.id = hashlib.sha256(raw_seed.encode("utf-8")).hexdigest()[:16]

        # ۲. محاسبه خودکار ریزامتیازهای Confidence Score
        c_score = 0.0
        cb = self.confidence_breakdown

        if self.contacts.phone_numbers:
            cb.has_valid_phone = 0.25
            c_score += 0.25

        if self.coordinates:
            # اگر مختصات داخل کادر یاسوج بود امتیاز بالاتر می‌گیرد
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

    # پیشنهاد ۸: تولید خروجی استاندارد نقشه (GeoJSON Feature)
    def to_geojson(self) -> Dict[str, Any]:
        """
        تبدیل مستقیم این کسب‌وکار به آبجکت استاندارد GeoJSON Feature.
        آماده برای رندر در Leaflet، Mapbox، QGIS و سرورهای نقشه نشان.
        """
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
