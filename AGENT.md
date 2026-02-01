# Developer Guide (AGENT.md)

## Architecture Overview

This project follows **Clean Architecture** principles to ensure scalability and ease of maintenance. The monolithic structure is designed to be easily decomposable into microservices if needed.

### Layers

1.  **Handlers (Interface Layer)**:
    -   Located in `handlers/`.
    -   Sole responsibility is handling Telegram updates, parsing input, and formatting output.
    -   **DO NOT** put business logic here. Call `services/` instead.

2.  **Services (Business Logic Layer)**:
    -   Located in `services/`.
    -   Contains the core logic (RAG search, Access Control, Workflows).
    -   `rag_engine.py`: Handles search logic. Currently mocked.
    -   `workflow.py`: Orchestrates complex interactions between users, DB, and AI.
    -   `ingestion_service.py`: Handles ETL for documents.

3.  **Database (Data Access Layer)**:
    -   Located in `database/`.
    -   `mongo_db.py`: Manages the async connection.
    -   Repositories (`users_repo.py`, `feedback_repo.py`) abstract the database queries.
    -   **Rule**: Services should strictly talk to Repositories, not raw MongoDB.

## Key Design Decisions

-   **config.py**: Uses `pydantic-settings` for robust environment variable management. It is configured to ignore extra variables to prevent crashes in diverse environments.
-   **Dependency Injection**: The `bot.py` initializes the DB connection, ensuring a single connection pool.
-   **FSM (Finite State Machines)**: Used for multi-step flows like Registration and Ingestion to keep tracking user context robust.

## Future Improvements / To-Do

1.  **Connect Real RAG**: Replace the mock response in `services/rag_engine.py` with actual `pinecone` query calls.
2.  **Real Ingestion**: Implement the file reading logic in `services/ingestion_service.py` using `pypdf` and `python-docx` (imports are currently commented out or mocked).
3.  **Dockerization**: Add a `Dockerfile` and `docker-compose.yml` for containerized deployment.
4.  **Testing**: Add `pytest` unit tests for Services and Repositories.
