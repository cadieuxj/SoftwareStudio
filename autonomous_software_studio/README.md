# Autonomous Software Studio

A Multi-Agent Orchestration Pipeline for AI-Powered Software Development

## Overview

Autonomous Software Studio is a fully functional AI software building tool that leverages multiple Claude Code CLI personas orchestrated through LangGraph. The system implements a human-in-the-loop workflow with rigorous QA and testing at every stage.

## Architecture

The system uses a **Multi-Account, Human-in-the-Loop Agentic Pipeline** with four distinct Claude Code CLI personas:

1. **Product Manager (PM)** - Gathers requirements, creates PRDs, manages scope
2. **Architect (ARCH)** - Designs system architecture, creates technical specifications
3. **Engineer (ENG)** - Implements code, follows specifications, writes tests
4. **QA Engineer (QA)** - Tests implementations, validates requirements, reports issues

### Key Features

- **LangGraph Orchestration**: Stateful workflow management with checkpointing
- **Human-in-the-Loop**: Approval gates at critical decision points
- **MCP Integration**: Extensible tool capabilities via Model Context Protocol
- **Streamlit Dashboard**: Real-time monitoring and interaction interface

## Project Structure

```
autonomous_software_studio/
├── src/
│   ├── orchestration/      # LangGraph control plane
│   ├── wrappers/           # Claude CLI wrapper classes
│   ├── personas/           # Agent system prompts
│   └── interfaces/         # Streamlit dashboard
├── docs/                   # Generated artifacts (PRD, specs)
├── tests/
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── config/
│   └── profiles/          # Claude agent profiles
│       ├── pm/
│       ├── arch/
│       ├── eng/
│       └── qa/
├── logs/                  # Execution logs
└── reports/               # QA reports
```

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd autonomous_software_studio
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment:
   ```bash
   cp .env.template .env
   # Edit .env with your API keys
   ```

## Usage

### Starting the Dashboard

```bash
streamlit run src/interfaces/dashboard.py
```

### Running Tests

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests
pytest tests/integration/
```

## Configuration

See `.env.template` for all available configuration options. Each agent persona can use a separate API key for isolation and tracking.

## Development

### Adding a New Persona

1. Create a profile directory in `config/profiles/<persona_name>/`
2. Add system prompt in `src/personas/<persona_name>.py`
3. Register the agent in the LangGraph workflow

### Extending MCP Capabilities

MCP servers can be configured to provide additional tools to agents. See the MCP documentation for integration details.

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting pull requests.
