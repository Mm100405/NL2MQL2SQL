# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Frontend
- Install deps: `cd frontend && npm install`
- Start dev server: `cd frontend && npm run dev`
- Build production bundle: `cd frontend && npm run build`

### Backend
- Install deps: `cd backend && pip install -r requirements.txt`
- Start dev server: `cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8011`
- Run migrations manually: `cd backend && alembic upgrade head`

### Full stack
- Local start script: `./start.sh` (or `start.bat` on Windows)
- Local stop script: `./stop.sh` (or `stop.bat` on Windows)
- Docker dev stack: `docker-compose -f docker-compose.dev.yml up --build`
- Docker prod-like stack: `docker-compose up -d`

### Checks
- Python lint: `cd backend && ruff check .`
- Python format: `cd backend && black .`
- Frontend type/build check: `cd frontend && npm run build`

### Tests
- Backend pytest is installed, but there is no committed `backend/tests/` directory at the moment.
- If tests are added later, run all tests with `cd backend && pytest` and a single test with `cd backend && pytest path/to/test_file.py::test_name`.

## Environment and startup
- Backend settings come from `backend/.env` via `backend/app/config.py`.
- Deep Agents feature flags live separately in `backend/.env.deep_agents`.
- Frontend API base URL is controlled by `frontend/.env*` via `VITE_API_BASE_URL`.
- In local frontend development, Vite proxies `/api` to `http://localhost:8011` (`frontend/vite.config.ts`).
- `backend/app/main.py` auto-creates the configured MySQL database if missing and runs Alembic migrations on startup.
- The app dynamically adds the current LAN IP to CORS, which is important for intranet access.
- For field deployment, the simplest standardized path is Docker Compose production mode with `.env.docker` copied to `.env`; see `docs/现场标准化部署文档.md`.

## High-level architecture

This is a full-stack natural-language analytics app:
- Vue 3 frontend for chat-style querying and semantic-layer administration
- FastAPI backend for CRUD APIs, model configuration, query execution, and agent streaming
- A semantic layer stored in the app database (datasources, datasets, metrics, dimensions, views)
- An MQL-to-SQL translation pipeline built on `sqlglot`
- A Deep Agents / LangGraph workflow for NL -> MQL -> SQL -> execution -> interpretation
- A data-format generation flow that turns query results into reusable dynamic APIs

### Frontend structure
- `frontend/src/router/index.ts` splits the app into two major areas:
  - `/agent-query` and `/query/*` for query experiences
  - `/management/*` for semantic-layer and system configuration
- `frontend/src/views/query/AgentQueryPage.vue` is the main agent chat UI and the default landing page.
- `frontend/src/views/query/QueryPage.vue` is the classic non-streaming query page; both query pages can generate reusable APIs from query results.
- The frontend uses Pinia for app/settings state and Arco Design for UI.
- Most API calls go through Axios in `frontend/src/api/request.ts`, but agent streaming uses `fetch()` directly in `AgentQueryPage.vue` so it can consume the SSE-style response stream manually.
- Query-result-to-API UI lives in `frontend/src/components/query/DataFormatConfigModal.vue` and `frontend/src/components/query/ApiDebugModal.vue`.

### Backend API shape
- `backend/app/main.py` wires all routers under `/api/v1`.
- Main backend areas:
  - `api/v1/query.py`: classic non-streaming NL/MQL/SQL/execute/query-history endpoints
  - `api/v1/agent.py`: agent status, tool listing, streaming query endpoint
  - `api/v1/semantic.py`: CRUD for datasources, datasets, metrics, dimensions, relations
  - `api/v1/views.py`, `api/v1/dictionaries.py`, `api/v1/data_format.py`: semantic-layer supporting features and generated API endpoints
  - `api/v1/settings.py`: LLM provider/model configuration and related system settings
  - `api/v1/skills.py`: dynamic skill loading endpoints

### Two query paths coexist
There are two backend query flows and it matters which one you are editing:

1. **Classic flow** in `api/v1/query.py`
   - Natural language -> `services/nl_parser.py`
   - MQL -> `services/mql_engine.py`
   - SQL execution -> `services/query_executor.py`

2. **Agent flow** in `api/v1/agent.py`
   - Frontend posts to `/api/v1/agent/query/stream`
   - Backend uses `EnhancedDeepAgentsManager`
   - Streamed progress is emitted back to the frontend and rendered step-by-step

The current default homepage uses the **agent flow**, not the classic query page.

### History and conversation routes
- The frontend currently uses the older query-history endpoints, not the newer conversation alias endpoints.
- Active frontend calls are:
  - list: `/query/history`
  - detail: `/query/history/{id}`
  - conversation load: `/query/conversation/{conversation_id}`
- Alias endpoints (`/query/conversation/list`, `/query/conversation/history`, `/query/conversation/detail/{id}`) exist for compatibility and documentation, but are not currently used by the shipped frontend.
- When editing `backend/app/api/v1/query.py`, preserve the old `/history` routes because current pages depend on them.

### Deep Agents architecture
- `backend/app/agents/deep_agents/manager.py` owns the base LangGraph execution path.
- `backend/app/agents/deep_agents/enhanced_manager.py` wraps the base manager with dynamic skill loading support.
- `backend/app/agents/deep_agents/workflow.py` defines the actual graph nodes.
- The workflow is:
  - `preparation`
  - `generation`
  - `validation`
  - conditional `correction`
  - `translation`
  - `execution`
  - `interpretation`
- Tool implementations live in `backend/app/agents/deep_agents/tools.py`.
- The workflow state is carried through `DeepAgentState` and streamed back as intermediate UI steps.

### Semantic layer and MQL translation
- The semantic layer is stored in the app DB and modeled via SQLAlchemy entities such as `DataSource`, `Dataset`, `Metric`, `Dimension`, `View`.
- The SQL generator is no longer the old string-based engine; `backend/app/services/mql_engine.py` is now a thin wrapper over the V2 translator.
- Real translation logic is in `backend/app/services/mql_translator/translator.py` and related modules:
  - `semantic.py`: loads semantic context from the DB
  - `ast_builder.py`: builds a `sqlglot` AST from MQL
  - `optimizer.py`: optional AST optimization
  - `dialect.py`: SQL dialect rendering
  - `cache.py`: translation cache
- Translation is semantic-layer-driven: the translator resolves the used view/datasource from metadata before rendering SQL.

### Query execution and generated APIs
- `backend/app/services/query_executor.py` executes rendered SQL against the selected datasource.
- Datasource connection details are stored in `datasources.connection_config` JSON.
- Supported datasource types in code are PostgreSQL, MySQL, and ClickHouse.
- Semantic datasource CRUD and connection testing are handled in `api/v1/semantic.py`.
- Query results can be turned into dynamic external APIs through `api/v1/data_format.py`; the frontend drives this via `generateDataFormatConfig`, then uses generated `/data-format/custom/{config_id}` endpoints and their `/docs` metadata.

### Model configuration
- Active LLM configuration is stored in the database, not just `.env`.
- `api/v1/settings.py` manages provider/model records and tests connectivity.
- Deep Agents tools read the active/default `ModelConfig` from the DB at runtime.
- If agent behavior seems broken, verify there is an active default model configured before changing prompts or workflow logic.
- If the UI loads but querying fails, model configuration is the first thing to check.

## Repo-specific notes
- `frontend/.env.example` recommends `VITE_API_BASE_URL=/api/v1` for LAN-friendly development; avoid hardcoding localhost unless you specifically want local-only behavior.
- `backend/.env.deep_agents` currently enables Deep Agents and auto-fallback, while intent/insight analysis toggles are disabled.
- `backend/app/main.py` deliberately reapplies logging setup after startup because Alembic startup migration can overwrite logger configuration.
- `docs/指定接口文档.md`, `docs/用户操作手册.md`, `docs/问数平台标准化配置文档.md`, and `docs/现场标准化部署文档.md` were written from actual code and are useful high-level references when editing APIs, user flows, or deployment.
- `CODEBUDDY.md` contains useful architecture notes and verified commands; use it as supporting context if `CLAUDE.md` needs to be expanded later.
