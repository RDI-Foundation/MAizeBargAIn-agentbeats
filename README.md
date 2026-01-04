# Meta-Game Bargaining Evaluator

**AgentBeats Competition Submission: Green Agent for Multi-Agent Negotiation Assessment**

This repository contains a **green agent** that implements the **Empirical Meta-Game Analysis** framework from Smithline, Mascioli, Chakraborty & Wellman (2025) for evaluating negotiation agents. The agent computes **Maximum Entropy Nash Equilibrium (MENE)** to rigorously assess purple agent strategies within their strategic ecosystem.

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

## The Meta-Game Framework

This green agent implements the **Empirical Meta-Game Analysis** methodology introduced by Li & Wellman (2024) and applied to LLM bargaining evaluation in Smithline et al. (2025).

### Why Meta-Game Analysis?

Traditional benchmarks evaluate agents in isolation against fixed opponents. But in strategic environments, an agent's performance inherently depends on the behavior of other agents. Meta-game analysis addresses this by:

1. **Constructing an empirical game** over the space of agent strategies
2. **Computing Nash equilibria** to identify stable population mixtures
3. **Evaluating agents at equilibrium** to measure how well-adapted they are to strategic competition

### Framework Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Purple Agent   │    │   Green Agent    │    │  Baseline Pool  │
│  (Challenger)   │───▶│  (Evaluator)     │◀───│  soft, tough,   │
└─────────────────┘    │                  │    │  aspire, walk,  │
                       │  1. Build Roster │    │  nfsp, rnad     │
                       │  2. Simulate N²  │    └─────────────────┘
                       │     Matchups     │
                       │  3. MENE Solve   │
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

### Evaluation Process

**Step 1: Agent Roster Construction**
- Your purple agent joins a pool of baseline strategies
- Heuristic agents: `soft` (accepts any offer), `tough` (minimal offers), `aspire` (concession schedule), `walk` (takes BATNA)
- RL-derived policies: `nfsp` (Neural Fictitious Self-Play), `rnad` (Regularized Nash Dynamics)

**Step 2: Pairwise Simulation**
- For each ordered pair (i, j), simulate N games with agent i as row player and j as column player
- Uses OpenSpiel's negotiation game with:
  - T=3 item types with quantities (7, 4, 1)
  - Private valuations drawn uniformly from [1, 100]
  - Private BATNAs (outside options)
  - Discount factor γ ∈ {0.9, 0.98} per round
  - Maximum R ∈ {3, 5} rounds

**Game Configurations (from paper)**

| Config | Discount (γ) | Rounds (R) | Description |
|--------|--------------|------------|-------------|
| BG4 | 0.9 | 3 | High time pressure, short horizon |
| BG5 | 0.98 | 3 | Low time pressure, short horizon |
| BG6 | 0.98 | 5 | Low time pressure, long horizon |

Pre-trained NFSP and RNAD checkpoints are provided for all three configurations.

**Step 3: Payoff Matrix & MENE**
- Construct symmetric payoff matrix where M[i][j] = agent i's average payoff when playing against agent j
- Solve for **Maximum Entropy Nash Equilibrium** using MILP (CVXPY)
- Bootstrap resampling (default 100 iterations) for statistical robustness

**Step 4: Metrics Computation**
- Compute regret and welfare metrics weighted by the MENE mixture

---

## Evaluation Metrics

### MENE Regret (Primary Metric)

The regret of a pure strategy π at Nash equilibrium σ* measures the deviation incentive:

```
Regret(π) = max(0, u(π, σ*) - u(σ*))
```

Where:
- u(π, σ*) = expected payoff for pure strategy π against the equilibrium mixture
- u(σ*) = expected payoff at equilibrium (playing the mixture)

**Interpretation**: Lower regret means the agent is better adapted to the equilibrium. An agent with zero regret has no incentive to deviate—it is either in the equilibrium support or weakly dominated. Positive regret indicates the strategy outperforms the equilibrium mixture (which should be near-zero for a correctly computed MENE).

### Welfare Metrics

| Metric | Formula | Description |
|--------|---------|-------------|
| **UW (Utilitarian Welfare)** | u₁ + u₂ | Total value created by both players |
| **NW (Nash Welfare)** | √(u₁ × u₂) | Geometric mean - balances efficiency and equity |
| **NW+ (Nash Welfare Advantage)** | √(max(0, u₁-b₁) × max(0, u₂-b₂)) | Surplus over BATNAs |
| **EF1 (Envy-Free up to 1 item)** | Boolean per game | Fairness: envy eliminable by removing one item |

All welfare metrics are normalized against calibration constants for cross-comparison.
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
| `max_rounds` | 5 | Maximum negotiation rounds (R) |
| `discount` | 0.98 | Per-round discount factor (γ) |
| `bootstrap` | 100 | Bootstrap iterations for MENE |
| `challenger_circle` | 0 | Prompt sophistication level (0-6) |
| `challenger_label` | "challenger" | Label for your agent in results |
| `remote_agents` | {} | Additional remote agents `{"label": "url"}` |

### Prompt Circles (LLM Agents)

The green agent provides structured prompts to LLM-based purple agents via "circles" - a hierarchical prompting framework:

| Circle | Content |
|--------|---------|
| 0 | Bare rules: items, valuations, BATNA, actions |
| 1 | + Objective specification (maximize outcome) |
| 2 | + Worked numeric example of offer evaluation |
| 3 | + Step-by-step routine: assess, compare, decide |
| 4 | + Five common negotiation mistakes to avoid |
| 5 | + Quick numeric checks against those mistakes |
| 6 | + Strategic inference from opponent's offers |

Set `challenger_circle` to inject these prompts into observations sent to your agent.

---

## Building a Purple Agent

Your purple agent must:

1. **Implement A2A protocol** - Expose an A2A server endpoint
2. **Handle negotiation messages** - Receive observations with valuations, BATNAs, and offers
3. **Return valid actions** - Propose offers or accept/walk

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
{"action": "COUNTEROFFER", "offer": [4, 2, 1]}
```

Or:

```json
{"action": "ACCEPT"}
```

Or:

```json
{"action": "WALK"}
```

### Common Mistakes to Avoid

From our analysis, these are the five key mistakes that LLM negotiators make:

1. **M1**: Making an offer worse than your previous offer
2. **M2**: Making an offer worse for you than your BATNA
3. **M3**: Offering no items or all items (extreme divisions)
4. **M4**: Accepting an offer worse than your BATNA
5. **M5**: Walking away from an offer better than your BATNA

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
│   │   ├── aspiration.py    # Concession-schedule agent
│   │   ├── walk.py          # BATNA-preferring agent
│   │   ├── nfsp.py          # Neural Fictitious Self-Play
│   │   └── rnad.py          # Regularized Nash Dynamics
│   ├── pyspiel_integration.py # Game parameter builder
│   ├── pyspiel_runner.py    # OpenSpiel game interface
│   ├── mene_solver.py       # MENE computation via MILP
│   └── run_entire_matrix.py # Matrix simulation orchestrator
├── rl_agent_checkpoints/    # Pre-trained RL policies
│   ├── nfsp/                # NFSP checkpoints (bg4, bg5, bg6)
│   └── rnad/                # RNAD checkpoints (bg4, bg5, bg6)
└── open_spiel/              # Custom OpenSpiel with negotiation game
```

---

## Technical Details

### OpenSpiel Integration

This repository includes a custom OpenSpiel build with the negotiation/bargaining game. The Docker build compiles OpenSpiel from source with:

- Abseil C++ library
- pybind11 Python bindings
- Double Dummy Solver (for bridge, included in full build)

**Loading the Game Correctly**

Always use `build_negotiation_params()` from `pyspiel_integration.py` to ensure correct game loading:

```python
from scenarios.bargaining.bargaining_env.pyspiel_integration import (
    build_negotiation_params,
    try_load_pyspiel_game
)

params = build_negotiation_params(
    discount=0.98,
    max_rounds=3,
    num_items=3,
    item_quantities=(7, 4, 1),
    min_value=1,
    max_value=100,
    max_quantity=10,
)
game = try_load_pyspiel_game(params)
```

> **Note**: The `item_quantities` parameter must use comma-separated values internally (e.g., `"7,4,1"`). The helper function handles this automatically.

### MENE Solver

The Maximum Entropy Nash Equilibrium is computed using:

- CVXPY for convex optimization
- ECOS_BB or GLPK_MI as MILP solvers
- Bootstrap resampling for robustness (following Wiedenbeck et al., 2014)

### RL Agent Checkpoints

Pre-trained checkpoints are available for both NFSP and RNAD agents:

| Agent | BG4 | BG5 | BG6 |
|-------|-----|-----|-----|
| NFSP | `nfsp_bg4.pt` | `nfsp_ng5.pt` | `nfsp_bg6.pt` |
| RNAD | `rnad_bg4.pkl` | `rnad_bg5.pkl` | `rnad_bg6.pkl` |

The checkpoints are automatically selected based on the game configuration (discount and max_rounds).

---

## References

1. **Smithline, G., Mascioli, C., Chakraborty, M., & Wellman, M. P.** (2025). "Measuring Competition and Cooperation in LLM Bargaining: An Empirical Meta-Game Analysis." University of Michigan.

2. **Li, Z., & Wellman, M. P.** (2024). "A Meta-Game Evaluation Framework for Deep Multiagent Reinforcement Learning." IJCAI.

3. **Wellman, M. P., Tuyls, K., & Greenwald, A.** (2025). "Empirical Game-Theoretic Analysis: A Survey." JAIR.

4. **Lewis, M., et al.** (2017). "Deal or No Deal? End-to-End Learning for Negotiation Dialogues." EMNLP.

5. **Lanctot, M., et al.** (2019). "OpenSpiel: A Framework for Reinforcement Learning in Games." arXiv:1908.09453.

---

## License

Apache 2.0

---

## AgentBeats Competition

This is a submission for the **AgentBeats x AgentX Competition 2025**.

- **Agent Type**: Green (Evaluator)
- **Domain**: Multi-agent negotiation / bargaining
- **Methodology**: Empirical Meta-Game Analysis with MENE
- **Docker Image**: `ghcr.io/gsmithline/tutorial-agent-beats-comp:latest`
- **Authors**: Based on research from the University of Michigan Strategic Reasoning Group
