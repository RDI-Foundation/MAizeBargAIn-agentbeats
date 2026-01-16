# AgentBeats Competition Submission

## Meta-Game Bargaining Evaluator

**Submission Type**: Green Agent (Evaluator)
**Domain**: Multi-Agent Negotiation
**Docker Image**: `ghcr.io/gsmithline/tutorial-agent-beats-comp:latest`

---

## Abstract

We present a **green agent** for the AgentBeats platform that implements an Empirical Game-Theoretic Analysis (EGTA) framework for evaluating negotiation agents. Rather than testing agents against fixed opponents, our evaluator computes the **Maximum Entropy Nash Equilibrium (MENE)** of the meta-game to measure how well-adapted each agent is to strategic competition.

The framework is based on computational game theory methodology developed by Zun Li and Michael Wellman, enabling rigorous, reproducible evaluation of agent strategies.

---

## Competition Requirements Compliance

### Green Agent Requirements

| Requirement | Implementation |
|-------------|----------------|
| A2A Protocol | Full compliance via `a2a-sdk` |
| Assessment Handling | `assessment_request` → simulation → artifact |
| Docker Container | Multi-stage build, GHCR published |
| Reproducibility | Stateless, fresh state per assessment |
| Result Artifacts | JSON with per-agent metrics |

### Registration

1. **Docker Image**: Published to GitHub Container Registry
   ```
   ghcr.io/gsmithline/tutorial-agent-beats-comp:latest
   ```

2. **Deployment**: Google Cloud Run compatible
   ```bash
   gcloud run deploy bargaining-green-agent \
     --image ghcr.io/gsmithline/tutorial-agent-beats-comp:latest \
     --region=us-central1 \
     --allow-unauthenticated \
     --memory=4Gi
   ```

3. **Platform Registration**: Register the Cloud Run URL at agentbeats.dev

---

## How the Evaluation Works

### Assessment Flow

```
1. Green agent receives assessment_request with:
   - participants.challenger = purple agent URL
   - config = evaluation parameters

2. Green agent builds agent roster:
   - Challenger (remote purple agent)
   - Baseline agents: soft, tough, aspiration, walk
   - RL agents: nfsp, rnad (when available)

3. Pairwise simulation:
   - For each (agent_i, agent_j) pair
   - Run N games in OpenSpiel negotiation environment
   - Record payoffs and outcomes

4. Meta-game analysis:
   - Construct payoff matrix where M[i][j] = agent i's average payoff against agent j
   - Solve for MENE via MILP
   - Compute regret and welfare metrics

5. Return artifact with results
```

### The Negotiation Environment

Based on OpenSpiel's negotiation game:

- **Items**: 3 types with quantities [7, 4, 1]
- **Valuations**: Private, drawn uniformly from [1, 100]
- **BATNAs**: Private outside options
- **Discount**: Configurable (0.9 or 0.98 per round)
- **Rounds**: Configurable (3 or 5 maximum)

Each game is a multi-round alternating-offer protocol where agents propose item divisions until one accepts or the deadline hits.

### Game Configurations

| Config | Discount (γ) | Rounds (R) | Use Case |
|--------|--------------|------------|----------|
| BG4 | 0.9 | 3 | High time pressure |
| BG5 | 0.98 | 3 | Low time pressure, short |
| BG6 | 0.98 | 5 | Low time pressure, long |

Pre-trained NFSP and RNAD checkpoints are included for all configurations.

### Baseline Agent Pool

| Agent | Strategy |
|-------|----------|
| `soft` | Always accepts any offer |
| `tough` | Proposes minimal offers, rarely concedes |
| `aspiration` | Gradually lowers aspirations over rounds |
| `walk` | Takes BATNA if offers don't improve quickly |
| `nfsp` | Neural Fictitious Self-Play (learned) |
| `rnad` | Regularized Nash Dynamics (learned) |

---

## Evaluation Metrics

### Primary Metric: MENE Regret

The regret measures the deviation incentive for each pure strategy:

```
Regret(π) = max(0, u(π, σ*) - u(σ*))
```

Where:
- u(π, σ*) = expected payoff for pure strategy π against the MENE mixture
- u(σ*) = expected payoff at equilibrium

**Interpretation**: Lower regret = better adapted to strategic competition. Zero regret means the strategy is in the equilibrium support or weakly dominated.

### Welfare Metrics

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| **UW** | p₁ + p₂ | Total value created |
| **NW** | √(p₁ × p₂) | Balanced value (Pareto-fair) |
| **NWA** | √(max(0,p₁-b₁) × max(0,p₂-b₂)) | Surplus over BATNAs |
| **EF1** | Boolean | Envy-free up to one item |

All metrics are normalized as percentages of calibration constants.

### Result Format

Results include bootstrap means with standard errors (following the paper's format: mean±SE):

```json
{
  "summary": {
    "num_agents": 5,
    "mene_regret_mean": 2.34,
    "uw_percent_mean": 87.2,
    "nw_percent_mean": 82.1,
    "nwa_percent_mean": 45.3,
    "ef1_percent_mean": 91.5
  },
  "per_agent": [
    {
      "agent_name": "challenger",
      "mene_regret": 1.2,
      "mene_regret_se": 0.15,
      "uw_percent": 89.1,
      "uw_percent_se": 0.08,
      "nw_percent": 85.3,
      "nw_percent_se": 0.12,
      "nwa_percent": 52.1,
      "nwa_percent_se": 0.18,
      "ef1_percent": 94.2,
      "ef1_percent_se": 0.25
    }
  ],
  "mene_distribution": {
    "challenger": 0.25,
    "soft": 0.15,
    "tough": 0.20,
    "aspiration": 0.25,
    "walk": 0.15
  }
}
```

**Note**: Standard errors are computed via bootstrap resampling (default 100 iterations), following the methodology from [Wiedenbeck et al., 2014].

---

## Configuration Options

### Assessment Request

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
    "challenger_circle": 5,
    "challenger_label": "my_agent_v1",
    "remote_agents": {
      "agent_b": "https://another-agent.example.com"
    }
  }
}
```

### Parameter Reference

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `games` | 50 | 10-200 | Games per pair |
| `max_rounds` | 5 | 3-10 | Negotiation rounds |
| `discount` | 0.98 | 0.9-1.0 | Time pressure |
| `bootstrap` | 100 | 50-500 | MENE bootstrap iterations |
| `challenger_circle` | 0 | 0-6 | LLM prompt level |

---

## LLM Agent Support

For LLM-based purple agents, the green agent provides structured prompts via "circles":

| Circle | Content |
|--------|---------|
| 0 | Basic game rules |
| 1 | + Valuations and actions |
| 2 | + BATNA emphasis |
| 3 | + Step-by-step reasoning |
| 4 | + Common mistake list |
| 5 | + Error prevention examples |
| 6 | + Advanced strategic guidance |

Set `challenger_circle` to inject these prompts into observations sent to your agent.

---

## Dependencies

- **Python 3.11**: Required (OpenSpiel binary is compiled for Python 3.11)
- **OpenSpiel**: Custom build with negotiation game (bundled)
- **CVXPY + ECOS**: MENE computation via MILP
- **A2A SDK**: Agent communication protocol
- **PyTorch**: For NFSP agent checkpoints
- **JAX/Haiku**: For RNAD agent checkpoints

### RL Checkpoints

Pre-trained checkpoints are included in `scenarios/bargaining/rl_agent_checkpoints/`:

| Agent | Format | Configs |
|-------|--------|---------|
| NFSP | PyTorch (`.pt`) | BG4, BG5, BG6 |
| RNAD | Pickle (`.pkl`) | BG4, BG5, BG6 |

---

## References

1. Li, Z., & Wellman, M. P. (2023). "Empirical Game-Theoretic Analysis of Adaptive Bargaining Strategies"
2. Wellman, M. P. (2016). "Putting the agent in agent-based modeling." Autonomous Agents and Multi-Agent Systems.
3. Lewis, M., et al. (2017). "Deal or No Deal? End-to-End Learning for Negotiation Dialogues." EMNLP.
4. Lanctot, M., et al. (2019). "OpenSpiel: A Framework for Reinforcement Learning in Games."

---

## Authors

Submission for the AgentBeats x AgentX Competition 2025.

**Repository**: https://github.com/gsmithline/tutorial-agent-beats-comp
