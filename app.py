#!/usr/bin/env python3
"""
TDS Virtual Teaching Assistant API
A FastAPI application that answers student questions based on course content and Discourse posts.
"""

import os
import json
import base64
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any
import logging
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import openai
from openai import OpenAI
import tiktoken
from PIL import Image
import io
import pytesseract
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="TDS Virtual Teaching Assistant",
    description="API to answer student questions based on course content and Discourse posts",
    version="1.0.0"
)

# Add CORS middleware (restrict origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.onlinedegree.iitm.ac.in", "http://localhost:3000"],  # Adjust as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class QuestionRequest(BaseModel):
    question: str
    image: Optional[str] = None  # base64 encoded image

class LinkResponse(BaseModel):
    url: str
    text: str

class AnswerResponse(BaseModel):
    answer: str
    links: List[LinkResponse] = []

# Global variables for caching
course_content = {}
discourse_posts = {}
openai_client = None

def initialize_openai():
    """Initialize OpenAI client"""
    global openai_client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    openai_client = OpenAI(api_key=api_key)

class TDSQuestionAnswerer:
    """Main class for answering TDS questions using LLM extraction"""
    
    def __init__(self):
        self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoding.encode(text))
    
    def process_image(self, base64_string: str) -> str:
        """Extract text from base64-encoded image using OCR"""
        try:
            img_data = base64.b64decode(base64_string)
            img = Image.open(io.BytesIO(img_data))
            text = pytesseract.image_to_string(img)
            return text.strip() if text.strip() else "No text extracted from image"
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return "Error processing image"
    
    def create_context(self, question: str, course_content: Dict, discourse_posts: Dict, image_text: Optional[str] = None) -> str:
        """Create context from course content, discourse posts, and image text"""
        context_parts = []
        
        # Add image text if available
        if image_text:
            context_parts.append("=== IMAGE CONTENT ===")
            context_parts.append(image_text[:1000])  # Limit to 1000 characters
        
        # Add course content
        context_parts.append("\n=== COURSE CONTENT ===")
        for file_name, content_data in course_content.items():
            context_parts.append(f"\n## {content_data['title']}")
            context_parts.append(f"URL: {content_data['url']}")
            # Use raw_content for simplicity, truncate to avoid token limits
            content = content_data.get('raw_content', '')[:2000]
            context_parts.append(content)
        
        # Add discourse posts
        context_parts.append("\n\n=== DISCOURSE POSTS ===")
        for topic_id, topic_data in discourse_posts.items():
            context_parts.append(f"\n## {topic_data['title']}")
            context_parts.append(f"URL: {topic_data['url']}")
            for post in topic_data.get('posts', []):
                content = post['content'][:1000]  # Limit post length
                context_parts.append(f"Post #{post['post_number']}: {content}")
        
        return "\n".join(context_parts)
    
    async def answer_question(self, question: str, image_data: Optional[str] = None) -> AnswerResponse:
        """Answer a student question using LLM extraction"""
        try:
            # Process image if provided
            image_text = self.process_image(image_data) if image_data else None
            
            # Create context
            context = self.create_context(question, course_content, discourse_posts, image_text)
            if self.count_tokens(context) > 12000:  # Approximate token limit for gpt-3.5-turbo
                context = context[:12000]  # Truncate to avoid exceeding token limit
            
            # Prepare messages
            messages = [
                {
                    "role": "system",
                    "content": """You are a TDS (Tools in Data Science) Virtual Teaching Assistant. 
                    Answer student questions based on the provided course content, Discourse posts, and image text (if any).
                    
                    Rules:
                    1. Use only information from the provided context
                    2. Be helpful, educational, and concise
                    3. Include relevant URLs from the context in your answer
                    4. For coding questions, prefer the exact models/versions mentioned in the context (e.g., gpt-3.5-turbo-0125)
                    5. If unsure, state that no relevant information was found
                    6. Respond within 30 seconds
                    
                    Response format: Provide a clear answer and include relevant links if available."""
                },
                {
                    "role": "user", 
                    "content": f"Context:\n{context}\n\nQuestion: {question}"
                }
            ]
            
            # Make API call
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=messages,
                max_tokens=500,
                temperature=0.1
            )
            
            answer_text = response.choices[0].message.content
            
            # Extract links based on question keywords
            links = []
            question_lower = question.lower()
            for topic_id, topic_data in discourse_posts.items():
                if any(keyword in question_lower for keyword in ["gpt", "model", "api", "ga5"]):
                    for post in topic_data.get('posts', []):
                        links.append(LinkResponse(
                            url=f"{topic_data['url']}/{post['post_number']}",
                            text=post['content'][:100] + "..." if len(post['content']) > 100 else post['content']
                        ))
            
            return AnswerResponse(answer=answer_text, links=links[:3])  # Limit to 3 links
            
        except openai.OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

# Initialize components
answerer = TDSQuestionAnswerer()

@app.on_event("startup")
async def startup_event():
    """Initialize the application"""
    global course_content, discourse_posts
    
    try:
        # Initialize OpenAI
        initialize_openai()
        logger.info("OpenAI client initialized")
        
        # Load pre-scraped data
        data_dir = Path("data")
        course_file = data_dir / "course_content.json"
        discourse_file = data_dir / "discourse_posts.json"
        
        if course_file.exists():
            with open(course_file, 'r', encoding='utf-8') as f:
                course_content.update(json.load(f))
            logger.info(f"Loaded {len(course_content)} course files")
        else:
            logger.warning("course_content.json not found")
        
        if discourse_file.exists():
            with open(discourse_file, 'r', encoding='utf-8') as f:
                discourse_posts.update(json.load(f))
            logger.info(f"Loaded {len(discourse_posts)} discourse topics")
        else:
            logger.warning("discourse_posts.json not found")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        # Continue startup but log the error

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "TDS Virtual Teaching Assistant API",
        "status": "running",
        "course_content_loaded": len(course_content),
        "discourse_posts_loaded": len(discourse_posts)
    }

@app.post("/api/", response_model=AnswerResponse)
async def answer_question(request: QuestionRequest, background_tasks: BackgroundTasks) -> AnswerResponse:
    """Main API endpoint to answer student questions"""
    try:
        # Validate request
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        logger.info(f"Processing question: {request.question[:100]}...")
        
        # Answer the question
        response = await answerer.answer_question(request.question, request.image)
        
        logger.info("Question answered successfully")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "openai_configured": openai_client is not None,
        "course_content_count": len(course_content),
        "discourse_posts_count": len(discourse_posts)
    }

if __name__ == "__main__":
    # Load environment variables
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    # Run the server
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )