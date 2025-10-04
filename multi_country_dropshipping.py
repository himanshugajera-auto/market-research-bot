"""
Enhanced Multi-Country Dropshipping Bot v2
- Parses trend articles to extract product names
- Searches Amazon for actual products + prices
- Searches AliExpress for supplier costs
- Calculates profit margins
- Saves only profitable products
"""

import os
import json
from datetime import datetime
import anthropic
import requests
from bs4 import BeautifulSoup
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import re
import time

class EnhancedDropshippingBot:
    def __init__(self):
        self.claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        # Google APIs - service account
        credentials_dict = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT"))
        creds = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/documents',
                'https://www.googleapis.com/auth/drive.file'
            ]
        )
        self.docs_service = build('docs', 'v1', credentials=creds)
        self.sheets_service = build('sheets', 'v4', credentials=creds)
        self.drive_service = build('drive', 'v3', credentials=creds)
        
        self.sheet_id = os.getenv("PRODUCT_SHEET_ID", "")
        self.serper_key = os.getenv("SERPER_API_KEY")
        
        # Safe categories
        self.safe_categories = [
            'home decor', 'kitchen', 'fitness', 'pet supplies',
            'baby products', 'jewelry', 'phone accessories'
        ]
    
    def find_trend_articles(self):
        """Find trending product articles"""
        results = []
        
        if not self.serper_key:
            print("  No Serper API key")
            return results
        
        countries = {
            'us': 'USA',
            'au': 'Australia',
            'ae': 'UAE',
            'sa': 'Saudi Arabia'
        }
        
        queries = [
            "trending products 2025",
            "viral products right now",
            "best selling products 2025",
            "hot products to sell",
            "trending pet products",
            "trending home decor",
            "trending kitchen gadgets"
        ]
        
        for country_code, country_name in countries.items():
            for query in queries[:2]:  # Limit to save API credits
                try:
                    response = requests.post(
                        'https://google.serper.dev/search',
                        headers={'X-API-KEY': self.serper_key},
                        json={'q': query, 'gl': country_code, 'num': 5},
                        timeout=10
                    )
                    data = response.json()
                    
                    for item in data.get('organic', [])[:2]:
                        results.append({
                            'url': item.get('link'),
                            'title': item.get('title'),
                            'snippet': item.get('snippet', ''),
                            'country': country_name
                        })
                    
                    time.sleep(0.5)  # Rate limiting
                    
                except Exception as e:
                    print(f"Error finding articles for {country_name}: {e}")
        
        return results[:20]  # Limit total articles
    
    def parse_article_for_products(self, article_url):
        """Extract product names from article"""
        try:
            response = requests.get(article_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }, timeout=10)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get article text
            article_text = soup.get_text()
            
            # Use Claude to extract product names
            prompt = f"""Extract product names from this article about trending products.

Article text (first 3000 chars):
{article_text[:3000]}

Return ONLY a Python list of product names, like:
["Product Name 1", "Product Name 2", "Product Name 3"]

Focus on actual product names, not categories. Max 10 products."""

            message = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text.strip()
            
            # Parse the list
            try:
                # Remove markdown code blocks if present
                if '```' in response_text:
                    response_text = response_text.split('```')[1]
                    if response_text.startswith('python'):
                        response_text = response_text[6:]
                
                products = eval(response_text.strip())
                return products if isinstance(products, list) else []
            except:
                return []
                
        except Exception as e:
            print(f"Error parsing article: {e}")
            return []
    
    def search_amazon_product(self, product_name, country_code='us'):
        """Search Amazon for product and get price"""
        if not self.serper_key:
            return None
        
        try:
            # Amazon domain mapping
            domains = {
                'us': 'amazon.com',
                'au': 'amazon.com.au',
                'ae': 'amazon.ae',
                'sa': 'amazon.sa'
            }
            
            domain = domains.get(country_code, 'amazon.com')
            query = f"site:{domain} {product_name}"
            
            response = requests.post(
                'https://google.serper.dev/search',
                headers={'X-API-KEY': self.serper_key},
                json={'q': query, 'gl': country_code, 'num': 3},
                timeout=10
            )
            data = response.json()
            
            for item in data.get('organic', []):
                link = item.get('link', '')
                if domain in link and '/dp/' in link:
                    # Extract price from snippet
                    snippet = item.get('snippet', '')
                    title = item.get('title', '')
                    
                    # Look for price patterns
                    price_patterns = [
                        r'\$(\d+\.?\d*)',  # $19.99
                        r'(\d+\.?\d*)\s*USD',  # 19.99 USD
                        r'AED\s*(\d+\.?\d*)',  # AED 50
                        r'SAR\s*(\d+\.?\d*)',  # SAR 75
                    ]
                    
                    price = None
                    for pattern in price_patterns:
                        match = re.search(pattern, snippet + ' ' + title)
                        if match:
                            price = float(match.group(1))
                            break
                    
                    if price:
                        return {
                            'product_name': title.split('|')[0].strip()[:100],
                            'amazon_price': price,
                            'amazon_url': link,
                            'country_code': country_code
                        }
            
            time.sleep(0.5)  # Rate limiting
            return None
            
        except Exception as e:
            print(f"Error searching Amazon: {e}")
            return None
    
    def search_aliexpress_supplier(self, product_name):
        """Search AliExpress for supplier cost"""
        if not self.serper_key:
            return None
        
        try:
            query = f"site:aliexpress.com {product_name}"
            
            response = requests.post(
                'https://google.serper.dev/search',
                headers={'X-API-KEY': self.serper_key},
                json={'q': query, 'num': 3},
                timeout=10
            )
            data = response.json()
            
            for item in data.get('organic', []):
                link = item.get('link', '')
                if 'aliexpress.com' in link:
                    snippet = item.get('snippet', '')
                    title = item.get('title', '')
                    
                    # Look for price
                    price_patterns = [
                        r'\$(\d+\.?\d*)',
                        r'(\d+\.?\d*)\s*USD',
                        r'US\s*\$(\d+\.?\d*)'
                    ]
                    
                    for pattern in price_patterns:
                        match = re.search(pattern, snippet + ' ' + title)
                        if match:
                            price = float(match.group(1))
                            return {
                                'supplier_price': price,
                                'supplier_url': link
                            }
            
            time.sleep(0.5)  # Rate limiting
            return None
            
        except Exception as e:
            print(f"Error searching AliExpress: {e}")
            return None
    
    def calculate_margins(self, amazon_price, supplier_price):
        """Calculate profit margins"""
        # Estimate costs
        shipping_cost = 5.0  # Average shipping
        transaction_fee = amazon_price * 0.03  # 3% payment processing
        
        total_cost = supplier_price + shipping_cost + transaction_fee
        profit = amazon_price - total_cost
        margin_percent = (profit / amazon_price * 100) if amazon_price > 0 else 0
        
        return {
            'profit': round(profit, 2),
            'margin_percent': round(margin_percent, 2),
            'total_cost': round(total_cost, 2),
            'recommended_price': round(amazon_price * 0.9, 2)  # Undercut by 10%
        }
    
    def score_product_opportunity(self, product_data):
        """Score the dropshipping opportunity"""
        margin = product_data.get('margin_percent', 0)
        profit = product_data.get('profit', 0)
        amazon_price = product_data.get('amazon_price', 0)
        
        # Scoring logic
        score = 0
        
        # Margin score (max 40 points)
        if margin >= 50:
            score += 40
        elif margin >= 40:
            score += 30
        elif margin >= 30:
            score += 20
        elif margin >= 20:
            score += 10
        
        # Profit amount score (max 30 points)
        if profit >= 30:
            score += 30
        elif profit >= 20:
            score += 20
        elif profit >= 10:
            score += 10
        
        # Price point score (max 30 points)
        # Sweet spot is $20-$80
        if 20 <= amazon_price <= 80:
            score += 30
        elif 10 <= amazon_price <= 100:
            score += 20
        elif amazon_price > 0:
            score += 10
        
        return min(score, 100)
    
    def process_products(self):
        """Main processing pipeline"""
        all_products = []
        
        print("\n📰 Finding trend articles...")
        articles = self.find_trend_articles()
        print(f"  Found {len(articles)} articles")
        
        for article in articles[:10]:  # Limit articles to process
            print(f"\n📄 Parsing: {article['title'][:60]}...")
            products = self.parse_article_for_products(article['url'])
            print(f"  Extracted {len(products)} product names")
            
            for product_name in products[:5]:  # Limit products per article
                print(f"\n  🔍 Researching: {product_name}")
                
                # Search Amazon
                amazon_data = self.search_amazon_product(product_name, 'us')
                if not amazon_data:
                    print(f"    ❌ No Amazon listing found")
                    continue
                
                print(f"    ✓ Amazon: ${amazon_data['amazon_price']}")
                
                # Search AliExpress
                supplier_data = self.search_aliexpress_supplier(product_name)
                if not supplier_data:
                    print(f"    ❌ No AliExpress supplier found")
                    continue
                
                print(f"    ✓ AliExpress: ${supplier_data['supplier_price']}")
                
                # Calculate margins
                margins = self.calculate_margins(
                    amazon_data['amazon_price'],
                    supplier_data['supplier_price']
                )
                
                print(f"    💰 Margin: {margins['margin_percent']}% (${margins['profit']} profit)")
                
                # Only keep if margin > 25%
                if margins['margin_percent'] < 25:
                    print(f"    ⚠️  Margin too low, skipping")
                    continue
                
                # Combine data
                product_data = {
                    **amazon_data,
                    **supplier_data,
                    **margins,
                    'source_article': article['title'],
                    'source_url': article['url'],
                    'country': article['country'],
                    'category': self._guess_category(product_name),
                    'timestamp': datetime.now().isoformat()
                }
                
                # Score it
                product_data['overall_score'] = self.score_product_opportunity(product_data)
                
                print(f"    ⭐ Score: {product_data['overall_score']}/100")
                
                all_products.append(product_data)
                
                time.sleep(1)  # Rate limiting between products
        
        return all_products
    
    def _guess_category(self, product_name):
        """Guess product category from name"""
        name_lower = product_name.lower()
        
        if any(word in name_lower for word in ['dog', 'cat', 'pet', 'collar', 'leash']):
            return 'Pet Supplies'
        elif any(word in name_lower for word in ['kitchen', 'cook', 'food', 'bowl']):
            return 'Kitchen'
        elif any(word in name_lower for word in ['home', 'decor', 'furniture', 'lamp']):
            return 'Home & Garden'
        elif any(word in name_lower for word in ['fitness', 'yoga', 'exercise', 'gym']):
            return 'Fitness'
        elif any(word in name_lower for word in ['baby', 'infant', 'toddler']):
            return 'Baby Products'
        else:
            return 'Other'
    
    def save_to_google_sheets(self, products):
        """Save profitable products to Google Sheets"""
        if not self.sheet_id or not products:
            print(f"  No products to save or sheet ID missing")
            return
        
        try:
            rows = []
            for p in products:
                row = [
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    p.get('product_name', ''),
                    p.get('category', ''),
                    p.get('country', 'USA'),
                    p.get('overall_score', 0),
                    int(p.get('margin_percent', 0)),  # demand_score = margin
                    0,  # competition_score (not calculated yet)
                    int(p.get('profit', 0)),  # margin_score = actual profit
                    20,  # legal_risk_score (safe products)
                    f"${p.get('amazon_price', 0)}",
                    p.get('supplier_url', ''),
                    '',  # image_url
                    f"Amazon: ${p.get('amazon_price', 0)} | Supplier: ${p.get('supplier_price', 0)} | Profit: ${p.get('profit', 0)} ({p.get('margin_percent', 0)}% margin)",
                    f"From: {p.get('source_article', 'Unknown')}. Recommended sell price: ${p.get('recommended_price', 0)}",
                    'pending',
                    ''
                ]
                rows.append(row)
            
            body = {'values': rows}
            self.sheets_service.spreadsheets().values().append(
                spreadsheetId=self.sheet_id,
                range='Products!A:P',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"\n✅ Saved {len(rows)} profitable products to Google Sheets")
            
        except Exception as e:
            print(f"\n❌ Error saving to Sheets: {e}")
    
    def run_daily_research(self):
        """Main execution"""
        print("=" * 60)
        print("🚀 ENHANCED DROPSHIPPING RESEARCH BOT v2")
        print("=" * 60)
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        products = self.process_products()
        
        print("\n" + "=" * 60)
        print(f"📊 RESULTS SUMMARY")
        print("=" * 60)
        print(f"Total profitable products found: {len(products)}")
        
        if products:
            avg_margin = sum(p['margin_percent'] for p in products) / len(products)
            avg_profit = sum(p['profit'] for p in products) / len(products)
            print(f"Average margin: {avg_margin:.1f}%")
            print(f"Average profit: ${avg_profit:.2f}")
            
            print("\n💾 Saving to Google Sheets...")
            self.save_to_google_sheets(products)
        else:
            print("\n⚠️  No profitable products found this run")
            print("Try again later or adjust margin requirements")
        
        print("\n✅ Research complete!")
        print("Open dashboard to review products")

if __name__ == "__main__":
    bot = EnhancedDropshippingBot()
    bot.run_daily_research()
