# TDS Virtual Teaching Assistant API

A FastAPI-based virtual teaching assistant designed for the Tools in Data Science (TDS) course at IIT Madras' Online Degree in Data Science. The application answers student questions by leveraging course content from GitHub and Discourse posts, using OpenAI's `gpt-3.5-turbo-0125` for intelligent responses. It supports base64-encoded image attachments with OCR processing and provides structured JSON responses with relevant links.

## Features

1. **Automated Content Scraping**:
   - Scrapes course content from the GitHub repository `https://github.com/sanand0/tools-in-data-science-public`.
   - Scrapes Discourse posts from `https://discourse.onlinedegree.iitm.ac.in` for the period January 1, 2025–April 14, 2025, using provided credentials.
2. **LLM-Powered Q&A**:
   - Uses OpenAI's `gpt-3.5-turbo-0125` to generate accurate and educational answers based on scraped content.
3. **Structured Response Format**:
   - Returns JSON responses with an `answer` and a list of `links` (each with `url` and `text`).
4. **Image Support**:
   - Processes base64-encoded images using Tesseract OCR to extract text, enhancing context for questions referencing screenshots.
5. **Fast Response Times**:
   - Optimized to respond within 30 seconds by limiting context size and tokens.
6. **RESTful API**:
   - Exposes a clean JSON API at `/api/` for POST requests, with additional health check endpoints (`/` and `/health`).
7. **Dockerized Deployment**:
   - Includes a `Dockerfile` and `docker-compose.yml` for easy local and cloud deployment.
8. **Secure Credential Handling**:
   - Uses a `.env` file for sensitive data like `OPENAI_API_KEY`, `DISCOURSE_USERNAME`, and `DISCOURSE_PASSWORD`.

## Project Structure
