# TrustWise Phase 1 - Planning & Execution Frontend

## Phase 1 Architecture Overview

This is the **correct Phase 1 implementation** that follows the trust-first, agent-based architecture:

```
User Query (Natural Language)
       ↓
LLM-Based Orchestrator (Plan Generation)
       ↓
Structured JSON Execution Plan
       ↓
Task Chunking
       ↓
Scheduler (Agent Routing)
       ↓
Agents Execute & Collect Raw Data
       ↓
Display Results (No Validation/Summarization)
```

## Key Features

### ✅ Phase 1 Compliance

- **Natural Language Input**: Users submit queries in plain English
- **LLM-Based Planning**: System generates structured JSON execution plans
- **Deterministic & Auditable**: All plans are JSON-based and reproducible
- **Agent Separation**: Clear separation between planning, routing, and execution
- **Raw Data Collection**: Agents collect data without reasoning or validation
- **No Database Storage**: Data is displayed directly (logging only)

### 🚫 Phase 1 Exclusions (Not Implemented)

- ❌ No Zero Trust validation
- ❌ No credibility scoring
- ❌ No LLM-based summarization
- ❌ No database sufficiency checks
- ❌ No trust verification or insights generation

## Architecture Components

### 1. Query Input

- Users enter natural language queries
- Example: "Give me weekly tech updates on AI and cybersecurity"

### 2. Execution Plan Generation

The system generates a structured JSON plan containing:

- **Goal**: Interpreted objective (e.g., "Collect weekly information on AI/ML, Cybersecurity")
- **Domains**: Relevant areas (e.g., AI/ML, Cybersecurity, Blockchain)
- **Time Range**: Weekly, monthly, latest, daily
- **Source Types**: Web, research papers, database, vector
- **Tasks**: Array of task objects, each with:
  - `task_id`: Unique identifier
  - `agent_type`: Which agent to use (web_agent, research_agent, db_agent, vector_agent)
  - `source_type`: Type of data source
  - `prompt`: Task-specific instruction for the agent
  - `timeout_ms`: Execution timeout

### 3. Task Execution

- Scheduler routes tasks to appropriate agents
- Agents execute independently without sharing context
- Each agent collects raw data from its assigned source
- No cross-agent communication or coordination

### 4. Results Display

- Shows raw data from each agent
- Displays execution status for each task
- Maintains full auditability of what was collected

## Quick Start

### Start Both Servers

**Terminal 1 - Backend:**

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 - Frontend:**

```bash
cd frontend
python serve_phase1.py
```

**Open Browser:**
http://localhost:3001

### Or Use the Convenience Script

```bash
# Windows PowerShell
.\start_phase1.ps1

# Or Windows CMD
start_phase1.bat
```

## How to Use

### Step 1: Enter Your Query

In the query input field, type a natural language request. Examples:

```
Give me weekly tech updates on AI and cybersecurity from trusted sources
```

```
Find the latest research papers on machine learning published this month
```

```
What are the recent developments in quantum computing and blockchain technology?
```

### Step 2: View Execution Plan

Click "Generate Execution Plan" to see the structured JSON plan that the system created:

```json
{
  "session_id": "uuid-here",
  "goal": "Collect weekly information on AI/ML, Cybersecurity",
  "domains": ["AI/ML", "Cybersecurity"],
  "time_range": "weekly",
  "source_types": ["web", "research_papers"],
  "tasks": [
    {
      "task_id": "task_1",
      "agent_type": "web_agent",
      "source_type": "web",
      "prompt": "Collect weekly updates on AI/ML from trusted web sources",
      "timeout_ms": 10000
    },
    ...
  ]
}
```

### Step 3: Monitor Task Execution

Tasks automatically execute after plan generation. Watch the status for each task:

- 🟡 **PENDING** - Task queued
- 🔵 **RUNNING** - Agent executing
- 🟢 **SUCCESS** - Data collected
- 🔴 **FAILED** - Execution error

### Step 4: View Raw Data

Each task shows the raw data collected by its agent:

```json
{
  "source": "arxiv.org",
  "title": "Latest AI Research Updates",
  "url": "https://arxiv.org/latest",
  "content": "Recent advances in transformer architectures...",
  "fetched_at": "2026-02-16T14:40:05.123456"
}
```

## API Endpoints

### POST /api/v1/plan

Generate execution plan from natural language query.

**Request:**

```json
{
  "query": "Give me weekly tech updates on AI"
}
```

**Response:**

```json
{
  "session_id": "uuid",
  "query": "...",
  "plan": { ... },
  "message": "Execution plan generated successfully"
}
```

### POST /api/v1/execute

Execute the generated plan with agents.

**Request:**

```json
{
  "session_id": "uuid",
  "plan": { ... }
}
```

**Response:**

```json
{
  "session_id": "uuid",
  "status": "completed",
  "results": [
    {
      "task_id": "task_1",
      "agent": "web_scrape_if_stale",
      "source": "web",
      "status": "success",
      "data": { ... },
      "executed_at": "2026-02-16T14:40:05.123456"
    }
  ],
  "executed_at": "2026-02-16T14:40:05.123456"
}
```

## Example Queries & Expected Plans

### Example 1: Weekly Tech Updates

**Query:** "Give me weekly tech updates on AI and cybersecurity from trusted sources"

**Generated Plan:**

- **Goal**: Collect weekly information on AI/ML, Cybersecurity
- **Domains**: AI/ML, Cybersecurity
- **Time Range**: weekly
- **Source Types**: web, research_papers
- **Tasks**: 4 tasks (2 web agents + 2 research agents)

### Example 2: Research Papers

**Query:** "Find the latest research papers on machine learning published this month"

**Generated Plan:**

- **Goal**: Collect latest information on AI/ML
- **Domains**: AI/ML
- **Time Range**: monthly
- **Source Types**: research_papers
- **Tasks**: 1 task (research agent)

### Example 3: Multi-Domain Query

**Query:** "What are recent developments in quantum computing and blockchain?"

**Generated Plan:**

- **Goal**: Collect latest information on Quantum Computing, Blockchain
- **Domains**: Quantum Computing, Blockchain
- **Time Range**: latest
- **Source Types**: web, research_papers
- **Tasks**: 4 tasks (2 domains × 2 source types)

## Agent Types

### Web Agent (`web_agent`)

- Collects data from trusted web sources
- Scrapes articles, news, blogs
- Returns: URL, title, content, metadata

### Research Agent (`research_agent`)

- Queries academic databases (ArXiv, IEEE, PubMed)
- Finds peer-reviewed papers
- Returns: Title, authors, abstract, DOI

### Database Agent (`db_agent`)

- Queries internal PostgreSQL databases
- Fetches structured records
- Returns: Query results, record count

### Vector Agent (`vector_agent`)

- Performs semantic search in vector databases
- Uses embeddings for similarity matching
- Returns: Top matches, similarity scores

## Current Implementation Status

### ✅ Implemented (Phase 1)

- Natural language query input UI
- Mock LLM-based plan generation
- Structured JSON plan display
- Task chunking and breakdown
- Agent execution simulation
- Raw data collection and display
- Session management
- Full frontend-backend integration

### 🔄 Mock vs. Production

**Current (Phase 1 Demo):**

- Mock plan generation using keyword matching
- Mock agent execution with sample data
- Simulated task routing

**Production Ready (Future):**

- Real LLM integration (GPT-4, Claude, Llama)
- Actual agent execution with real data sources
- Real scheduler integration
- Production data sources configuration

## Customization

### Add New Domain Keywords

Edit `app/api_phase1.py`, function `_generate_mock_plan()`:

```python
if 'your_domain' in query_lower:
    domains.append('Your Domain')
```

### Add New Time Range Keywords

```python
elif 'your_timerange' in query_lower:
    time_range = 'your_timerange'
```

### Customize Task Generation

Modify the task creation loop to add more sophisticated logic:

```python
for source_type in source_types:
    for domain in domains:
        # Your custom task generation logic
```

### Add Real LLM Integration

Replace `_generate_mock_plan()` with actual LLM calls:

```python
async def _generate_plan_with_llm(query: str) -> Dict[str, Any]:
    # OpenAI API call
    response = await openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{
            "role": "system",
            "content": "You are a planning agent..."
        }, {
            "role": "user",
            "content": query
        }]
    )
    # Parse and return structured plan
```

## Troubleshooting

### Backend not responding

**Check:** Is uvicorn running on port 8000?

```bash
Invoke-WebRequest http://localhost:8000/health
```

### Frontend shows CORS error

**Fix:** CORS is already enabled in `app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    ...
)
```

### Plan generation fails

**Check:** Backend logs for errors:

```bash
# Check terminal running uvicorn
```

### Tasks show "PENDING" forever

**Reason:** This is expected in current mock implementation - tasks execute instantly.
**Future:** Real agents will show actual status progression.

## Next Steps (Future Phases)

### Phase 2: Real LLM Integration

- Integrate OpenAI GPT-4 / Anthropic Claude
- Advanced prompt engineering for plan generation
- Context-aware task creation

### Phase 3: Production Agents

- Connect web agent to real scraping infrastructure
- Integrate research agent with ArXiv/IEEE APIs
- Connect database agent to production PostgreSQL
- Set up vector database with real embeddings

### Phase 4: Trust & Validation (Post Phase 1)

- Implement Zero Trust validation
- Add credibility scoring
- Source verification
- Data quality checks

### Phase 5: Storage & Analytics

- Store plans and results in database
- Add analytics and insights
- Generate reports
- Historical trend analysis

## Architecture Principles (Phase 1)

### Planning First

- LLM generates complete plan before any execution
- No dynamic re-planning during execution
- Plans are immutable and auditable

### Agent Independence

- Each agent executes its task independently
- No inter-agent communication
- Single responsibility per agent

### Raw Data Only

- Agents return unprocessed data
- No summarization or interpretation
- No trust scoring or validation

### Deterministic Execution

- Same plan always executes the same tasks
- Reproducible results
- Full audit trail

## Files Structure

```
TrustWise/
├── app/
│   ├── api_phase1.py          # Phase 1 API endpoints
│   ├── main.py                # Main FastAPI app
│   ├── agents/                # Agent implementations
│   └── orchestrator/          # Planning & scheduling
├── frontend/
│   ├── phase1.html            # Phase 1 UI
│   ├── serve_phase1.py        # Frontend server
│   └── README_PHASE1.md       # This file
└── start_phase1.ps1           # Quick start script
```

## Support

For questions about Phase 1 implementation:

1. Check this README
2. Review `app/api_phase1.py` for API logic
3. Review `frontend/phase1.html` for UI behavior
4. Check backend logs in the terminal

---

**Phase 1 Status: ✅ Complete & Running**

Access the system at: http://localhost:3001
