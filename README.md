# PowerWorldCUA

> Bring PowerWorld online for modern companies to use

## Why We Built This

PowerWorld software is used by electric utilities, consultants, and universities for analyzing and visualizing high-voltage power systems for power flow, contingency analysis, transient stability, and optimal power flow (OPF) to plan transmission, manage markets, and train operators, especially with renewables integration.

**The Problem:** It is used by 1000 utility providers in the US but still it is only supported in Win32.

## What It Does

We used Computer Use Agents to bring the decades-old legacy system online by connecting it to APIs - enabling modern companies to plan transmission, manage markets, and train operators using modern technology.

## How We Built It

- **CUA** Computer Use Agents
- **CodeRabbit** for code assistance

## Challenges We Ran Into

Integrating PowerWorld with CUA was challenging since its UI hasn't changed in a decade. The complex UI required multi-step prompts and validation to make it work reliably every time. CUA does most of the heavy lifting for us.

## What We're Proud Of

Bringing PowerWorld online - connecting critical infrastructure software used by 1000+ US utilities to the modern world through AI-powered automation.

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Anthropic API Key
- CUA API Key

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file with your API keys:

```
ANTHROPIC_API_KEY=your_key_here
CUA_API_KEY=your_key_here
```

Run the server:

```bash
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend
pnpm install
pnpm dev
```

## Built With

- Python / FastAPI (Backend)
- Next.js / React (Frontend)
- Anthropic CUA (AI Agent)
