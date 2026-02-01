# Legally Bot ⚖️

Legally Bot is a scalable, modular Telegram bot designed for legal education and assistance. It leverages RAG (Retrieval-Augmented Generation) with Hybrid Search (Pinecone + BM25) to provide accurate legal answers and features a gamified "Student Mode" for RLHF (Reinforcement Learning from Human Feedback).

## 🚀 Tech Stack

-   **Language**: Python 3.11+
-   **Framework**: aiogram 3.x (Async)
-   **Database**: MongoDB (via Motor)
-   **Vector DB**: Pinecone
-   **RAG**: SentenceTransformers + RankBM25
-   **Architecture**: Modular Clean Architecture (Service/Repository Pattern)

## 📂 Project Structure

```plaintext
legally_bot/
├── bot.py                # Entry point
├── config.py             # Configuration & Env Loading
├── database/             # Data Access Layer (MongoDB/Repositories)
├── services/             # Business Logic (RAG, ETL, Access Control)
├── handlers/             # Telegram Handlers (UI/UX)
├── keyboards/            # Keyboard Builders
└── states/               # FSM States
```

## 🛠️ Setup & Installation

1.  **Clone the repository**:
    ```bash
    git clone <repo_url>
    cd legally-bot
    ```

2.  **Create a virtual environment**:
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Mac/Linux
    source .venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r legally_bot/requirements.txt
    ```

4.  **Configure Environment**:
    -   Rename `.env.example` to `.env` inside `legally_bot/`.
    -   Fill in your API keys:
        ```env
        BOT_TOKEN=your_telegram_bot_token
        MONGO_URI=mongodb://localhost:27017
        PINECONE_API_KEY=your_pinecone_key
        ```

5.  **Run the Bot**:
    ```bash
    cd legally_bot
    python bot.py
    ```

## 🌟 Features

-   **Role-Based Access**:
    -   **User**: Basic access.
    -   **Student**: Access to Case Trainer mode.
    -   **Professor**: Validates student corrections.
    -   **Admin**: Manages users and roles.
    -   **Developer**: Access to ingestion tools.
-   **RAG Engine**: Hybrid search using Vector (Semantic) and Keyword (BM25) search.
-   **ETL Pipeline**: Ingest PDF, DOCX, and URLs into the knowledge base (Developer only).
-   **RLHF**: Students can correct AI answers, creating a feedback loop for improvement.

## 📝 Developer Notes

-   **RAG Mocking**: The `rag_engine.py` currently mocks the search response. Connect a real Pinecone index to enable actual retrieval.
-   **Ingestion**: `ingestion_service.py` provides the structure for document parsing and chunking.
