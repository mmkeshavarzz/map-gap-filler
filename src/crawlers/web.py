"""
src/crawlers/web.py
=============================================================================
خزنده وب (The Web Godzilla - Autonomous Edition) 🦖🌐
ارث‌بری شده از BaseCrawler ناهمگام.

تجهیزات: 
استخراج JSON-LD، رندر JS و عبور از Cloudflare، استخراج اینماد و نقشه، هوش مصنوعی آدرس،
+ (آپدیت جدید): پیمایش خودکار و عمیق (Deep Crawl) صفحات تماس و نقشه سایت بدون نیاز به ارکستراتور!
=============================================================================
"""

import re
import json
import time
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import AsyncGenerator, Optional, Tuple, List, Dict
from urllib.parse import urljoin, urlparse

# تلاش برای لود کردن Playwright (برای سایت‌های خفن و کلودفلردار)
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_ENABLED = True
except ImportError:
    PLAYWRIGHT_ENABLED = False

from src.crawlers.base import BaseCrawler

class WebCrawler(BaseCrawler):
    """
    هیولای خودمختار اینترنت که تا تهِ سایت‌ها رو درمیاره! 🦖🔍
    """

    def __init__(self, proxies: list = None):
        super().__init__(crawler_name="web_godzilla", proxies=proxies, delay_range=(2.0, 5.0))
        self._session: Optional[aiohttp.ClientSession] = None
        
        # مانیتورینگ سرعت و عملکرد 📊
        self.total_pages_crawled = 0
        self.start_time = time.time()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            headers = self._get_random_headers()
            headers.update({
                "Accept": "*/*", 
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
            })
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    async def _render_with_playwright(self, url: str) -> Optional[str]:
        """اجرای مرورگر واقعی برای رندر جاوا اسکریپت و عبور از کپچا 🛡️"""
        if not PLAYWRIGHT_ENABLED:
            return None
        try:
            self.logger.info(f"🕶️ اجرای مرورگر نامرئی برای سایت: {url}")
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, wait_until="networkidle", timeout=20000)
                html = await page.content()
                await browser.close()
                return html
        except Exception as e:
            self.logger.warning(f"❌ شکست در رندر Playwright: {e}")
            return None

    async def explore_sitemap(self, base_url: str) -> List[str]:
        """پیمایشگر نقشه سایت: پیدا کردن لینک‌های مهم به صورت خودکار 🧭"""
        sitemap_url = urljoin(base_url, "sitemap.xml")
        session = await self._get_session()
        important_urls = []
        try:
            self.logger.debug(f"🗺️ در حال جستجو در نقشه سایت: {sitemap_url}")
            async with session.get(sitemap_url, timeout=10) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    soup = BeautifulSoup(content, 'xml')
                    # دنبال کلمات کلیدی تو لینک‌های سایت‌مپ می‌گردیم
                    for loc in soup.find_all('loc'):
                        text_url = loc.text.lower()
                        if any(kw in text_url for kw in ['contact', 'about', 'branch', 'تماس', 'درباره']):
                            important_urls.append(loc.text)
                    self.logger.debug(f"🎯 {len(important_urls)} لینک طلایی از نقشه سایت پیدا شد!")
                    return important_urls[:3] # بیشتر از ۳ تا نره که تو لوپ نیفتیم
        except Exception as e:
            self.logger.debug(f"⚠️ نقشه سایتی پیدا نشد یا خطا داد.")
        return []

    def get_performance_metric(self) -> float:
        """سرعت‌سنج ربات 📊"""
        elapsed = time.time() - self.start_time
        speed = self.total_pages_crawled / elapsed if elapsed > 0 else 0
        return speed

    async def fetch_data(self, target_url: str, checkpoint_id: Optional[str] = None) -> Optional[str]:
        """گرفتن سورس صفحه با هر ترفندی که شده (معمولی یا Playwright)"""
        if not target_url.startswith('http'):
            target_url = 'https://' + target_url

        session = await self._get_session()
        proxy = self.proxies[self.current_proxy_index] if self.proxies else None
        
        try:
            async with session.get(target_url, proxy=proxy, timeout=15) as response:
                if response.status in [403, 503]:
                    self.logger.warning(f"🚫 سپر دفاعی سایت فعال شد! سوئیچ به Playwright...")
                    return await self._render_with_playwright(target_url)
                if response.status == 200:
                    return await response.text()
        except Exception:
            return await self._render_with_playwright(target_url)
        return None

    def _extract_page_features(self, html_data: str, current_url: str) -> dict:
        """
        این متد کارگرِ زحمت‌کشِ ماست! فقط کالبدشکافی می‌کنه و دیتاها رو خام می‌ده بیرون 🪚
        """
        features = {
            "schema_org": {}, "contact_pages": [], "enamad_link": None,
            "embed_coords": [], "addresses": [], "phones": [],
            "socials": {"whatsapp": [], "emails": [], "instagram": [], "telegram": []}
        }
        
        soup = BeautifulSoup(html_data, 'html.parser')
        
        # ۱. استخراج JSON-LD
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and '@type' in data:
                    features["schema_org"] = data
                    break
            except: pass

        # ۲. پیدا کردن لینک‌های تماس با ما برای خزش عمیق
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.text.lower()
            if any(kw in text or kw in href.lower() for kw in ['تماس', 'ارتباط', 'contact', 'about']):
                full_link = urljoin(current_url, href)
                features["contact_pages"].append(full_link)
                
            # شکار اینماد
            if 'trustseal.enamad.ir' in href:
                features["enamad_link"] = href

        # ۳. استخراج مختصات از نقشه‌های جاساز شده (Iframe)
        for iframe in soup.find_all('iframe', src=True):
            if 'google.com/maps' in iframe['src']:
                coords = re.findall(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', iframe['src'])
                if coords:
                    features["embed_coords"].extend(coords)

        # ۴. پردازش متن برای آدرس، تلفن و لینک‌های عمیق
        clean_text = ' '.join(soup.get_text(separator=' ').split())
        
        address_pattern = r"(?:استان|شهر|خیابان|میدان|بلوار|کوچه|پلاک)\s+[\w\s،,-]{10,100}"
        features["addresses"] = re.findall(address_pattern, clean_text)
        features["phones"] = re.findall(r"(09\d{9}|0[1-9]{2}-?\d{8}|\+98\s?9\d{9})", clean_text.replace(" ", ""))

        # ۵. شبکه‌های اجتماعی
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].lower()
            if 'wa.me/' in href or 'whatsapp' in href:
                features["socials"]["whatsapp"].append(href)
            elif href.startswith('mailto:'):
                features["socials"]["emails"].append(href.replace('mailto:', ''))
            elif 'instagram.com' in href:
                features["socials"]["instagram"].append(href)
            elif 't.me' in href or 'telegram.me' in href:
                features["socials"]["telegram"].append(href)

        return features

    async def parse_data(self, html_data: str, base_url: str = "") -> AsyncGenerator[Tuple[dict, str], None]:
        """
        مدیر کل کالبدشکافی! اینجا صفحات رو خودمختار شخم می‌زنیم و دیتاها رو تلفیق می‌کنیم 🧠
        """
        if not html_data:
            return

        self.total_pages_crawled += 1
        speed = self.get_performance_metric()
        self.logger.info(f"⚡ سرعت خزش فعلی: {speed:.2f} صفحه/ثانیه")

        try:
            # گام اول: استخراج دیتای صفحه اصلی
            main_features = self._extract_page_features(html_data, base_url)
            
            # گام دوم: جمع‌آوری لینک‌های زیرمجموعه (تماس با ما + نقشه سایت)
            contact_links = list(set(main_features["contact_pages"]))[:3]
            sitemap_links = await self.explore_sitemap(base_url)
            
            sub_pages_to_crawl = list(set(contact_links + sitemap_links))
            
            # گام سوم: خزش عمیق (Deep Crawl) تو صفحات پیدا شده! 🤿
            if sub_pages_to_crawl:
                self.logger.info(f"🤿 شروع خزش عمیق روی {len(sub_pages_to_crawl)} لینک داخلی...")
                for sub_url in sub_pages_to_crawl:
                    # کمی تاخیر انسان‌گونه
                    await asyncio.sleep(1.5)
                    sub_html = await self.fetch_data(sub_url)
                    if sub_html:
                        self.total_pages_crawled += 1
                        sub_features = self._extract_page_features(sub_html, sub_url)
                        
                        # تلفیق (Merge) دیتاهای صفحه داخلی با صفحه اصلی
                        main_features["addresses"].extend(sub_features["addresses"])
                        main_features["phones"].extend(sub_features["phones"])
                        main_features["embed_coords"].extend(sub_features["embed_coords"])
                        
                        for k, v in sub_features["socials"].items():
                            main_features["socials"][k].extend(v)
                            
                        if not main_features["enamad_link"]:
                            main_features["enamad_link"] = sub_features["enamad_link"]
                        if not main_features["schema_org"]:
                            main_features["schema_org"] = sub_features["schema_org"]

            # گام چهارم: تمیزکاری و حذف تکراری‌ها (Deduplication) 🧹
            poi_data = {
                "source": "web_godzilla",
                "url": base_url,
                "schema_org": main_features["schema_org"],
                "enamad_link": main_features["enamad_link"],
                "embed_coords": list(set(main_features["embed_coords"])),
                "extracted_addresses": list(set(main_features["addresses"])),
                "phones": list(set(main_features["phones"])),
                "socials": {k: list(set(v)) for k, v in main_features["socials"].items()}
            }

            domain = urlparse(base_url).netloc if base_url else "unknown_domain"
            
            self.logger.debug(f"🎉 پایان عملیات گودزیلا برای {domain} | {len(poi_data['phones'])} تلفن و {len(poi_data['extracted_addresses'])} آدرس جمع شد!")
            yield poi_data, domain

        except Exception as e:
            self.logger.error(f"❌ خطا در آنالیز و تلفیق سایت: {e}")

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self.logger.debug("🔌 گودزیلا با شکم پر به خواب رفت! Zzz...")
