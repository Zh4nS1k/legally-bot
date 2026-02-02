# Developer Guide & Architecture (AGENT.md)

This document details the internal architecture of **Legally Bot**, focusing on the **RAG 2.0** implementation, Graph Algorithms, and Reasoning Engines.

## 🧠 Core Systems

### 1. Ingestion Service (The "Graph Builder")
*Located in: `services/ingestion_service.py`*

The ingestion pipeline transforms raw HTML/PDFs into a structured **Knowledge Graph**.

-   **Extraction**: Uses `trafilatura` for high-fidelity HTML parsing, bypassing `adilet.zan.kz` SSL issues via custom `requests` adapters.
-   **Semantic Chunking (Regex)**:
    -   Unlike standard "split by 500 chars", we split by **Legal Norm**.
    -   **Regex**: `((?:Article|Статья)\s+\d+)`
    -   Result: One Chunk = One Article. This prevents splitting a sentence in half.
    -   **Size Safety**: Any Article > 35KB is sub-chunked intelligently to respect Pinecone limits (40KB metadata).
-   **Edge Detection (Graph Construction)**:
    -   The system scans every article for citations (e.g., "according to Article 5").
    -   These found citations are stored in the vector database metadata as `references: ["5", "10"]`.

### 2. RAG Engine (The "Reasoning Brain")
*Located in: `services/rag_engine.py`*

The search process is not a simple lookup. It follows a **Graph-Enhanced Reasoning Chain (Algorithm)**.

#### Phase 1: Retrieval & Graph Traversal (The "Dijkstra" Step)
1.  **Initial Search**: Query the Vector DB (Pinecone) for the top N most relevant chunks.
2.  **Edge Expansion**: 
    -   The engine explicitly checks the `references` metadata of the found chunks.
    -   Example: If we find "Article 15 (Penalty)", and it says "see Article 3 (Definitions)", the engine **automatically** fetches Article 3.
    -   This mimics a lawyer cross-referencing definitions.

#### Phase 2: Reasoning Chain (The "Markov" Step)
The answer is generated via a multi-state loop (Chain of Thought):

1.  **State S0 (Drafting)**:
    -   *Input*: Context + Query.
    -   *Action*: LLM drafts a raw, fact-based answer.
    -   *Prompt*: "Draft a preliminary answer..."
2.  **State S1 (Refining)**:
    -   *Input*: Draft Answer + Context.
    -   *Action*: A second persona ("Senior Editor") verifies every citation.
    -   *Constraint*: If a source is cited but not in Context -> Delete it (Hallucination prevention).
    -   *Output*: Final, legally binding answer.

### 3. Verification & Safety
-   **Pinecone Metadata Limits**: We enforce strict byte-size checks before upload.
-   **LLM Fallback**: The engine tries `DeepSeek` -> `Gemini` -> `Groq` in sequence. If one fails, the next takes over instantly.

## 🛠️ Data Flow

```mermaid
graph TD
    User[User Query] --> Bot[Telegram Bot]
    Bot --> Ingestion{Ingest?}
    Ingestion -- Yes --> Trafilatura[HTML Parse]
    Trafilatura --> Chunker[Semantic Regex Split]
    Chunker --> EdgeDetect[Extract "Article X" Refs]
    EdgeDetect --> Pinecone[(Vector DB)]
    
    Bot --> RAG{Search?}
    RAG --> Pinecone
    Pinecone --> Docs[Initial Docs]
    Docs --> GraphExpand[Fetch Referenced Articles]
    GraphExpand --> Context[Full Context]
    Context --> DraftLLM[Drafting Phase]
    DraftLLM --> RefineLLM[Refining Phase]
    RefineLLM --> User
```

## 📝 Future Complexities

1.  **Recursive Graph Expansion**: Currently step-1 expansion. Can be upgraded to N-depth (traverse references of references).
2.  **Dynamic Graph Visualization**: Generate a visual graph of how laws connect for the user.
