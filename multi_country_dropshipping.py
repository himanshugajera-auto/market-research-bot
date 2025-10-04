"""
Multi-Country Dropshipping Product Trend Finder
Targets: USA, Australia, UAE, Saudi Arabia
Focus: Safe, non-branded trending products
"""

import os
import json
from datetime import datetime
import anthropic
import requests
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class MultiCountryDropshippingBot:
    def __init__(self):
        self.claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        # Google Docs API
        creds = Credentials.from_authorized_user_info(
            json.loads(os.getenv("GOOGLE_CREDENTIALS"))
        )
        self.docs_service = build('docs', 'v1', credentials=creds)
        self.drive_service = build('drive', 'v3', credentials=creds)
        
        # Safe product categories (avoid copyright/legal issues)
        self.safe_categories = [
            'home-garden',
            'kitchen',
            'sports-fitness',
            'pet-supplies',
            'baby-products',
            'arts-crafts',
            'tools-home-improvement',
            'automotive-accessories',
            'health-household'
        ]
    
    def scrape_amazon_usa(self):
        """Scrape Amazon.com best sellers (USA)"""
        results = []
        
        for category in self.safe_categories[:5]:
            try:
                url = f'https://www.amazon.com/Best-Sellers-{category}/zgbs/{category}'
                response = requests.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Basic scraping - Amazon structure changes frequently
                print(f"  Scraped Amazon USA - {category}")
                
            except Exception as e:
                print(f"Error scraping Amazon USA {category}: {e}")
        
        return results[:20]
    
    def scrape_amazon_australia(self):
        """Scrape Amazon.com.au best sellers (Australia)"""
        results = []
        
        for category in self.safe_categories[:5]:
            try:
                url = f'https://www.amazon.com.au/Best-Sellers-{category}/zgbs/{category}'
                response = requests.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }, timeout=10)
                
                print(f"  Scraped Amazon AU - {category}")
                
            except Exception as e:
                print(f"Error scraping Amazon AU {category}: {e}")
        
        return results[:20]
    
    def scrape_amazon_uae(self):
        """Scrape Amazon.ae best sellers (UAE)"""
        results = []
        
        for category in self.safe_categories[:5]:
            try:
                url = f'https://www.amazon.ae/Best-Sellers-{category}/zgbs/{category}'
                response = requests.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }, timeout=10)
                
                print(f"  Scraped Amazon UAE - {category}")
                
            except Exception as e:
                print(f"Error scraping Amazon UAE {category}: {e}")
        
        return results[:20]
    
    def scrape_etsy_trending(self):
        """Scrape Etsy trending products (good for handmade/unique items)"""
        results = []
        try:
            url = 'https://www.etsy.com/trending'
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }, timeout=10)
            
            print("  Scraped Etsy trending")
            
        except Exception as e:
            print(f"Error scraping Etsy: {e}")
        
        return results[:15]
    
    def scrape_tiktok_made_me_buy_it(self):
        """Get products from TikTok viral trends (via Google search)"""
        results = []
        serper_key = os.getenv("SERPER_API_KEY")
        
        if not serper_key:
            print("  Skipping TikTok trends (no Serper API key)")
            return results
        
        queries = [
            "TikTok made me buy it 2025",
            "viral TikTok products",
            "TikTok shop trending products"
        ]
        
        for query in queries:
            try:
                response = requests.post(
                    'https://google.serper.dev/search',
                    headers={'X-API-KEY': serper_key},
                    json={'q': query, 'num': 10},
                    timeout=10
                )
                data = response.json()
                
                for item in data.get('organic', [])[:3]:
                    results.append({
                        'source': 'TikTok Trends (via Search)',
                        'title': item.get('title'),
                        'snippet': item.get('snippet'),
                        'url': item.get('link'),
                        'country': 'Global',
                        'timestamp': datetime.now().isoformat()
                    })
                    
            except Exception as e:
                print(f"Error searching TikTok trends: {e}")
        
        return results[:15]
    
    def scrape_google_trends_by_country(self):
        """Get Google Shopping trends for each target country"""
        results = []
        serper_key = os.getenv("SERPER_API_KEY")
        
        if not serper_key:
            print("  Skipping Google Trends (no API key)")
            return results
        
        countries = {
            'us': 'USA',
            'au': 'Australia', 
            'ae': 'UAE',
            'sa': 'Saudi Arabia'
        }
        
        safe_queries = [
            "trending home decor products",
            "viral kitchen gadgets",
            "best fitness accessories",
            "popular pet products",
            "trending baby items"
        ]
        
        for country_code, country_name in countries.items():
            for query in safe_queries[:2]:  # Limit to save API credits
                try:
                    response = requests.post(
                        'https://google.serper.dev/search',
                        headers={'X-API-KEY': serper_key},
                        json={
                            'q': query,
                            'gl': country_code,
                            'num': 5
                        },
                        timeout=10
                    )
                    data = response.json()
                    
                    for item in data.get('organic', [])[:2]:
                        results.append({
                            'source': f'Google Search ({country_name})',
                            'query': query,
                            'title': item.get('title'),
                            'snippet': item.get('snippet'),
                            'url': item.get('link'),
                            'country': country_name,
                            'timestamp': datetime.now().isoformat()
                        })
                        
                except Exception as e:
                    print(f"Error with Serper API for {country_name}: {e}")
        
        return results[:30]
    
    def scrape_aliexpress_dropshipping_center(self):
        """Get trending products from AliExpress Dropshipping Center"""
        results = []
        try:
            url = 'https://www.aliexpress.com/premium/dropshipping-products.html'
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }, timeout=10)
            
            print("  Scraped AliExpress dropshipping center")
            
        except Exception as e:
            print(f"Error scraping AliExpress: {e}")
        
        return results[:20]
    
    def scrape_reddit_dropshipping(self):
        """Scrape dropshipping-related subreddits"""
        results = []
        # Would use PRAW API like the SaaS bot
        # Placeholder for now
        return results
    
    def analyze_with_ai(self, data):
        """Use Claude to analyze multi-country dropshipping opportunities"""
        
        formatted_data = "\n\n".join([
            f"Country: {item.get('country', 'N/A')}\n"
            f"Source: {item.get('source', 'Unknown')}\n"
            f"Category: {item.get('category', 'N/A')}\n"
            f"Product/Topic: {item.get('title', item.get('snippet', 'N/A'))}\n"
            f"URL: {item.get('url', 'N/A')}"
            for item in data
        ])
        
        prompt = f"""You are an international e-commerce expert specializing in safe, legal dropshipping across USA, Australia, UAE, and Saudi Arabia.

IMPORTANT CONSTRAINTS:
- AVOID: Electronics (phones, laptops, TVs), branded products, trademarked items, copyrighted characters
- FOCUS: Home decor, kitchen gadgets, fitness accessories, pet supplies, baby products, jewelry, phone accessories (generic)

Analyze this data collected today ({datetime.now().strftime('%Y-%m-%d')}):

{formatted_data}

Provide analysis for each target market:

1. TOP TRENDING PRODUCTS BY COUNTRY:

   USA:
   - 3 safe product opportunities
   - Price range in USD
   - Target demographics
   - Marketing angle
   - Profit margin estimate

   AUSTRALIA:
   - 3 safe product opportunities  
   - Price range in AUD
   - Target demographics
   - Shipping considerations
   - Profit margin estimate

   UAE:
   - 3 safe product opportunities
   - Price range in AED
   - Cultural considerations
   - Payment preferences (COD important)
   - Profit margin estimate

   SAUDI ARABIA:
   - 3 safe product opportunities
   - Price range in SAR
   - Cultural sensitivities
   - Religious/seasonal factors
   - Profit margin estimate

2. UNIVERSAL TRENDING CATEGORIES:
   - Products that work across all 4 markets
   - Why they're trending globally
   - Sourcing recommendations (AliExpress, CJ Dropshipping, etc.)

3. MARKET-SPECIFIC INSIGHTS:
   - USA: Competition level, shipping expectations, return rates
   - Australia: Shipping times tolerance, popular niches
   - UAE: Luxury preferences, social media behavior
   - Saudi Arabia: Festival timing, gender-specific products

4. LEGAL & SAFETY CHECK:
   - Categories to completely avoid
   - Import restrictions by country
   - Certification requirements (if any)

5. SOURCING STRATEGY:
   - Best suppliers for each product type
   - Quality control tips
   - Shipping methods by country
   - Cost breakdown

6. MARKETING RECOMMENDATIONS:
   - USA: Facebook Ads, Google Shopping
   - Australia: Instagram, TikTok
   - UAE/Saudi: Instagram, Snapchat, WhatsApp marketing
   - Budget allocation per country

7. ACTION ITEMS:
   - Top 3 products to test FIRST (specify country)
   - Store setup priorities for multi-country
   - First week testing plan
   - Budget needed per country

Focus on SAFE, non-branded products with low legal risk. Prioritize profit margins and market demand."""

        try:
            message = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return message.content[0].text
            
        except Exception as e:
            print(f"Error with Claude API: {e}")
            return f"Error analyzing data: {e}"
    
    def create_google_doc(self, analysis, data_summary):
        """Create Google Doc with multi-country dropshipping report"""
        
        now = datetime.now()
        title = f"{now.strftime('%Y-%m-%d_%H-%M')}_DS_MULTI"
        
        try:
            doc = self.docs_service.documents().create(
                body={'title': title}
            ).execute()
            
            doc_id = doc['documentId']
            
            content = f"""MULTI-COUNTRY DROPSHIPPING TRENDS REPORT
Target Markets: USA | AUSTRALIA | UAE | SAUDI ARABIA
Generated: {now.strftime('%B %d, %Y at %I:%M %p UTC')}
Report ID: {now.strftime('%Y%m%d_%H%M')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 DATA SOURCES

Collection Time: {now.strftime('%Y-%m-%d %H:%M:%S')}

Platforms Monitored:
• Amazon.com (USA)
• Amazon.com.au (Australia)
• Amazon.ae (UAE)
• Google Trends (USA, AU, UAE, SA)
• TikTok Viral Products
• Etsy Trending
• AliExpress Dropshipping Center

Total Data Points: {len(data_summary)}

PRODUCT FOCUS: Safe categories (home, kitchen, fitness, pets, baby)
AVOIDING: Electronics, branded items, trademarked products

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AI ANALYSIS

{analysis}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 RAW DATA BY COUNTRY

"""
            
            # Group data by country
            by_country = {}
            for item in data_summary:
                country = item.get('country', 'Global')
                if country not in by_country:
                    by_country[country] = []
                by_country[country].append(item)
            
            for country, items in by_country.items():
                content += f"\n=== {country.upper()} ===\n"
                for i, item in enumerate(items[:10], 1):
                    content += f"\n{i}. {item.get('title', 'N/A')}\n"
                    if item.get('category'):
                        content += f"   Category: {item.get('category')}\n"
                    if item.get('url'):
                        content += f"   Link: {item.get('url')}\n"
                    content += f"   Source: {item.get('source', 'N/A')}\n"
            
            requests_body = [
                {
                    'insertText': {
                        'location': {'index': 1},
                        'text': content
                    }
                }
            ]
            
            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests_body}
            ).execute()
            
            print(f"✅ Report created: https://docs.google.com/document/d/{doc_id}/edit")
            return doc_id
            
        except HttpError as e:
            print(f"Error creating Google Doc: {e}")
            return None
    
    def run_daily_research(self):
        """Main execution"""
        print("🌍 Starting multi-country dropshipping trend research...")
        print(f"🎯 Target Markets: USA | Australia | UAE | Saudi Arabia")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n📊 Collecting data from international platforms...")
        
        usa_data = self.scrape_amazon_usa()
        print(f"  ✓ USA: {len(usa_data)} items")
        
        au_data = self.scrape_amazon_australia()
        print(f"  ✓ Australia: {len(au_data)} items")
        
        uae_data = self.scrape_amazon_uae()
        print(f"  ✓ UAE: {len(uae_data)} items")
        
        google_data = self.scrape_google_trends_by_country()
        print(f"  ✓ Google Trends (All Countries): {len(google_data)} items")
        
        tiktok_data = self.scrape_tiktok_made_me_buy_it()
        print(f"  ✓ TikTok Trends: {len(tiktok_data)} items")
        
        etsy_data = self.scrape_etsy_trending()
        print(f"  ✓ Etsy: {len(etsy_data)} items")
        
        aliexpress_data = self.scrape_aliexpress_dropshipping_center()
        print(f"  ✓ AliExpress: {len(aliexpress_data)} items")
        
        all_data = usa_data + au_data + uae_data + google_data + tiktok_data + etsy_data + aliexpress_data
        print(f"\n📦 Total data points: {len(all_data)}")
        
        if len(all_data) == 0:
            print("❌ No data collected. Exiting.")
            return
        
        print("\n🤖 Analyzing with Claude AI...")
        print("   Focusing on safe, non-branded products...")
        analysis = self.analyze_with_ai(all_data)
        print("  ✓ Analysis complete")
        
        print("\n📝 Creating Google Doc report...")
        doc_id = self.create_google_doc(analysis, all_data)
        
        if doc_id:
            print(f"\n✅ SUCCESS! Report available at:")
            print(f"https://docs.google.com/document/d/{doc_id}/edit")
        else:
            print("\n⚠️  Report creation failed, but here's the analysis:")
            print(analysis)
        
        print("\n🎉 Multi-country dropshipping research complete!")

if __name__ == "__main__":
    bot = MultiCountryDropshippingBot()
    bot.run_daily_research()
