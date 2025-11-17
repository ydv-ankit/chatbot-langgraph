# Chatbot LangGraph

A full-stack chatbot application built with LangGraph, FastAPI, and Next.js that provides AI-powered conversations with web search capabilities.

## Features

- 🤖 AI-powered chat using OpenAI GPT-4o-mini
- 🔍 Web search integration via Tavily Search
- 💬 Streaming responses with real-time updates
- 💾 Conversation memory and checkpointing
- 🎨 Modern UI built with Next.js and Tailwind CSS

## Tech Stack

**Backend:**
- FastAPI
- LangGraph
- LangChain
- OpenAI
- Tavily Search

**Frontend:**
- Next.js 16
- React 19
- TypeScript
- Tailwind CSS

## Setup

### Backend

1. Navigate to the server directory:
```bash
cd server
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your API keys:
```
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
```

4. Run the server:
```bash
uvicorn app:app --reload
```

### Frontend

1. Navigate to the client directory:
```bash
cd client
```

2. Install dependencies:
```bash
npm install
```

3. Create a `.env.local` file:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

4. Run the development server:
```bash
npm run dev
```

## Usage

1. Start both the backend and frontend servers
2. Open your browser to `http://localhost:3000`
3. Start chatting! The bot can answer questions and search the web when needed

## Project Structure

```
chatbot-langgraph/
├── server/          # FastAPI backend with LangGraph
├── client/          # Next.js frontend
└── README.md
```

