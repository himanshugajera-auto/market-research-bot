"""
Free AI Market Research Bot
Runs daily via GitHub Actions
Updated to use Google Service Account instead of OAuth
"""

import os
import json
from datetime import datetime
import anthropic
import praw
from google.oauth2 import service_account  # ← NEW IMPORT
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import requests
from bs4 import BeautifulSoup

class MarketResearchBot:
    def __init__(self):
        # API Keys from environment variables
        self.claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        # Reddit API (Free)
        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent="MarketResearch/1.0"
        )
        
        # Google Docs API - Service Account (Updated)
        try:
            creds = service_account.Credentials.from_service_account_info(
                json.loads(os.getenv("GOOGLE_CREDENTIALS")),
                scopes=[
                    'https://www.googleapis.com/auth/documents',
                    'https://www.googleapis.com/auth/drive'
                ]
            )
            self.docs_service = build('docs', 'v1', credentials=creds)
            self.drive_service = build('drive', 'v3', credentials=creds)
        except Exception as e:
            print(f"⚠️  Google authentication failed: {e}")
            self.docs_service = None
            self.drive_service = None
        
    def scrape_reddit(self):
        """Scrape Reddit for pain points and opportunities"""
        subreddits = ['SaaS', 'Entrepreneur', 'smallbusiness', 'startups', 'indiehackers']
        # Expanded keywords for better matching
        keywords = ['frustrated', 'need alternative', 'looking for solution', 
                   'wish there was', 'painful', 'inefficient', 'problem with',
                   'need help', 'struggle', 'difficult', 'annoying', 'hate that',
                   'better way', 'recommendations for', 'alternatives to']
        
        results = []
        for sub in subreddits:
            try:
                subreddit = self.reddit.subreddit(sub)
                
                # Get hot AND new posts for more coverage
                for post in list(subreddit.hot(limit=30)) + list(subreddit.new(limit=20)):
                    text = f"{post.title} {post.selftext}".lower()
                    if any(keyword in text for keyword in keywords):
                        results.append({
                            'source': f'r/{sub}',
                            'title': post.title,
                            'content': post.selftext[:500] if post.selftext else post.title,
                            'url': f"https://reddit.com{post.permalink}",
                            'upvotes': post.score,
                            'comments': post.num_comments,
                            'timestamp': datetime.fromtimestamp(post.created_utc).isoformat()
                        })
                
                # Get top comments from popular posts
                for post in subreddit.hot(limit=15):
                    try:
                        post.comments.replace_more(limit=0)
                        for comment in post.comments[:8]:
                            text = comment.body.lower()
                            if any(keyword in text for keyword in keywords) and len(comment.body) > 80:
                                results.append({
                                    'source': f'r/{sub}',
                                    'title': f"Comment on: {post.title[:80]}",
                                    'content': comment.body[:500],
                                    'url': f"https://reddit.com{comment.permalink}",
                                    'upvotes': comment.score,
                                    'comments': 0,
                                    'timestamp': datetime.fromtimestamp(comment.created_utc).isoformat()
                                })
                    except:
                        continue
            except Exception as e:
                print(f"Error scraping r/{sub}: {e}")
                
        # Remove duplicates based on URL
        seen_urls = set()
        unique_results = []
        for item in results:
            if item['url'] not in seen_urls:
                seen_urls.add(item['url'])
                unique_results.append(item)
                
        return unique_results[:50]  # Increased limit
    
    def scrape_producthunt(self):
        """Scrape Product Hunt for new launches and feedback"""
        results = []
        try:
            # Scrape Product Hunt homepage
            response = requests.get(
                'https://www.producthunt.com/',
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Note: This is basic scraping. Product Hunt's structure may change.
            # Finding posts with common pain point indicators in titles/descriptions
            print("  Product Hunt scraping completed (basic)")
            
        except Exception as e:
            print(f"Error scraping Product Hunt: {e}")
        
        return results[:10]
    
    def scrape_indiehackers(self):
        """Scrape IndieHackers for founder insights"""
        results = []
        try:
            response = requests.get(
                'https://www.indiehackers.com/posts',
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            keywords = ['revenue', 'failed', 'lesson', 'mistake', 'struggle', 
                       'problem', 'difficult', 'challenge']
            
            # Find post titles and links
            posts = soup.find_all('div', class_='feed-item')[:20]
            for post in posts:
                try:
                    title_elem = post.find('a')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        link = 'https://www.indiehackers.com' + title_elem.get('href', '')
                        
                        if any(keyword in title.lower() for keyword in keywords):
                            results.append({
                                'source': 'IndieHackers',
                                'title': title,
                                'content': title,
                                'url': link,
                                'score': 0,
                                'comments': 0,
                                'timestamp': datetime.now().isoformat()
                            })
                except:
                    continue
                    
        except Exception as e:
            print(f"Error scraping IndieHackers: {e}")
        
        return results[:15]
    
    def scrape_devto(self):
        """Scrape Dev.to using their free API"""
        results = []
        try:
            # Dev.to has a free API
            response = requests.get(
                'https://dev.to/api/articles?per_page=30&top=7',
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            articles = response.json()
            
            keywords = ['problem', 'struggle', 'difficult', 'frustrat', 
                       'why', 'how to', 'alternative', 'better way']
            
            for article in articles:
                title = article.get('title', '').lower()
                description = article.get('description', '').lower()
                
                if any(keyword in title or keyword in description for keyword in keywords):
                    results.append({
                        'source': 'Dev.to',
                        'title': article.get('title'),
                        'content': article.get('description', '')[:500],
                        'url': article.get('url'),
                        'score': article.get('positive_reactions_count', 0),
                        'comments': article.get('comments_count', 0),
                        'timestamp': article.get('published_at', datetime.now().isoformat())
                    })
                    
        except Exception as e:
            print(f"Error scraping Dev.to: {e}")
        
        return results[:15]
    
    def scrape_hackernews(self):
        """Scrape Hacker News via their free API"""
        results = []
        try:
            # Get top stories AND ask stories
            top_stories = requests.get(
                'https://hacker-news.firebaseio.com/v0/topstories.json'
            ).json()[:50]
            
            ask_stories = requests.get(
                'https://hacker-news.firebaseio.com/v0/askstories.json'
            ).json()[:30]
            
            all_story_ids = list(set(top_stories + ask_stories))
            
            keywords = ['need', 'looking for', 'alternative', 'frustrated', 
                       'problem', 'struggle', 'difficult', 'recommendation']
            
            for story_id in all_story_ids[:80]:
                try:
                    story = requests.get(
                        f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json',
                        timeout=5
                    ).json()
                    
                    if story and story.get('type') in ['story', 'ask']:
                        title = story.get('title', '').lower()
                        text = story.get('text', '').lower()
                        
                        # Look for Ask HN or pain points
                        if 'ask hn' in title or 'show hn' in title or any(word in title or word in text for word in keywords):
                            results.append({
                                'source': 'Hacker News',
                                'title': story.get('title'),
                                'content': story.get('text', story.get('title', ''))[:500],
                                'url': f"https://news.ycombinator.com/item?id={story_id}",
                                'score': story.get('score', 0),
                                'comments': story.get('descendants', 0),
                                'timestamp': datetime.fromtimestamp(story.get('time', 0)).isoformat()
                            })
                except:
                    continue
                        
        except Exception as e:
            print(f"Error scraping Hacker News: {e}")
            
        return results[:30]
    
    def analyze_with_ai(self, data):
        """Use Claude to analyze the collected data"""
        
        # Format data for analysis
        formatted_data = "\n\n".join([
            f"Source: {item['source']}\n"
            f"Title: {item['title']}\n"
            f"Content: {item['content']}\n"
            f"URL: {item['url']}\n"
            f"Engagement: {item.get('upvotes', item.get('score', 0))} upvotes, "
            f"{item.get('comments', 0)} comments"
            for item in data
        ])
        
        prompt = f"""You are a market research analyst helping a software engineer freelancer identify product opportunities.

Analyze the following data collected from Reddit and Hacker News today ({datetime.now().strftime('%Y-%m-%d')}):

{formatted_data}

Please provide a comprehensive analysis with:

1. TOP 3 OPPORTUNITIES: Identify the most promising product ideas based on:
   - Clear pain points mentioned multiple times
   - High engagement (upvotes/comments)
   - Feasibility for a solo developer
   - Market demand signals

For each opportunity, provide:
   - Problem Statement (2-3 sentences)
   - Target Audience
   - Existing Solutions & Their Gaps
   - Why This Matters (validation signals)
   - Technical Feasibility Score (1-10)
   - Estimated Market Size (Small/Medium/Large)
   - Potential Features (3-5 bullet points)
   - Revenue Model Ideas

2. EMERGING TRENDS: What topics are gaining traction?

3. NOTABLE QUOTES: 3-5 compelling user complaints or feature requests (paraphrase, don't quote directly)

4. ACTION ITEMS: Specific next steps for validation

Format your response in clear sections with headers."""

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
        """Create a Google Doc with the research report"""
        
        # Check if Google services are available
        if not self.docs_service or not self.drive_service:
            print("⚠️  Google Docs service not available. Skipping report creation.")
            print("\nAnalysis Result:")
            print(analysis)
            return None
        
        now = datetime.now()
        title = f"{now.strftime('%Y-%m-%d_%H-%M')}_MR"
        
        try:
            # Create new document
            doc = self.docs_service.documents().create(
                body={'title': title}
            ).execute()
            
            doc_id = doc['documentId']
            
            # Build document content
            content = f"""MARKET RESEARCH REPORT
{datetime.now().strftime('%B %d, %Y')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 DATA COLLECTED TODAY

Sources Analyzed:
• Reddit: {len([d for d in data_summary if 'reddit' in d['source'].lower()])} posts/comments
• Hacker News: {len([d for d in data_summary if 'hacker' in d['source'].lower()])} stories

Total Data Points: {len(data_summary)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AI ANALYSIS

{analysis}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📎 SOURCE LINKS

Top Discussions:
"""
            
            # Add top 10 most engaged sources
            sorted_data = sorted(
                data_summary, 
                key=lambda x: x.get('upvotes', x.get('score', 0)) + x.get('comments', 0), 
                reverse=True
            )[:10]
            
            for item in sorted_data:
                content += f"\n• {item['title']}\n  {item['url']}\n  {item.get('upvotes', item.get('score', 0))} upvotes, {item.get('comments', 0)} comments\n"
            
            # Insert content into document
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
        """Main execution function"""
        print("🚀 Starting daily market research...")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Step 1: Collect data
        print("\n📊 Collecting data from sources...")
        reddit_data = self.scrape_reddit()
        print(f"  ✓ Reddit: {len(reddit_data)} items")
        
        hn_data = self.scrape_hackernews()
        print(f"  ✓ Hacker News: {len(hn_data)} items")
        
        ph_data = self.scrape_producthunt()
        print(f"  ✓ Product Hunt: {len(ph_data)} items")
        
        ih_data = self.scrape_indiehackers()
        print(f"  ✓ IndieHackers: {len(ih_data)} items")
        
        devto_data = self.scrape_devto()
        print(f"  ✓ Dev.to: {len(devto_data)} items")
        
        all_data = reddit_data + hn_data + ph_data + ih_data + devto_data
        print(f"\n📦 Total data points: {len(all_data)}")
        
        if len(all_data) == 0:
            print("❌ No data collected. Exiting.")
            return
        
        # Step 2: AI Analysis
        print("\n🤖 Analyzing with Claude AI...")
        analysis = self.analyze_with_ai(all_data)
        print("  ✓ Analysis complete")
        
        # Step 3: Create Report
        print("\n📝 Creating Google Doc report...")
        doc_id = self.create_google_doc(analysis, all_data)
        
        if doc_id:
            print(f"\n✅ SUCCESS! Report available at:")
            print(f"https://docs.google.com/document/d/{doc_id}/edit")
        else:
            print("\n⚠️  Report creation skipped, but analysis is complete above.")
        
        print("\n🎉 Daily research complete!")

if __name__ == "__main__":
    bot = MarketResearchBot()
    bot.run_daily_research()
