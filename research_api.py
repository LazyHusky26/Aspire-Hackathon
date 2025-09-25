import os
import asyncio
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import aiohttp
import urllib.parse
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="AI Research Agent API")

# CORS configuration - same origins as resume parser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Initialize Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

class ResearchRequest(BaseModel):
    question: str

class ResearchResponse(BaseModel):
    question: str
    report: str
    sources: list
    timestamp: str

class SimpleResearcher:
    async def search_duckduckgo(self, query):
        """Search using DuckDuckGo instant answers API"""
        url = "https://api.duckduckgo.com/"
        params = {
            'q': query,
            'format': 'json',
            'no_html': '1',
            'skip_disambig': '1'
        }
        
        results = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Get abstract if available
                        if data.get('Abstract'):
                            results.append({
                                'title': data.get('Heading', query),
                                'url': data.get('AbstractURL', ''),
                                'snippet': data.get('Abstract', '')
                            })
                        
                        # Get related topics
                        for topic in data.get('RelatedTopics', [])[:3]:
                            if isinstance(topic, dict) and topic.get('FirstURL'):
                                results.append({
                                    'title': topic.get('Text', '').split(' - ')[0],
                                    'url': topic.get('FirstURL', ''),
                                    'snippet': topic.get('Text', '')
                                })
        except Exception as e:
            print(f"DuckDuckGo error: {e}")
        
        return results

    async def search_reliable_sites(self, query):
        """Search specific reliable sites directly"""
        encoded_query = urllib.parse.quote_plus(query)
        
        search_urls = [
            f"https://en.wikipedia.org/wiki/Special:Search?search={encoded_query}",
            f"https://www.bbc.com/search?q={encoded_query}",
        ]
        
        results = []
        for url in search_urls[:2]:
            try:
                content = await self.get_content(url)
                if content and len(content) > 200:
                    site_name = url.split('/')[2].replace('www.', '').replace('.com', '').title()
                    results.append({
                        'title': f"{query} - {site_name}",
                        'url': url,
                        'snippet': content[:200] + "..."
                    })
            except Exception:
                continue
        
        return results

    async def get_content(self, url):
        """Get content from a webpage"""
        if not url:
            return ""
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Remove unwanted elements
                        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                            element.decompose()
                        
                        # Try to find main content
                        main_selectors = ['main', 'article', '.content', '.post-content']
                        content_text = ""
                        
                        for selector in main_selectors:
                            main_content = soup.select_one(selector)
                            if main_content:
                                content_text = main_content.get_text()
                                break
                        
                        if not content_text:
                            body = soup.find('body')
                            if body:
                                content_text = body.get_text()
                        
                        # Clean up text
                        lines = [line.strip() for line in content_text.splitlines() if line.strip()]
                        content = ' '.join(lines)
                        
                        if len(content) > 4000:
                            content = content[:4000] + "..."
                        
                        return content
        except Exception:
            return ""

    def ask_gemini(self, prompt):
        """Ask Gemini a question"""
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Gemini error: {e}")
            return "Sorry, I couldn't generate a response."

    async def research_question(self, question):
        """Research a question and provide a comprehensive answer"""
        
        # Step 1: Break down the question
        breakdown_prompt = f"""
        Break down this research question into 3-4 specific, searchable sub-questions:
        "{question}"
        
        Return just the sub-questions, one per line, without numbering.
        Make them specific and good for web search.
        """
        
        sub_questions = self.ask_gemini(breakdown_prompt).strip().split('\n')
        sub_questions = [q.strip('- ').strip() for q in sub_questions if q.strip()]
        
        # Step 2: Research each sub-question
        all_content = []
        all_sources = []
        
        for sub_q in sub_questions[:3]:
            # Search DuckDuckGo
            ddg_results = await self.search_duckduckgo(sub_q)
            
            # Search reliable sites if needed
            if len(ddg_results) < 2:
                site_results = await self.search_reliable_sites(sub_q)
                ddg_results.extend(site_results)
            
            for result in ddg_results[:2]:
                if result['url']:
                    content = await self.get_content(result['url'])
                    if content and len(content) > 100:
                        all_content.append({
                            'question': sub_q,
                            'content': content,
                            'url': result['url'],
                            'title': result['title']
                        })
                        all_sources.append(result['url'])
                else:
                    if result['snippet'] and len(result['snippet']) > 50:
                        all_content.append({
                            'question': sub_q,
                            'content': result['snippet'],
                            'url': 'Direct Answer',
                            'title': result['title']
                        })
        
        # Step 3: Generate comprehensive answer
        if not all_content:
            # Fallback: Use Gemini's knowledge directly
            direct_prompt = f"""
            Please provide a comprehensive answer to this question based on your knowledge:
            "{question}"
            
            Include:
            - Key facts and information
            - Recent developments (if applicable)
            - Different perspectives or viewpoints
            - Practical implications
            
            Structure your response with clear headings and bullet points.
            """
            return self.ask_gemini(direct_prompt), []
        
        # Prepare content for analysis
        research_data = ""
        for item in all_content:
            research_data += f"\nSource: {item['title']} ({item['url']})\n"
            research_data += f"Content: {item['content'][:1500]}...\n"
            research_data += "---\n"
        
        # Generate final report
        report_prompt = f"""
        Based on the research data below, write a comprehensive answer to this question:
        "{question}"
        
        Requirements:
        1. Write a clear, well-structured response
        2. Include specific facts and data points from the sources
        3. Provide actionable insights
        4. Use markdown formatting for better readability
        5. Structure with headers and bullet points where appropriate
        
        Research Data:
        {research_data[:12000]}
        
        Write a thorough research report:
        """
        
        report = self.ask_gemini(report_prompt)
        
        # Get unique sources
        unique_sources = list(set([s for s in all_sources if s != 'Direct Answer']))
        
        return report, unique_sources

# Initialize researcher
researcher = SimpleResearcher()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/research", response_model=ResearchResponse)
async def research_endpoint(request: ResearchRequest):
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        report, sources = await researcher.research_question(request.question)
        
        return ResearchResponse(
            question=request.question,
            report=report,
            sources=sources,
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Research failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)