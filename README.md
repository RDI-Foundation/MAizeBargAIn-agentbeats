# Meta-Game Bargaining Evaluator

**AgentBeats Competition Submission: Green Agent for Multi-Agent Negotiation Assessment**

This repository contains a **green agent** that implements an Empirical Game-Theoretic Analysis (EGTA) framework for evaluating negotiation agents. Based on methodology from Zun Li and Michael Wellman, the agent computes Maximum Entropy Nash Equilibrium (MENE) to rigorously assess purple agent strategies.

## Quick Start

### Option A: Run Locally

```bash
# Clone and setup
git clone https://github.com/gsmithline/tutorial-agent-beats-comp.git
cd tutorial-agent-beats-comp
uv sync

# Set environment variables
cp sample.env .env
# Add your API key to .env

# Run a local assessment
uv run python -m scenarios.bargaining.bargaining_green once --config '{"challenger_url": "https://your-purple-agent.com", "games": 10}'
```

### Option B: Deploy to Cloud Run

```bash
# Deploy using the pre-built Docker image
gcloud run deploy bargaining-green-agent \
  --image ghcr.io/gsmithline/tutorial-agent-beats-comp:latest \
  --region=us-central1 \
  --allow-unauthenticated \
  --memory=4Gi

# Or build from source
gcloud run deploy bargaining-green-agent \
  --source . \
  --region=us-central1 \
  --allow-unauthenticated
```

### Option C: Register on AgentBeats Platform

1. Deploy your green agent (Option B above)
2. Navigate to [agentbeats.dev](https://agentbeats.dev)
3. Register your agent with the Cloud Run URL
4. Run assessments against purple agents via the platform

---

## How It Works

### The Meta-Game Framework

Unlike traditional benchmarks that measure agents in isolation, meta-game analysis evaluates agents within their **strategic ecosystem**:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Purple Agent   │    │   Green Agent    │    │  Baseline Pool  │
│  (Challenger)   │───▶│  (Evaluator)     │◀───│  soft, tough,   │
└─────────────────┘    │                  │    │  aspiration,    │
                       │  1. Build Roster │    │  walk, nfsp,    │
                       │  2. Run N² Games │    │  rnad           │
                       │  3. MENE Solve   │    └─────────────────┘
                       │  4. Compute      │
                       │     Metrics      │
                       └────────┬─────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Evaluation    │
                       │   Results       │
                       │  - MENE Regret  │
                       │  - Welfare %    │
                       │  - Fairness %   │
                       └─────────────────┘
```

**Key Insight**: A purple agent isn't just tested against fixed opponents. It joins a population of strategies, and we find the Nash equilibrium of the meta-game to measure how well-adapted it is.

### Evaluation Process

1. **Roster Construction**: Your purple agent joins baseline agents (soft, tough, aspiration, walk) and optionally RL agents (NFSP, RNaD)

2. **Pairwise Simulation**: Every agent pair plays N games in OpenSpiel's negotiation environment:
   - 3 item types with private valuations
   - Private BATNAs (outside options)
   - Discount factor for time pressure
   - Multi-round alternating offers

3. **MENE Computation**: Solve for the Maximum Entropy Nash Equilibrium using MILP (CVXPY)

4. **Metrics Extraction**: Compute regret, welfare, and fairness metrics weighted by the equilibrium

### Metrics

| Metric | What It Measures | Good Score |
|--------|------------------|------------|
| **MENE Regret** | Incentive to deviate from equilibrium | < 5 |
| **UW%** | Total value created (utilitarian) | > 80% |
| **NW%** | Balanced value distribution | > 75% |
| **NWA%** | Surplus over outside options | > 40% |
| **EF1%** | Envy-free allocations | > 90% |

---

## Assessment Configuration

### Assessment Request Format

Per the A2A protocol, send an assessment request to the green agent:

```json
{
  "participants": {
    "challenger": "https://your-purple-agent.example.com"
  },
  "config": {
    "games": 50,
    "max_rounds": 5,
    "discount": 0.98,
    "bootstrap": 100,
    "challenger_circle": 5
  }
}
```

### Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `games` | 50 | Number of games per agent pair |
| `max_rounds` | 5 | Maximum negotiation rounds |
| `discount` | 0.98 | Per-round discount factor |
| `bootstrap` | 100 | Bootstrap iterations for MENE |
| `challenger_circle` | 0 | Prompt sophistication level (0-6) |
| `challenger_label` | "challenger" | Label for your agent in results |
| `remote_agents` | {} | Additional remote agents `{"label": "url"}` |

### Prompt Circles (LLM Agents)

For LLM-based purple agents, the green agent injects structured prompts:

| Circle | Focus |
|--------|-------|
| 0-1 | Basic rules, valuations, available actions |
| 2 | BATNA comparison emphasis |
| 3 | Step-by-step reasoning framework |
| 4 | Common mistake awareness |
| 5-6 | Detailed error prevention with examples |

---

## Building a Purple Agent

Your purple agent must:

1. **Implement A2A protocol** - Expose an A2A server endpoint
2. **Handle negotiation messages** - Receive observations with valuations, BATNAs, and offers
3. **Return valid actions** - Propose offers or accept/reject

### Expected Message Format

The green agent sends observations like:

```json
{
  "role": "row",
  "round": 2,
  "valuations": [45, 72, 33],
  "batna": 85,
  "quantities": [7, 4, 1],
  "last_offer": [3, 2, 0],
  "history": [...]
}
```

Your agent responds with an action:

```json
{
  "action": "propose",
  "offer": [4, 2, 1]
}
```

Or:

```json
{
  "action": "accept"
}
```

---

## Local Development

### Running the Green Agent Server

```bash
# Start the A2A server
uv run python -m scenarios.bargaining.bargaining_green serve \
  --host 0.0.0.0 \
  --port 8080

# In another terminal, send an assessment request
curl -X POST http://localhost:8080/a2a \
  -H "Content-Type: application/json" \
  -d '{"type": "assessment_request", "participants": {...}, "config": {...}}'
```

### Running a Single Assessment

```bash
uv run python -m scenarios.bargaining.bargaining_green once \
  --config '{"challenger_url": "https://...", "games": 10}'
```

### Docker Build

```bash
# Build locally
docker build -t bargaining-green-agent .

# Run locally
docker run -p 8080:8080 bargaining-green-agent
```

---

## Project Structure

```
scenarios/bargaining/
├── bargaining_green.py      # Main green agent implementation
├── bargaining_env/
│   ├── agents/              # Baseline negotiation agents
│   │   ├── soft.py          # Always-accept agent
│   │   ├── tough.py         # Minimal-offer agent
│   │   ├── aspiration.py    # Gradual-concession agent
│   │   ├── walk.py          # BATNA-preferring agent
│   │   ├── nfsp.py          # Neural Fictitious Self-Play
│   │   └── rnad.py          # Regularized Nash Dynamics
│   ├── pyspiel_runner.py    # OpenSpiel game interface
│   ├── mene_solver.py       # MENE computation via MILP
│   └── run_entire_matrix.py # Matrix simulation orchestrator
└── open_spiel/              # Custom OpenSpiel with negotiation game
```

---

## Technical Details

### OpenSpiel Integration

This repository includes a custom OpenSpiel build with the negotiation/bargaining game. The Docker build compiles OpenSpiel from source with:

- Abseil C++ library
- pybind11 Python bindings
- Double Dummy Solver (for bridge, included in full build)

### MENE Solver

The Maximum Entropy Nash Equilibrium is computed using:

- CVXPY for convex optimization
- ECOS_BB or GLPK_MI as MILP solvers
- Bootstrap resampling for robustness

---

## References

1. Li, Z., & Wellman, M. P. (2023). "Empirical Game-Theoretic Analysis of Adaptive Bargaining Strategies"
2. Wellman, M. P. (2016). "Putting the agent in agent-based modeling." Autonomous Agents and Multi-Agent Systems.
3. Lewis, M., et al. (2017). "Deal or No Deal? End-to-End Learning for Negotiation Dialogues." EMNLP.
4. Lanctot, M., et al. (2019). "OpenSpiel: A Framework for Reinforcement Learning in Games." arXiv:1908.09453.

---

## License

Apache 2.0

---

## AgentBeats Competition

This is a submission for the **AgentBeats x AgentX Competition 2025**.

- **Agent Type**: Green (Evaluator)
- **Domain**: Multi-agent negotiation / bargaining
- **Methodology**: Empirical Game-Theoretic Analysis with MENE
- **Docker Image**: `ghcr.io/gsmithline/tutorial-agent-beats-comp:latest`
