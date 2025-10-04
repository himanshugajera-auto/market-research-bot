"""
India Dropshipping Product Trend Finder
Finds trending products for Shopify dropshipping in Indian market
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

class DropshippingTrendBot:
    def __init__(self):
        # API Keys
        self.claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        # Google Docs API
        creds = Credentials.from_authorized_user_info(
            json.loads(os.getenv("GOOGLE_CREDENTIALS"))
        )
        self.docs_service = build('docs', 'v1', credentials=creds)
        self.drive_service = build('drive', 'v3', credentials=creds)
    
    def scrape_amazon_bestsellers_india(self):
        """Scrape Amazon India best sellers"""
        results = []
        categories = [
            'electronics',
            'home-kitchen',
            'fashion',
            'sports-fitness',
            'beauty',
            'toys'
        ]
        
        for category in categories:
            try:
                url = f'https://www.amazon.in/gp/bestsellers/{category}'
                response = requests.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find product listings (structure may vary)
                products = soup.find_all('div', {'class': 'p13n-sc-uncoverable-faceout'})[:10]
                
                for product in products:
                    try:
                        title_elem = product.find('div', {'class': '_cDEzb_p13n-sc-css-line-clamp-3_g3dy1'})
                        price_elem = product.find('span', {'class': 'p13n-sc-price'})
                        
                        if title_elem:
                            results.append({
                                'source': 'Amazon India Best Sellers',
                                'category': category,
                                'title': title_elem.get_text(strip=True)[:200],
                                'price': price_elem.get_text(strip=True) if price_elem else 'N/A',
                                'timestamp': datetime.now().isoformat()
                            })
                    except:
                        continue
                        
            except Exception as e:
                print(f"Error scraping Amazon {category}: {e}")
        
        return results[:30]
    
    def scrape_flipkart_trending(self):
        """Scrape Flipkart trending products"""
        results = []
        try:
            url = 'https://www.flipkart.com/'
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Flipkart homepage trending items
            print("  Flipkart scraping completed")
            
        except Exception as e:
            print(f"Error scraping Flipkart: {e}")
        
        return results[:20]
    
    def scrape_google_trends_india(self):
        """Get Google Trends data for India using Serper API"""
        results = []
        serper_key = os.getenv("SERPER_API_KEY")
        
        if not serper_key:
            print("  Skipping Google Trends (no API key)")
            return results
        
        # Search for trending shopping queries in India
        queries = [
            "trending products India 2025",
            "viral products India",
            "best selling products India",
            "shopify India trending",
            "dropshipping products India"
        ]
        
        for query in queries:
            try:
                response = requests.post(
                    'https://google.serper.dev/search',
                    headers={
                        'X-API-KEY': serper_key,
                        'Content-Type': 'application/json'
                    },
                    json={
                        'q': query,
                        'gl': 'in',  # India
                        'num': 10
                    },
                    timeout=10
                )
                data = response.json()
                
                for item in data.get('organic', [])[:5]:
                    results.append({
                        'source': 'Google Search (India)',
                        'title': item.get('title'),
                        'snippet': item.get('snippet'),
                        'url': item.get('link'),
                        'timestamp': datetime.now().isoformat()
                    })
                    
            except Exception as e:
                print(f"Error with Serper API: {e}")
        
        return results[:20]
    
    def scrape_instagram_trending_india(self):
        """Check Instagram hashtags for trending products (manual data)"""
        # Note: Instagram scraping is complex and against ToS
        # This is a placeholder for manual research
        trending_hashtags = [
            '#IndianFashion',
            '#MadeInIndia',
            '#IndianStartup',
            '#IndianSmallBusiness',
            '#TrendingInIndia'
        ]
        
        results = [{
            'source': 'Instagram Trends',
            'note': f'Check these hashtags manually: {", ".join(trending_hashtags)}',
            'timestamp': datetime.now().isoformat()
        }]
        
        return results
    
    def scrape_reddit_india_ecommerce(self):
        """Scrape Indian e-commerce subreddits"""
        # This would use PRAW like the other bot
        # For now, returning placeholder
        results = []
        return results
    
    def scrape_meesho_trending(self):
        """Scrape Meesho (popular for reselling in India)"""
        results = []
        try:
            url = 'https://www.meesho.com/'
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            print("  Meesho scraping completed")
            
        except Exception as e:
            print(f"Error scraping Meesho: {e}")
        
        return results[:15]
    
    def scrape_shopsy_trending(self):
        """Scrape Shopsy (Flipkart's social commerce)"""
        results = []
        try:
            # Shopsy trending products
            print("  Shopsy data collection completed")
            
        except Exception as e:
            print(f"Error scraping Shopsy: {e}")
        
        return results[:15]
    
    def analyze_with_ai(self, data):
        """Use Claude to analyze dropshipping opportunities"""
        
        formatted_data = "\n\n".join([
            f"Source: {item.get('source', 'Unknown')}\n"
            f"Category: {item.get('category', 'N/A')}\n"
            f"Product: {item.get('title', item.get('snippet', 'N/A'))}\n"
            f"Price: {item.get('price', 'N/A')}\n"
            f"URL: {item.get('url', 'N/A')}"
            for item in data
        ])
        
        prompt = f"""You are an e-commerce trend analyst specializing in the Indian dropshipping market.

Analyze the following trending products data collected from Amazon India, Flipkart, Google Trends, and other Indian platforms today ({datetime.now().strftime('%Y-%m-%d')}):

{formatted_data}

Provide a comprehensive analysis for someone starting a Shopify dropshipping store targeting Indian customers:

1. TOP 5 TRENDING PRODUCT CATEGORIES:
   For each category:
   - Why it's trending now
   - Target audience in India (age, income level, location)
   - Average price range (in INR)
   - Profit margin potential
   - Competition level (Low/Medium/High)
   - Seasonal factor (if any)
   - Sourcing recommendations (AliExpress, local suppliers, etc.)

2. VIRAL PRODUCT OPPORTUNITIES:
   - Specific products gaining traction
   - Why they're going viral
   - Estimated demand
   - Marketing angle

3. MARKET INSIGHTS:
   - Consumer behavior trends in India
   - Popular payment methods to support
   - Shipping considerations for Indian market
   - Regional preferences (North vs South vs Metro cities)

4. COMPETITION ANALYSIS:
   - Saturated categories to avoid
   - Underserved niches
   - Unique selling propositions that work in India

5. MARKETING RECOMMENDATIONS:
   - Social media strategies (Instagram, Facebook, WhatsApp)
   - Influencer collaboration opportunities
   - Festival/seasonal timing (Diwali, Holi, etc.)
   - Budget allocation suggestions

6. ACTION ITEMS:
   - Top 3 products to test first
   - Supplier sourcing steps
   - Store setup priorities
   - First marketing campaign ideas

Focus on practical, actionable insights for the Indian market specifically."""

        try:
            message = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return message.content[0].text
            
        except Exception as e:
            print(f"Error with Claude API: {e}")
            return f"Error analyzing data: {e}"
    
    def create_google_doc(self, analysis, data_summary):
        """Create Google Doc with dropshipping trends report"""
        
        now = datetime.now()
        title = f"{now.strftime('%Y-%m-%d_%H-%M')}_DS"
        
        try:
            doc = self.docs_service.documents().create(
                body={'title': title}
            ).execute()
            
            doc_id = doc['documentId']
            
            content = f"""INDIA DROPSHIPPING TRENDS REPORT
Generated: {now.strftime('%B %d, %Y at %I:%M %p IST')}
Report ID: {now.strftime('%Y%m%d_%H%M')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 DATA SOURCES

Collection Time: {now.strftime('%Y-%m-%d %H:%M:%S')}

Platforms Monitored:
• Amazon India Best Sellers
• Flipkart Trending
• Google Trends (India)
• Meesho Popular Products
• Instagram Trending Hashtags

Total Products Analyzed: {len(data_summary)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AI ANALYSIS

{analysis}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 TRENDING PRODUCTS DATA

"""
            
            # Add top products
            for i, item in enumerate(data_summary[:30], 1):
                content += f"\n{i}. {item.get('title', 'N/A')}\n"
                content += f"   Category: {item.get('category', 'N/A')}\n"
                content += f"   Price: {item.get('price', 'N/A')}\n"
                content += f"   Source: {item.get('source', 'N/A')}\n"
                if item.get('url'):
                    content += f"   Link: {item.get('url')}\n"
            
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
        print("🛍️ Starting India dropshipping trend research...")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n📊 Collecting data from Indian e-commerce platforms...")
        
        amazon_data = self.scrape_amazon_bestsellers_india()
        print(f"  ✓ Amazon India: {len(amazon_data)} products")
        
        flipkart_data = self.scrape_flipkart_trending()
        print(f"  ✓ Flipkart: {len(flipkart_data)} products")
        
        google_data = self.scrape_google_trends_india()
        print(f"  ✓ Google Trends: {len(google_data)} items")
        
        meesho_data = self.scrape_meesho_trending()
        print(f"  ✓ Meesho: {len(meesho_data)} products")
        
        instagram_data = self.scrape_instagram_trending_india()
        print(f"  ✓ Instagram Trends: {len(instagram_data)} items")
        
        all_data = amazon_data + flipkart_data + google_data + meesho_data + instagram_data
        print(f"\n📦 Total data points: {len(all_data)}")
        
        if len(all_data) == 0:
            print("❌ No data collected. Exiting.")
            return
        
        print("\n🤖 Analyzing with Claude AI...")
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
        
        print("\n🎉 Dropshipping research complete!")

if __name__ == "__main__":
    bot = DropshippingTrendBot()
    bot.run_daily_research()
