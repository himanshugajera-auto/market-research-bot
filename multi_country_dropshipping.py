"""
Multi-Country Dropshipping Product Trend Finder with Scoring
Saves scored products to Google Sheets for dashboard review
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
import re

class MultiCountryDropshippingBot:
    def __init__(self):
        self.claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        # Google APIs
        creds = Credentials.from_authorized_user_info(
            json.loads(os.getenv("GOOGLE_CREDENTIALS"))
        )
        self.docs_service = build('docs', 'v1', credentials=creds)
        self.sheets_service = build('sheets', 'v4', credentials=creds)
        self.drive_service = build('drive', 'v3', credentials=creds)
        
        # Google Sheet ID for product database
        self.sheet_id = os.getenv("PRODUCT_SHEET_ID", "")
        
        # Safe categories
        self.safe_categories = [
            'home-garden', 'kitchen', 'sports-fitness',
            'pet-supplies', 'baby-products', 'arts-crafts',
            'tools-home-improvement', 'automotive-accessories'
        ]
    
    def scrape_google_trends_by_country(self):
        """Get Google Shopping trends with product details"""
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
            "trending home decor 2025",
            "viral kitchen gadgets",
            "best fitness accessories",
            "popular pet products 2025",
            "trending baby products"
        ]
        
        for country_code, country_name in countries.items():
            for query in safe_queries:
                try:
                    response = requests.post(
                        'https://google.serper.dev/search',
                        headers={'X-API-KEY': serper_key},
                        json={
                            'q': query,
                            'gl': country_code,
                            'num': 10
                        },
                        timeout=10
                    )
                    data = response.json()
                    
                    for item in data.get('organic', [])[:3]:
                        # Try to extract product info
                        title = item.get('title', '')
                        snippet = item.get('snippet', '')
                        
                        # Look for price in snippet
                        price_match = re.search(r'\$(\d+\.?\d*)', snippet)
                        price = price_match.group(0) if price_match else 'N/A'
                        
                        results.append({
                            'source': f'Google Trends ({country_name})',
                            'country': country_name,
                            'category': self._extract_category(query),
                            'product_name': title,
                            'description': snippet[:200],
                            'price': price,
                            'url': item.get('link'),
                            'image_url': item.get('imageUrl', ''),
                            'timestamp': datetime.now().isoformat()
                        })
                        
                except Exception as e:
                    print(f"Error with Serper API for {country_name}: {e}")
        
        return results
    
    def scrape_aliexpress_products(self):
        """Search AliExpress for dropshipping products with details"""
        results = []
        serper_key = os.getenv("SERPER_API_KEY")
        
        if not serper_key:
            return results
        
        queries = [
            "site:aliexpress.com trending home decor",
            "site:aliexpress.com kitchen gadgets bestseller",
            "site:aliexpress.com fitness accessories"
        ]
        
        for query in queries:
            try:
                response = requests.post(
                    'https://google.serper.dev/search',
                    headers={'X-API-KEY': serper_key},
                    json={'q': query, 'num': 5},
                    timeout=10
                )
                data = response.json()
                
                for item in data.get('organic', []):
                    results.append({
                        'source': 'AliExpress',
                        'country': 'Global',
                        'category': self._extract_category(query),
                        'product_name': item.get('title'),
                        'description': item.get('snippet', '')[:200],
                        'supplier_link': item.get('link'),
                        'url': item.get('link'),
                        'timestamp': datetime.now().isoformat()
                    })
                    
            except Exception as e:
                print(f"Error searching AliExpress: {e}")
        
        return results
    
    def _extract_category(self, text):
        """Extract category from search query"""
        text_lower = text.lower()
        if 'home' in text_lower or 'decor' in text_lower:
            return 'Home & Garden'
        elif 'kitchen' in text_lower:
            return 'Kitchen'
        elif 'fitness' in text_lower or 'sports' in text_lower:
            return 'Fitness'
        elif 'pet' in text_lower:
            return 'Pet Supplies'
        elif 'baby' in text_lower:
            return 'Baby Products'
        else:
            return 'Other'
    
    def score_products_with_ai(self, products):
        """Use Claude to score each product opportunity"""
        scored_products = []
        
        # Process in batches to avoid token limits
        batch_size = 10
        for i in range(0, len(products), batch_size):
            batch = products[i:i+batch_size]
            
            formatted_batch = "\n\n".join([
                f"Product {idx}: {p.get('product_name', 'N/A')}\n"
                f"Category: {p.get('category', 'N/A')}\n"
                f"Country: {p.get('country', 'N/A')}\n"
                f"Description: {p.get('description', 'N/A')}\n"
                f"Price: {p.get('price', 'N/A')}"
                for idx, p in enumerate(batch, 1)
            ])
            
            prompt = f"""Score these dropshipping product opportunities on a scale of 0-100.

Products to analyze:
{formatted_batch}

For each product, provide scores in this EXACT format:
Product X:
- Overall Score: [0-100]
- Demand Score: [0-100] (trending, search volume potential)
- Competition Score: [0-100] (lower = less competition, better)
- Margin Score: [0-100] (profit potential)
- Legal Risk Score: [0-100] (lower = safer, avoid branded/electronics)
- Reasoning: [One sentence why this score]

IMPORTANT:
- Heavily penalize electronics, branded items, trademarked products
- Favor unique, non-branded items in safe categories
- Consider target country's market
- Be critical and realistic"""

            try:
                message = self.claude.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                analysis = message.content[0].text
                scores = self._parse_scores(analysis, batch)
                scored_products.extend(scores)
                
            except Exception as e:
                print(f"Error scoring batch: {e}")
                # Add products without scores
                for p in batch:
                    p['overall_score'] = 0
                    p['demand_score'] = 0
                    p['competition_score'] = 0
                    p['margin_score'] = 0
                    p['legal_risk_score'] = 50
                    p['score_reasoning'] = 'Scoring failed'
                    scored_products.append(p)
        
        return scored_products
    
    def _parse_scores(self, analysis, products):
        """Parse Claude's scoring response"""
        scored = []
        lines = analysis.split('\n')
        
        current_product_idx = -1
        current_scores = {}
        
        for line in lines:
            line = line.strip()
            
            # Detect product number
            if line.startswith('Product '):
                if current_product_idx >= 0 and current_scores:
                    # Save previous product
                    if current_product_idx < len(products):
                        products[current_product_idx].update(current_scores)
                        scored.append(products[current_product_idx])
                
                # Start new product
                match = re.search(r'Product (\d+)', line)
                if match:
                    current_product_idx = int(match.group(1)) - 1
                    current_scores = {}
            
            # Extract scores
            if 'Overall Score:' in line:
                score = re.search(r'(\d+)', line)
                if score:
                    current_scores['overall_score'] = int(score.group(1))
            elif 'Demand Score:' in line:
                score = re.search(r'(\d+)', line)
                if score:
                    current_scores['demand_score'] = int(score.group(1))
            elif 'Competition Score:' in line:
                score = re.search(r'(\d+)', line)
                if score:
                    current_scores['competition_score'] = int(score.group(1))
            elif 'Margin Score:' in line:
                score = re.search(r'(\d+)', line)
                if score:
                    current_scores['margin_score'] = int(score.group(1))
            elif 'Legal Risk Score:' in line:
                score = re.search(r'(\d+)', line)
                if score:
                    current_scores['legal_risk_score'] = int(score.group(1))
            elif 'Reasoning:' in line:
                reasoning = line.replace('Reasoning:', '').strip()
                current_scores['score_reasoning'] = reasoning
        
        # Save last product
        if current_product_idx >= 0 and current_scores and current_product_idx < len(products):
            products[current_product_idx].update(current_scores)
            scored.append(products[current_product_idx])
        
        return scored
    
    def save_to_google_sheets(self, products):
        """Save scored products to Google Sheets database"""
        if not self.sheet_id:
            print("  No Google Sheet ID configured, skipping save")
            return
        
        try:
            # Prepare rows
            rows = []
            for p in products:
                row = [
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    p.get('product_name', ''),
                    p.get('category', ''),
                    p.get('country', ''),
                    p.get('overall_score', 0),
                    p.get('demand_score', 0),
                    p.get('competition_score', 0),
                    p.get('margin_score', 0),
                    p.get('legal_risk_score', 0),
                    p.get('price', 'N/A'),
                    p.get('supplier_link', p.get('url', '')),
                    p.get('image_url', ''),
                    p.get('description', ''),
                    p.get('score_reasoning', ''),
                    'pending',  # status
                    ''  # notes
                ]
                rows.append(row)
            
            # Append to sheet
            body = {'values': rows}
            self.sheets_service.spreadsheets().values().append(
                spreadsheetId=self.sheet_id,
                range='Products!A:P',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"  Saved {len(rows)} products to Google Sheets")
            
        except Exception as e:
            print(f"  Error saving to Google Sheets: {e}")
    
    def create_google_doc_report(self, products):
        """Create summary Google Doc"""
        now = datetime.now()
        title = f"{now.strftime('%Y-%m-%d_%H-%M')}_DS_MULTI"
        
        try:
            doc = self.docs_service.documents().create(
                body={'title': title}
            ).execute()
            
            doc_id = doc['documentId']
            
            # Sort by score
            sorted_products = sorted(products, key=lambda x: x.get('overall_score', 0), reverse=True)
            
            content = f"""MULTI-COUNTRY DROPSHIPPING OPPORTUNITIES
Generated: {now.strftime('%B %d, %Y at %I:%M %p UTC')}
Report ID: {now.strftime('%Y%m%d_%H%M')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 SUMMARY

Total Products Analyzed: {len(products)}
Products with Score > 70: {len([p for p in products if p.get('overall_score', 0) > 70])}
Products with Score 50-70: {len([p for p in products if 50 <= p.get('overall_score', 0) <= 70])}

Top 3 Opportunities:
"""
            
            for i, p in enumerate(sorted_products[:3], 1):
                content += f"\n{i}. {p.get('product_name', 'N/A')} (Score: {p.get('overall_score', 0)})\n"
                content += f"   Country: {p.get('country', 'N/A')} | Category: {p.get('category', 'N/A')}\n"
            
            content += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            content += "TOP 10 SCORED PRODUCTS\n\n"
            
            for i, p in enumerate(sorted_products[:10], 1):
                content += f"{i}. {p.get('product_name', 'N/A')}\n"
                content += f"   Overall Score: {p.get('overall_score', 0)}/100\n"
                content += f"   Demand: {p.get('demand_score', 0)} | Competition: {p.get('competition_score', 0)} | Margin: {p.get('margin_score', 0)}\n"
                content += f"   Legal Risk: {p.get('legal_risk_score', 0)} (lower is safer)\n"
                content += f"   Country: {p.get('country', 'N/A')} | Category: {p.get('category', 'N/A')}\n"
                content += f"   Price: {p.get('price', 'N/A')}\n"
                content += f"   Reasoning: {p.get('score_reasoning', 'N/A')}\n"
                if p.get('supplier_link'):
                    content += f"   Supplier: {p.get('supplier_link')}\n"
                content += "\n"
            
            content += "\n\nView all products in the dashboard to approve/reject for your Shopify store.\n"
            
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
            
            print(f"  Report created: https://docs.google.com/document/d/{doc_id}/edit")
            return doc_id
            
        except HttpError as e:
            print(f"  Error creating Google Doc: {e}")
            return None
    
    def run_daily_research(self):
        """Main execution"""
        print("🌍 Starting multi-country dropshipping research with scoring...")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n📊 Collecting product data...")
        
        google_data = self.scrape_google_trends_by_country()
        print(f"  ✓ Google Trends: {len(google_data)} items")
        
        aliexpress_data = self.scrape_aliexpress_products()
        print(f"  ✓ AliExpress: {len(aliexpress_data)} items")
        
        all_products = google_data + aliexpress_data
        print(f"\n📦 Total products collected: {len(all_products)}")
        
        if len(all_products) == 0:
            print("❌ No data collected. Exiting.")
            return
        
        print("\n🤖 Scoring products with Claude AI...")
        scored_products = self.score_products_with_ai(all_products)
        print(f"  ✓ Scored {len(scored_products)} products")
        
        print("\n💾 Saving to Google Sheets...")
        self.save_to_google_sheets(scored_products)
        
        print("\n📝 Creating summary report...")
        doc_id = self.create_google_doc_report(scored_products)
        
        print("\n✅ Research complete!")
        print(f"   Products saved to Google Sheets")
        print(f"   Open dashboard to review and approve products")

if __name__ == "__main__":
    bot = MultiCountryDropshippingBot()
    bot.run_daily_research()
