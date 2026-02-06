# TrustWise - Trustworthy Information Orchestration Engine

A FastAPI-based orchestration system that intelligently coordinates multiple data sources while ensuring information reliability through a sophisticated trust verification engine.

## Overview

TrustWise is an intelligent query orchestration platform designed to:
- **Retrieve information** from multiple trusted sources (databases, vector stores, web APIs, research repositories)
- **Verify credibility** by enforcing minimum confidence thresholds and trust score validations
- **Parallelize execution** by breaking queries into concurrent tasks across specialized agents
- **Block untrusted sources** to prevent LLM context pollution from unreliable data

## Key Features

### 🔐 Trust-Based Architecture
- Configurable trust scores for databases, web sources, and APIs
- Confidence threshold enforcement (minimum 80% for acceptance)
- Automatic rejection of queries when no trusted sources validate

### ⚡ Parallel Task Execution
- Dynamic query planning based on configurable strategies
- Automatic task chunking for concurrent agent execution
- Built-in task timeout management (100ms per task)

### 🤖 Multi-Agent System
- **Vector Agent**: Retrieves similar answers from vector databases
- **Database Agent**: Queries internal trusted databases (PostgreSQL)
- **Web Agent**: Crawls whitelisted domains (ArXiv, IEEE, NIST, etc.)
- **Research Agent**: Accesses peer-reviewed research repositories

### 🎯 Strategy-Driven Planning
- Flexible execution strategies defined in `prompts.json`
- Default strategy: `vector_check → db_check → web_scrape_if_stale → research_lookup`

## Project Structure

```
TrustWise/
├── app/
│   ├── main.py                 # FastAPI entry point
│   ├── agents/                 # Specialized data agents
│   │   ├── db_agent.py        # Database queries
│   │   ├── vector_agent.py    # Vector similarity search
│   │   ├── web_agent.py       # Web scraping from trusted domains
│   │   └── research_agent.py  # Research paper lookup
│   └── orchestrator/           # Core orchestration logic
│       ├── orchestrator.py    # Main coordinator
│       ├── planner.py         # Query planning from strategies
│       ├── chunker.py         # Task decomposition
│       ├── scheduler.py       # Task dispatch to agents
│       └── trust_engine.py    # Verification & aggregation
├── prompts.json               # Execution strategies
├── trusted_sources.json       # Trust scores for sources
└── requirements.txt           # Python dependencies
```

## Configuration

### Trusted Sources (`trusted_sources.json`)

Define trust profiles for all data sources:

```json
{
  "databases": [
    {
      "name": "internal_postgres",
      "type": "sql",
      "trust_score": 0.95
    }
  ],
  "web_sources": [
    {
      "name": "arxiv",
      "domain": "arxiv.org",
      "trust_score": 0.97
    },
    {
      "name": "nist",
      "domain": "nist.gov",
      "trust_score": 0.99
    }
  ],
  "apis": [
    {
      "name": "world_bank",
      "base_url": "api.worldbank.org",
      "trust_score": 0.94
    }
  ]
}
```

### Execution Strategies (`prompts.json`)

Configure the order of agent execution:

```json
{
  "default_strategy": {
    "steps": [
      "vector_check",
      "db_check",
      "web_scrape_if_stale",
      "research_lookup"
    ]
  }
}
```

## Execution Flow

```
Query Input
    ↓
[Planner] Creates execution plan from strategies
    ↓
[Chunker] Breaks plan into parallel tasks
    ↓
[Scheduler] Dispatches tasks to corresponding agents
    ↓
[Agents] Execute in parallel:
  • Vector Agent
  • DB Agent
  • Web Agent
  • Research Agent
    ↓
[Trust Engine] Verifies results:
  • Checks confidence ≥ 0.8
  • Validates "trusted" status
  • Rejects if no trusted sources
    ↓
Verified Context Output
```

## API Endpoints

### Health Check
```
GET /
```
Returns service status and version.

**Response:**
```json
{
  "status": "running",
  "service": "TrustWise Orchestrator"
}
```

## Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd TrustWise
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure trusted sources**
   - Edit `trusted_sources.json` to define your data source trust profiles
   - Edit `prompts.json` to customize execution strategies

## Usage

### Starting the Server
```bash
uvicorn app.main:app --reload
```

The service will start on `http://localhost:8000`

### Query Processing (Conceptual)
```python
from app.orchestrator.orchestrator import Orchestrator

orchestrator = Orchestrator()
result = orchestrator.handle_query("What is the latest ML research trend?")
# Returns verified context from trusted sources only
```

## Dependencies

- **fastapi**: Modern web framework for building APIs
- **uvicorn**: ASGI server for running FastAPI

See `requirements.txt` for complete dependency list.

## Trust Verification Rules

The `TrustEngine` enforces:

1. **Confidence Threshold**: Result confidence must be ≥ 0.8 (80%)
2. **Trust Status**: Result must have `"status": "trusted"`
3. **Minimum Results**: At least one result must pass both checks
4. **Failure Mode**: Raises exception if no trusted sources found (prevents LLM hallucination)

## Agent Specifications

### Vector Agent
- **Purpose**: Find similar answers in vector database
- **Output**: `{"source": "vector_db", "confidence": 0.85, "status": "trusted"}`

### Database Agent
- **Purpose**: Query internal PostgreSQL database
- **Output**: `{"source": "postgres", "confidence": 0.9, "data": "..."`

### Web Agent
- **Purpose**: Scrape data from whitelisted domains
- **Logic**: Checks domain against `trusted_sources.json` before returning data
- **Security**: Blocks unknown domains with `confidence: 0.0, status: "blocked_untrusted_source"`

### Research Agent
- **Purpose**: Lookup peer-reviewed research papers
- **Sources**: ArXiv, IEEE, NIST (configurable)
- **Output**: `{"source": "arxiv", "confidence": 0.97, "status": "trusted"}`

## Security Considerations

- **Source Whitelisting**: Only pre-approved domains and databases are accessible
- **Confidence Validation**: Low-confidence results are automatically rejected
- **Status Enforcement**: Unknown source status prevents context inclusion
- **Fail-Fast**: System aborts rather than hallucinating when no trusted sources exist

## Future Enhancements

- [ ] Async agent execution for better performance
- [ ] Caching layer for frequently accessed data
- [ ] Dynamic trust score adjustment based on data accuracy
- [ ] Multi-strategy selection based on query type
- [ ] Detailed audit logging for trust decisions
- [ ] Real-time monitoring dashboard

## Contributing

1. Maintain trust scores in `trusted_sources.json`
2. Add new strategies to `prompts.json` before implementation
3. Implement new agents following the existing interface pattern
4. Ensure all results include `confidence` and `status` fields

## License

[Add license information]

## Support

For issues, questions, or contributions, please open an issue in the repository.
