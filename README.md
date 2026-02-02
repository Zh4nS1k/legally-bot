# Legally Bot ⚖️ - AI Legal Assistant 2.0

**Legally Bot** is an advanced AI-powered legal assistant designed for the Kazakhstan legal system. It goes beyond simple semantic search by implementing **Graph-based Retrieval (RAG 2.0)** and **Multi-Step Reasoning Chains**.

## 🚀 Key Features

### 🧠 Advanced RAG 2.0 Engine
- **Semantic Chunking**: Instead of arbitrary text splitting, the bot understands legal structure. It chunks documents by **Article** ("Статья"), ensuring that every retrieval unit is a complete legal norm.
- **Graph RAG (Dijkstra Traversal)**: The bot builds a "Citation Graph" during ingestion. If a found article references another (e.g., *"see Article 5"*), the system automatically traverses this link and fetches the referenced article, providing a complete legal context.
- **Reasoning Chains (Markov Logic)**: The AI doesn't just "guess". It follows a rigorous chain of thought:
    1.  **Draft**: Generates a preliminary answer based on retrieved context.
    2.  **Refine**: A "Senior Editor" persona critiques the draft, verifies citations against metadata, and removes hallucinations.
- **Strict Citation**: Every claim is backed by a specific Source and Article number.

### 🛡️ Robust Ingestion Pipeline
- **Trafilatura Parsing**: Uses state-of-the-art HTML extraction to strip UI noise (menus, ads) from government sites (`adilet.zan.kz`).
- **SSL Bypass**: Custom networking logic handles specific government SSL configurations to ensure reliable scraping.
- **Metadata Enrichment**: every chunk is tagged with:
    -   `source`: Official Law Title
    -   `article`: Article Number
    -   `url`: Direct link to the source
    -   `references`: List of outgoing citations (Edges)

### 👥 Role-Based Ecosystem
-   **User**: Ask questions, get accurate legal answers.
-   **Student**: "Case Trainer" mode for gamified learning.
-   **Professor**: Validate student inputs.
-   **Developer**: Access to `/ingest_link` and debug tools.

---

## 🛠️ Tech Stack

-   **Core**: Python 3.11+, `aiogram` (Async Telegram Bot)
-   **AI/LLM**: Multi-Provider Fallback (DeepSeek, Gemini, Groq)
-   **Vector DB**: Pinecone (Serverless)
-   **Embeddings**: `BAAI/bge-large-en-v1.5` (State-of-the-art retrieval model)
-   **Database**: MongoDB (User Data, FSM States)
-   **Ingestion**: `trafilatura` (Scraping), `regex` (Chunking)

---

## 📂 Architecture

The project follows **Clean Architecture**:

```plaintext
legally_bot/
├── bot.py                  # Application Entry Point
├── config.py               # Settings & secrets
├── services/               # 🧠 THE BRAIN
│   ├── rag_engine.py       # Reasoning Chains & Graph Search
│   ├── ingestion_service.py# Semantic Chunking & Graph Construction
│   └── ...
├── database/               # Data Persistence
├── handlers/               # Telegram UI Logic
└── ...
```

## 🚀 Quick Start

1.  **Clone & Install**:
    ```bash
    git clone <repo_url>
    pip install -r legally_bot/requirements.txt
    ```

2.  **Environment Setup**:
    Create `.env`:
    ```env
    BOT_TOKEN=...
    MONGO_URI=mongodb://localhost:27017
    PINECONE_API_KEY=...
    PINECONE_INDEX_NAME=...
    # LLM Keys
    DEEPSEEK_API_KEY=...
    GEMINI_API_KEY=...
    GROQ_API_KEY=...
    ```

3.  **Run**:
    ```bash
    cd legally_bot
    python bot.py
    ```

## 📝 Developer Commands

-   `/ingest_link`: (Developer Only) Feed a URL from `adilet.zan.kz`. The bot will parse, chunk, and indexing it into Pinecone.
-   `⚠️ Note`: The bot automatically handles 404/SSL errors for supported domains.
