# Dashboard User Guide

## Overview

The Autonomous Software Studio Dashboard provides a futuristic 2055+ themed web interface for managing AI-powered software development sessions. Built with Streamlit, it offers real-time monitoring, approval workflows, and comprehensive analytics.

## Accessing the Dashboard

**URL:** http://localhost:8501 (default)

**Requirements:**
- Modern web browser (Chrome, Firefox, Safari, Edge)
- JavaScript enabled
- WebSocket support for real-time updates

---

## Navigation

The dashboard features a sidebar navigation with the following pages:

| Page | Description |
|------|-------------|
| Session Management | Create and monitor development sessions |
| Artifact Review | View generated documents and code |
| Approval Interface | Approve or reject with feedback |
| Live Logs | Real-time execution monitoring |
| Metrics & Analytics | Statistics and quality signals |
| GitHub Integration | Repository connection and issues |
| Project Settings | Per-project configuration |
| Agent Account Management | API keys, models, and prompts |

---

## Session Management

### Creating a New Session

1. Navigate to **Session Management**
2. Click **Start New Session** expander
3. Fill in the form:
   - **Mission:** Describe what you want to build
   - **Project Name:** (Optional) Group sessions by project
4. Click **Start Session**

**Example Mission:**
```
Build a REST API for user authentication with JWT tokens,
supporting registration, login, and password reset.
Use Python with FastAPI and PostgreSQL.
```

### Viewing Sessions

Sessions are displayed in two views:

#### List View
Expandable cards showing:
- Session ID
- Mission description
- Current phase
- Status
- Progress bar
- Last updated timestamp

#### Kanban Board
Visual board with columns for each status:
- **Pending** - Created, not started
- **Running** - Active execution
- **Awaiting Approval** - Needs human review
- **Completed** - Successfully finished
- **Failed** - Error occurred
- **Expired** - TTL exceeded

### Filtering Sessions

Use the **Filter by status** dropdown to show only sessions with a specific status.

---

## Artifact Review

### Viewing Artifacts

1. Navigate to **Artifact Review**
2. Select a session from the dropdown
3. Browse artifacts in tabs:

#### PRD Tab
- Product Requirements Document
- User stories and acceptance criteria
- Rendered as Markdown

#### Tech Spec Tab
- Technical Specification
- Architecture and API design
- Rendered as Markdown

#### Code Tab
- Scaffold scripts
- Bug reports (if QA failed)
- Work directory file listing

### Artifact Actions

- **Copy:** Click to copy artifact content
- **Download:** Right-click to save locally
- **Expand:** View full content in modal

---

## Approval Interface

### When to Use

The approval interface is active when a session reaches the **Human Gate** phase (status: `awaiting_approval`).

### Reviewing for Approval

1. Navigate to **Approval Interface**
2. Select the session awaiting approval
3. Review the PRD and Tech Spec in **Artifact Review**
4. Choose an action:

#### Approve & Build
- Click **Approve & Build** button
- Session proceeds to Engineer phase
- Balloons animation confirms approval

#### Request Changes
1. Expand **Request Changes** section
2. Enter detailed feedback
3. Select where to send feedback:
   - **PM** - Revise requirements
   - **Architect** - Revise technical design
4. Click **Submit Feedback**

### Feedback Best Practices

**Good Feedback:**
```
Please add rate limiting to the API specification.
The current design allows unlimited requests which could
lead to abuse. Suggest 100 requests per minute per user.
```

**Poor Feedback:**
```
Not good enough.
```

---

## Live Logs

### Real-Time Monitoring

1. Navigate to **Live Logs**
2. Select a session
3. View execution output in real-time

### Controls

- **Auto refresh:** Toggle for automatic updates (2s interval)
- **Refresh now:** Manual refresh button

### Log Format

```
[2055-01-26 12:00:00] [PM] Starting requirements analysis...
[2055-01-26 12:00:15] [PM] Identified 5 user stories
[2055-01-26 12:00:30] [PM] Creating PRD document...
[2055-01-26 12:01:00] [PM] PRD complete: docs/PRD.md
```

---

## Metrics & Analytics

### Dashboard Metrics

| Metric | Description |
|--------|-------------|
| Total Sessions | All sessions ever created |
| Running | Currently executing sessions |
| Awaiting Approval | Sessions needing review |
| Completed | Successfully finished sessions |
| Failed | Sessions that encountered errors |

### Quality Signals

- **QA Passed:** Number of sessions passing QA
- **Average QA Iterations:** Mean iterations before passing

### Status Breakdown

Table showing count of sessions per status.

---

## GitHub Integration

### Connecting GitHub

1. Navigate to **GitHub Integration**
2. Enter your GitHub Personal Access Token (PAT)
3. Optionally enter your organization/username
4. Click **Save GitHub Settings**

**Required Token Scopes:**
- `repo` - Full repository access
- `read:org` - Organization membership (optional)

### Viewing Repositories

After connecting, you'll see:
- Repository cards with name, description, privacy status
- Search filter for finding specific repos
- **View Details** button for each repo

### Repository Details

Clicking **View Details** shows:
- Open issues count
- Open PRs count
- Default branch
- Languages used

### Issues and Pull Requests

Browse issues and PRs in tabs:
- View issue/PR details
- Create session from issue (auto-populates mission)
- Quick clone command

### Creating Session from Issue

1. Find the relevant issue
2. Click **Create session from issue #X**
3. Session Management opens with pre-filled mission
4. Review and start session

---

## Project Settings

### Project Overview

View all projects with sessions:
- Total sessions per project
- Running/Completed/QA Passed counts

### Project Configuration

For each project, configure:

#### Repository Settings
- **GitHub Repository:** Link to repo (owner/repo)
- **Work Directory:** Local path for project files

#### Automation Settings
- **Auto-commit changes:** Automatically commit agent changes
- **Branch Prefix:** Prefix for auto-created branches (e.g., `auto/`)
- **Default Agent:** Which agent handles initial requests

### Agent Assignments

Assign specific models to each agent for this project:
- Product Manager model
- Architect model
- Engineer model
- QA model

Set priority (1-10) for resource allocation.

---

## Agent Account Management

### Per-Agent Settings

Each agent (PM, ARCH, ENG, QA) has its own tab with settings:

#### Provider & Model
- **Provider:** anthropic (default)
- **Model:** claude-sonnet-4-20250514, claude-opus-4-20250514, etc.

#### Auth & Keys
- **Auth Type:** api_key, token, none
- **API Key:** Anthropic API key (masked)
- **Auth Token:** Alternative token auth
- **Token Env Var:** Environment variable name
- **Account Label:** Human-readable label
- **Claude Profile Dir:** Custom profile directory

#### Daily Usage
- **Usage Unit:** runs, sessions, minutes
- **Daily Limit:** Maximum usage (0 = unlimited)
- **Hard stop:** Block when limit reached
- **Usage today:** Current usage counter
- **Reset usage:** Manual counter reset

#### Custom Environment Variables
Data editor for adding custom env vars per agent.

### Persona Prompts

#### Viewing Current Prompt
- Active prompt path displayed
- Full prompt content in text area

#### Editing Prompts
1. Modify prompt in text area
2. Add optional version note
3. Click **Save new prompt version**

#### Version History
- List of all prompt versions
- Select version to preview
- **Revert to selected version** button

---

## UI Theme

### Futuristic 2055+ Design

The dashboard features a cyberpunk-inspired dark theme:

#### Colors
| Element | Color | Hex |
|---------|-------|-----|
| Background | Near Black | #0a0a0f |
| Surface | Dark Gray | #12121a |
| Text Primary | Light Gray | #e8e8f0 |
| Accent (Cyan) | Neon Cyan | #00f0ff |
| Accent (Magenta) | Neon Magenta | #ff00e5 |
| Success | Neon Green | #00ff9d |

#### Fonts
- **Headings:** Orbitron (futuristic)
- **Body:** Rajdhani (modern)
- **Code:** Share Tech Mono

#### Effects
- Animated grid background
- Neon glow on hover
- Holographic card animations
- Gradient scrollbars

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `R` | Refresh page |
| `Ctrl+Enter` | Submit form |
| `Esc` | Close modal/expander |

---

## Troubleshooting

### Page Not Loading

1. Check if services are running:
   ```bash
   docker compose ps
   ```
2. Check dashboard logs:
   ```bash
   docker compose logs dashboard
   ```
3. Verify port is available:
   ```bash
   curl http://localhost:8501/_stcore/health
   ```

### Session Not Starting

- Verify Claude CLI is installed in container
- Check API key is configured
- Review orchestrator logs for errors

### Artifacts Not Showing

- Session may still be in early phase
- Check if session status is `running`
- Wait for phase completion

### Slow Performance

- Reduce auto-refresh frequency
- Close unused browser tabs
- Check container resource usage

---

## Best Practices

### Session Management
- Use descriptive mission statements
- Group related sessions with project names
- Clean up old/failed sessions regularly

### Approval Workflow
- Review both PRD and Tech Spec before approving
- Provide specific, actionable feedback when rejecting
- Test artifacts locally if possible

### Monitoring
- Enable auto-refresh only when actively monitoring
- Use Live Logs for debugging issues
- Check Metrics regularly for quality trends

### Security
- Use separate API keys per agent when possible
- Set usage limits to prevent runaway costs
- Rotate API keys periodically
