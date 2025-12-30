# AgentBeats Competition Submission: Meta-Game Bargaining Evaluator

## Abstract

We present a **green agent** for the AgentBeats platform that implements an Empirical Game-Theoretic Analysis (EGTA) framework for evaluating negotiation agents in a multi-item bargaining scenario. The framework is based on the computational game theory methodology developed by Wellman and colleagues, enabling rigorous evaluation of agent strategies within a meta-game context.

## Key Features

### Meta-Game Analysis Pipeline
- **Pairwise Simulation**: Evaluates submitted agents against a pool of baseline negotiators (soft, tough, aspiration, walk) and optionally RL-trained agents (NFSP, RNaD)
- **Maximum Entropy Nash Equilibrium (MENE)**: Computes the unique maximum-entropy Nash equilibrium to identify stable population mixtures
- **Regret Analysis**: Measures each agent's deviation incentive from the equilibrium mixture
- **Welfare Metrics**: Reports utilitarian welfare (UW), Nash welfare (NW), surplus over BATNA (NWA), and fairness (EF1)

### Bargaining Environment
- OpenSpiel-based negotiation game with configurable parameters
- 3-item division with private valuations and outside options (BATNAs)
- Discount factor modeling time pressure
- Support for multi-round alternating offers

### LLM Agent Support
- 7-level "prompt circle" system providing progressively sophisticated reasoning scaffolds
- Error-prevention guidance based on common negotiation mistakes
- Compatible with Gemini, OpenAI, Anthropic, and OpenAI-compatible endpoints

## Technical Architecture

```
Purple Agent (Challenger)
        │
        ▼
┌───────────────────────────────────────────┐
│           BargainingGreenAgent            │
│  ┌─────────────────────────────────────┐  │
│  │     run_matrix_pipeline()           │  │
│  │  • Build agent roster               │  │
│  │  • Simulate N² pairwise matchups    │  │
│  │  • Record traces & payoffs          │  │
│  └─────────────────────────────────────┘  │
│  ┌─────────────────────────────────────┐  │
│  │     run_analysis()                  │  │
│  │  • Bootstrap payoff matrix          │  │
│  │  • Solve MENE via MILP              │  │
│  │  • Compute regrets & welfare        │  │
│  └─────────────────────────────────────┘  │
│  ┌─────────────────────────────────────┐  │
│  │     run_metagame_analysis()         │  │
│  │  • Aggregate metrics                │  │
│  │  • Return JSON artifact             │  │
│  └─────────────────────────────────────┘  │
└───────────────────────────────────────────┘
        │
        ▼
   Evaluation Results
```

## Evaluation Criteria

| Metric | Interpretation |
|--------|----------------|
| MENE Regret | Lower = better adapted to equilibrium |
| UW% | Higher = more total value created |
| NW% | Higher = more equitable value distribution |
| NWA% | Higher = more surplus over outside options |
| EF1% | Higher = fairer allocations |

## Dependencies

- OpenSpiel (bundled, built from source for pyspiel)
- CVXPY with ECOS_BB/GLPK_MI solvers for MENE computation
- A2A SDK for agent communication
- PyTorch (optional, for RL agent checkpoints)

## Deployment

The green agent is containerized via Docker and deployable to Google Cloud Run:

```bash
gcloud run deploy bargaining-green-agent \
  --source . \
  --region=us-central1 \
  --allow-unauthenticated
```

## Usage Example

```json
{
  "participants": {
    "challenger": "https://my-purple-agent.example.com"
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

## References

1. Li, Z., & Wellman, M. P. "Empirical Game-Theoretic Analysis of Adaptive Bargaining Strategies"
2. Wellman, M. P. (2016). "Putting the agent in agent-based modeling." Autonomous Agents and Multi-Agent Systems.
3. Lewis, M., et al. (2017). "Deal or No Deal? End-to-End Learning for Negotiation Dialogues." EMNLP.

## Authors

Submission for the AgentBeats x AgentX Competition 2025.
