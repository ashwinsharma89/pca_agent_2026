# 🎯 PCA Agent - Complete Documentation

> **Performance Campaign Analyzer** - An AI-powered platform for analyzing advertising campaigns across Google Ads, Meta, LinkedIn, TikTok, and more.

---

## 📋 Table of Contents

1. [Overview](#-overview)
2. [Architecture](#-architecture)
3. [Pages & Features](#-pages--features)
4. [AI Agents & Intelligence](#-ai-agents--intelligence)
5. [Security](#-security)
6. [Technology Stack](#-technology-stack)
7. [Testing](#-testing)
8. [Data Flow](#-data-flow)

---

## 🌟 Overview

PCA Agent is a **full-stack analytics platform** that helps marketing teams:
- 📊 **Upload** campaign data from any advertising platform
- 🤖 **Analyze** performance using AI-powered insights
- 💬 **Ask questions** in plain English and get SQL-backed answers
- 📈 **Visualize** trends, funnels, and comparisons
- 📋 **Generate reports** for pacing and performance tracking

### Who is this for?
| Role | Benefits |
|------|----------|
| 🎯 **Marketing Managers** | Get instant insights without SQL knowledge |
| 📊 **Media Analysts** | Deep-dive into cross-platform performance |
| 💼 **Executives** | One-click executive summaries |
| 🛠️ **Developers** | Extensible architecture, clean APIs |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USER'S BROWSER                              │
│                         http://localhost:3000                            │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js + React)                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ Upload  │ │Analysis │ │   Q&A   │ │ Charts  │ │ Reports │           │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘           │
└───────┼───────────┼───────────┼───────────┼───────────┼─────────────────┘
        │           │           │           │           │
        └───────────┴───────────┴─────┬─────┴───────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        BACKEND API (FastAPI/Python)                      │
│                         http://localhost:8000                            │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                         API ENDPOINTS                               │ │
│  │  • /auth/login          • /campaigns/upload                        │ │
│  │  • /campaigns/analyze   • /campaigns/chat                          │ │
│  │  • /campaigns/visualizations                                       │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                      │                                   │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                │
│  │ Data Processor│  │  Query Engine │  │ Analytics AI  │                │
│  │   (Pandas)    │  │  (NL to SQL)  │  │ (RAG Expert)  │                │
│  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘                │
└──────────┼──────────────────┼──────────────────┼────────────────────────┘
           │                  │                  │
           ▼                  ▼                  ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│     DuckDB      │  │   LLM APIs      │  │ Vector Store    │
│ (Campaign Data) │  │ (OpenAI/Gemini) │  │ (RAG Context)   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Three-Layer Design

| Layer | Technology | Purpose |
|-------|------------|---------|
| 🎨 **Frontend** | Next.js, React, Tailwind | Beautiful, responsive UI |
| ⚙️ **Backend** | FastAPI, Python | Business logic, AI orchestration |
| 💾 **Data** | DuckDB | Fast analytics queries |

---

## 📱 Pages & Features

### 1️⃣ Upload Page (`/upload`)

> **Purpose**: Import your campaign data into the system

**What it does:**
- ✅ Accepts CSV and Excel files (.xlsx, .xls)
- ✅ Auto-detects multiple sheets in Excel files
- ✅ Standardizes 100+ different column name variations
- ✅ Calculates derived metrics (CTR, CPC, CPA, ROAS)
- ✅ Shows data preview and schema validation

**Under the hood:**
```python
# MediaDataProcessor standardizes messy column names
"cost" → "Spend"
"platform_name" → "Platform"  
"click_through_rate" → "CTR"
```

**Required columns:**
| Column | Description |
|--------|-------------|
| Campaign_Name | Name of the campaign |
| Platform | Google Ads, Meta, LinkedIn, etc. |
| Spend | Amount spent (in dollars) |
| Impressions | Number of ad views |
| Clicks | Number of clicks |

---

### 2️⃣ Analysis Page (`/analysis`)

> **Purpose**: Get AI-powered insights about your campaigns

**Features:**
- 🧠 **RAG-Enhanced Summaries** - AI reads your data + marketing knowledge base
- 📊 **Portfolio Summary** - Key KPIs at a glance
- 💡 **Key Insights** - What's working, what's not
- 🎯 **Strategic Recommendations** - Actionable next steps

**Configuration Options:**
| Option | Description |
|--------|-------------|
| Use RAG Intelligence | Enhance with marketing knowledge |
| Industry Benchmarks | Compare against standards |
| Analysis Depth | Quick / Standard / Deep |
| Strategic Roadmap | Include recommendations |

**How the AI works:**
1. Aggregates your data by channel, funnel stage, device, etc.
2. Builds a detailed prompt with the aggregated metrics
3. Sends to LLM (OpenAI, Gemini, or Claude)
4. Returns structured insights in natural language

---

### 3️⃣ Q&A Page (`/chat`)

> **Purpose**: Ask questions in plain English, get data-backed answers

**Example Questions:**
- *"Which campaign had the best ROAS last month?"*
- *"Show me spend breakdown by device type"*
- *"Compare Google Ads vs Meta performance"*

**How it works:**

```
┌─────────────────────────────────────────────────────────────┐
│  "Which platform had the highest conversions?"              │
└─────────────────────────────────┬───────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│  NL to SQL Engine (LLM converts question to SQL)            │
│  ────────────────────────────────────────────────           │
│  SELECT Platform, SUM(Conversions) as total                 │
│  FROM campaigns GROUP BY Platform ORDER BY total DESC       │
└─────────────────────────────────┬───────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│  Safe Query Executor (validates SQL for security)           │
└─────────────────────────────────┬───────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│  DuckDB executes query → Returns results                    │
└─────────────────────────────────┬───────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│  LLM generates natural language answer with data            │
│  "Meta had the highest conversions with 12,450, followed    │
│   by Google Ads with 8,320..."                              │
└─────────────────────────────────────────────────────────────┘
```

---

### 4️⃣ Visualizations Page (`/visualizations`)

> **Purpose**: Interactive charts and graphs

**Available Charts:**
| Chart Type | Use Case |
|------------|----------|
| 📈 Area Chart | Trends over time |
| 📊 Bar Chart | Platform/channel comparison |
| 🥧 Pie Chart | Device/audience breakdown |
| 📊 Composed | Metrics + line overlay |
| 🔄 Funnel | Impressions → Clicks → Conversions |

**Filter Options:**
- Platform (Google, Meta, LinkedIn, etc.)
- Date Range
- Funnel Stage (Awareness, Consideration, Conversion)
- Channel, Device, Placement

---

### 5️⃣ Intelligence Studio (`/intelligence-studio`)

> **Purpose**: Natural language visualization builder

**Special Features:**
- 🎤 **Voice Input** - Ask questions by speaking
- 🤖 **Auto Chart Selection** - AI picks the best chart type
- 💬 **Conversational** - Follow-up questions build on context
- 📥 **Export** - Download charts and data

---

### 6️⃣ Reports Page (`/reports`)

> **Purpose**: Generate downloadable reports

**Report Types:**
- 📊 **Pacing Report** - Budget utilization tracking
- 📈 **Performance Report** - Campaign metrics summary
- 📋 **Excel Export** - Full data download

---

### 7️⃣ Other Pages

| Page | Purpose |
|------|---------|
| 🏠 Dashboard | Quick overview |
| 📉 Regression | Statistical analysis |
| ⚙️ Settings | API keys, preferences |

---

## 🤖 AI Agents & Intelligence

### The Brain: MediaAnalyticsExpert

Located in `src/analytics/auto_insights.py`, this is the core AI that:

1. **Calculates Metrics** by dimension:
   - By Channel (Google, Meta, etc.)
   - By Funnel Stage (Awareness → Conversion)
   - By Device (Mobile, Desktop, Tablet)
   - By Placement, Region, Ad Type

2. **Builds RAG-Augmented Prompts**:
   ```
   "You are a senior media analytics expert with 15+ years experience...
   
   Here is the campaign data:
   - Total Spend: $1.2M
   - By Channel: Google ($500K), Meta ($400K)...
   
   Provide insights on what's working and what's not."
   ```

3. **Generates Insights**:
   - Executive Summary (brief + detailed)
   - Key Insights (8-10 actionable points)
   - Strategic Recommendations

---

### The Query Engine: NL to SQL

Located in `src/query_engine/nl_to_sql.py`:

**Purpose**: Convert plain English questions into SQL queries

**Multi-Model Support:**
| Provider | Model | Use Case |
|----------|-------|----------|
| OpenAI | gpt-4o-mini | Default, balanced |
| Google | gemini-1.5-flash | Fast, cost-effective |
| Anthropic | claude-3-5-sonnet | High quality |
| Groq | llama-3.3-70b | Open source |
| DeepSeek | deepseek-chat | Alternative |

**Safety Layer** (`src/query_engine/safe_query.py`):
- ❌ Blocks DELETE, DROP, UPDATE, INSERT
- ❌ Blocks UNION to prevent injection
- ✅ Only allows SELECT queries
- ✅ Validates table/column names against schema

---

## 🔒 Security

### Authentication
- **JWT Tokens** - Secure, time-limited access tokens
- **Password Hashing** - bcrypt with salt
- **Session Management** - Auto-expire after inactivity

### API Security
| Protection | Implementation |
|------------|----------------|
| CSRF Protection | X-CSRF-Token header required |
| CORS | Configured for localhost:3000 only |
| Rate Limiting | Prevents abuse |
| Input Validation | Pydantic models validate all inputs |

### SQL Injection Prevention
```python
# SafeQueryExecutor checks every query:
BLOCKED_PATTERNS = [
    "DELETE", "DROP", "UPDATE", "INSERT",
    "UNION", "ALTER", "TRUNCATE", "--"
]
```

### File Upload Security
- ✅ File type validation (only CSV, Excel)
- ✅ Size limits
- ✅ Content validation (must have required columns)

---

## 🛠️ Technology Stack

### Frontend

| Library | Purpose |
|---------|---------|
| **Next.js 16** | React framework with routing |
| **React 19** | UI components |
| **Tailwind CSS** | Utility-first styling |
| **Recharts** | Charts and visualizations |
| **TanStack Query** | API data fetching & caching |
| **Lucide Icons** | Beautiful icons |
| **shadcn/ui** | Pre-built UI components |

### Backend

| Library | Purpose |
|---------|---------|
| **FastAPI** | Modern, fast web framework |
| **Uvicorn** | ASGI server |
| **Pandas** | Data manipulation |
| **DuckDB** | Analytics database |
| **Loguru** | Better logging |
| **Pydantic** | Data validation |
| **python-jose** | JWT handling |
| **bcrypt** | Password hashing |

### AI/ML

| Library | Purpose |
|---------|---------|
| **OpenAI** | GPT models for text generation |
| **google-generativeai** | Gemini models |
| **Anthropic** | Claude models |
| **Groq** | Fast inference |
| **LangChain** (optional) | RAG orchestration |

### Database

| Technology | Purpose |
|------------|---------|
| **DuckDB** | Primary analytics database |
| **SQLite** | User/session storage |

---

## 🧪 Testing

### Frontend Testing

**Playwright** for end-to-end browser tests:
```bash
cd frontend
npm run test:e2e
```

Test files in `frontend/e2e/`:
- `auth.spec.ts` - Login/logout flows
- `upload.spec.ts` - File upload
- `analysis.spec.ts` - AI analysis

### Backend Testing

**Pytest** for unit and integration tests:
```bash
pytest tests/
```

### Manual Testing Checklist

| Feature | Test |
|---------|------|
| ✅ Upload | CSV with 10K+ rows |
| ✅ Q&A | Complex multi-table queries |
| ✅ Analysis | RAG summary generation |
| ✅ Charts | All chart types render |
| ✅ Export | Excel download works |

---

## 🔄 Data Flow

### Complete User Journey

```
┌──────────────────────────────────────────────────────────────────────┐
│                         1. UPLOAD                                     │
│  ┌────────┐    ┌──────────┐    ┌───────────┐    ┌────────────┐       │
│  │ Excel  │───►│ Frontend │───►│  Backend  │───►│  DuckDB    │       │
│  │ File   │    │ /upload  │    │ /upload   │    │ campaigns  │       │
│  └────────┘    └──────────┘    └───────────┘    └────────────┘       │
└──────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         2. ANALYZE                                    │
│  ┌────────┐    ┌──────────┐    ┌───────────┐    ┌────────────┐       │
│  │ Click  │───►│ Frontend │───►│ Analytics │───►│   LLM      │       │
│  │ Button │    │ /analysis│    │   Expert  │    │ (OpenAI)   │       │
│  └────────┘    └──────────┘    └───────────┘    └────────────┘       │
│                                      │                                │
│                                      ▼                                │
│                              ┌───────────┐                            │
│                              │ Insights  │                            │
│                              │ Summary   │                            │
│                              └───────────┘                            │
└──────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         3. QUERY (Q&A)                                │
│  ┌────────┐    ┌──────────┐    ┌───────────┐    ┌────────────┐       │
│  │ "Best  │───►│ NL→SQL   │───►│  Execute  │───►│  Results   │       │
│  │ ROAS?" │    │  Engine  │    │   Query   │    │  + Answer  │       │
│  └────────┘    └──────────┘    └───────────┘    └────────────┘       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 📁 File Structure

```
pca_agent/
├── 📂 frontend/                 # Next.js application
│   ├── src/
│   │   ├── app/                 # Pages (upload, analysis, chat, etc.)
│   │   ├── components/          # Reusable UI components
│   │   └── lib/                 # API client, utilities
│
├── 📂 src/                      # Python backend
│   ├── api/                     # FastAPI endpoints
│   │   └── v1/                  # API routes (upload, campaigns, query)
│   │
│   ├── analytics/               # AI analysis logic
│   │   ├── auto_insights.py     # MediaAnalyticsExpert (Orchestrator)
│   │   └── metrics_calculator.py# Fast polars-based metrics
│   │
│   ├── ingestion/               # Unified Ingestion Pipeline (Phase 2)
│   │   ├── adapters.py          # Readers (CSV, Excel, API, DB)
│   │   ├── normalizer.py        # Schema standardization
│   │   ├── validators.py        # Data quality checks (Pandera)
│   │   └── pipeline.py          # Pipeline orchestrator & Sink
│   │
│   ├── query_engine/            # NL to SQL Engine (Phase 2/3)
│   │   ├── nl_to_sql.py         # Main Engine (Orchestrator)
│   │   ├── schema_manager.py    # Schema extraction
│   │   ├── prompt_builder.py    # RAG Prompt construction
│   │   ├── executor.py          # Safe query execution
│   │   └── validator.py         # AST Security checks
│   │
│   ├── intelligence/            # Advanced Intelligence (Phase 3)
│   │   ├── lancedb_manager.py   # Hybrid Search (RAG)
│   │   └── semantic_cache.py    # Semantic Caching
│   │
│   ├── database/                # Data Access Layer
│   │   └── duckdb_repository.py # DuckDB operations
│   │
│   ├── services/                # Business Logic
│   │   └── campaign_service.py  # Campaign operations
│   │
│   └── utils/                   # Shared Utilities
│       ├── metrics.py           # Safe metric calculations
│       └── column_mapping.py    # Column aliases
│
├── 📂 data/                     # Database files
│   └── campaigns.duckdb         # Your campaign data
│
├── 📂 tests/                    # Comprehensive Test Suite
│   ├── unit/                    # Unit tests
│   └── integration/             # End-to-end tests
```

---

## 🚀 Quick Start

### 1. Start the Application
```bash
# Option A: Double-click
open PCA_AutoStart.command

# Option B: Terminal
./start_all.sh
```

### 2. Access the App
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/api/docs

### 3. Login
- **Username**: `auditor`
- **Password**: `audit123`

### 4. Upload Data
Go to `/upload` and upload your campaign CSV/Excel file

### 5. Analyze
Go to `/analysis` and click "RAG Summary" for AI insights!

---

## 📞 Support

For issues or questions:
1. Check the `/api/docs` for API documentation
2. Review logs in `backend.log` and `frontend.log`
3. Ensure all API keys are set in `.env` file

---

*Built with ❤️ using FastAPI, Next.js, and AI*
