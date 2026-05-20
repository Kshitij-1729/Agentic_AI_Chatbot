# 🤖 Agentic AI Chatbot

An advanced multi-agent AI chatbot system built with **LangGraph**, **LangChain**, and **Flask**, inspired by modern AI assistants like ChatGPT and Claude. The system intelligently routes user queries to specialized AI agents using an agentic workflow architecture.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-Backend-lightgrey.svg)](https://flask.palletsprojects.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-green.svg)](https://www.langchain.com/langgraph)

---

## ✨ Features at a Glance

| Feature | Description |
|---|---|
| 🧠 Multi-Agent Routing | Dynamically routes queries to the right specialized agent |
| 📚 RAG / CRAG | Retrieval-Augmented Generation with document intelligence |
| 💬 Persistent Memory | Multi-session conversation history and context summarization |
| 🛠 Tool Integration | Web search, financial data, and custom retrieval pipelines |
| 🔗 Multi-LLM Support | OpenAI and Google Gemini via a modular provider layer |
| 🌐 RESTful API | Clean Flask-based API with full conversation management |

---

## 🧠 Agent Types

The chatbot uses a **LangGraph-based orchestration pipeline** where agents collaborate to resolve user tasks:

- **Retrieval Agent** — Contextual RAG / CRAG-based document Q&A
- **Blog Writer Agent** — AI-powered content and blog generation
- **Academic Assistant Agent** — Research and academic support
- **Travel Planner Agent** — Destination and itinerary planning
- **General Conversational Agent** — Open-ended multi-turn dialogue

---

## 🏗 Architecture

```
User Query
    ↓
Flask API Layer
    ↓
LangGraph Workflow
    ↓
Intent Analysis & Routing
    ↓
Specialized Agent Selection
    ↓
Tool Usage / Retrieval / Reasoning
    ↓
LLM Response Generation
    ↓
Database Memory Storage
    ↓
Final Response to User
```

---

## 📁 Project Structure

```
Agentic_AI_Chatbot/
│
├── agents/              # Multi-agent workflow logic
├── database/            # Database connection, schema & models
├── llm/                 # LLM provider abstraction layer
├── static/              # CSS, JavaScript, frontend assets
├── templates/           # HTML templates
├── tools/               # RAG, search and utility tools
│
├── app.py               # Main Flask application entry point
├── config.py            # Application configuration
├── requirements.txt     # Python dependencies
└── .gitignore
```

---

## ⚙️ Tech Stack

**AI / ML**
- LangChain, LangGraph, ChromaDB
- OpenAI API, Google Gemini API
- RAG Pipelines

**Backend**
- Flask, Flask-CORS, Python

**Database**
- MySQL

**Search & Retrieval**
- Tavily, DuckDuckGo Search, Yahoo Finance API

**Document Processing**
- PyPDF, Python-Docx

---

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Kshitij-1729/Agentic_AI_Chatbot.git
cd Agentic_AI_Chatbot
```

### 2. Create & Activate a Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory:

```env
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_gemini_api_key
TAVILY_API_KEY=your_tavily_key

MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=agentic_chatbot
```

### 5. Run the Application

```bash
python app.py
```

The app will start at **http://localhost:5000**

---

## 🔄 API Reference

### Chat

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/chat` | Process a user query through the agentic workflow |

### Conversation Management

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/conversations` | List all conversations |
| POST | `/api/conversations` | Create a new conversation |
| GET | `/api/conversations/<id>` | Get conversation details |
| DELETE | `/api/conversations/<id>` | Delete a conversation |
| PUT | `/api/conversations/<id>/title` | Rename a conversation |
| PUT | `/api/conversations/<id>/settings` | Update conversation settings |

### Files & RAG

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/upload` | Upload a document for RAG |
| GET | `/api/files` | List uploaded files |

### System

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/providers` | List available LLM providers |
| GET | `/api/health` | Health check |

---

## 🗺 Roadmap

- [ ] Streaming responses
- [ ] Voice assistant integration
- [ ] Authentication system
- [ ] Multi-user collaboration
- [ ] Advanced vector search optimization
- [ ] Docker & Kubernetes deployment
- [ ] Real-time web search agents
- [ ] Autonomous planning agents

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create a new branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## 📜 License

This project is open-source and available under the [MIT License](https://opensource.org/licenses/MIT).

---

## 👨‍💻 Author

Developed by **Kshitij Maindola** — [GitHub Profile](https://github.com/Kshitij-1729)

If you found this project useful, please ⭐ star the repo and share it!
