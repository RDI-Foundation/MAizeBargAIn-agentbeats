import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
import random


def _ensure_dir(p: str | Path) -> Path:
    path = Path(p)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_meta(input_dir: Path) -> Dict[str, Any]:
    return json.loads((input_dir / "meta.json").read_text())


def _load_payoffs(input_dir: Path) -> Dict[str, Any]:
    return json.loads((input_dir / "payoffs.json").read_text())


def _build_matrix(agents: List[str], payoffs: Dict[str, Any]) -> List[List[float]]:
    n = len(agents)
    M = [[0.0 for _ in range(n)] for _ in range(n)]
    for i, ai in enumerate(agents):
        for j, aj in enumerate(agents):
            key = f"{ai}__vs__{aj}"
            cell = payoffs.get(key, None)
            if cell is None:
                continue
            M[i][j] = float(cell.get("row_mean_payoff", 0.0))
    return M


def run_analysis(
    *,
    input_dir: str,
    output_dir: str,
	discount_factor: float = 0.98,
	num_bootstrap: int = 100,
	norm_constants: Dict[str, float] | None = None,
	random_seed: int | None = 42,
) -> Dict[str, Any]:
	"""Empirical meta-game analysis with bootstrapping:
	- Build symmetric payoff matrix from per-match traces via bootstrap resampling
	- Compute MENE using MILP
	- Compute NE regrets
	- Evaluate normalized UW, NW, NWA and EF1 frequency against MENE for each agent
	Repeat for num_bootstrap samples and write results.
	"""
	in_dir = Path(input_dir)
	out_dir = _ensure_dir(output_dir)

	meta = _load_meta(in_dir)
	agents: List[str] = list(meta.get("agents", []))
	if len(agents) == 0:
		raise ValueError("No agents found for meta-game analysis.")
	num_agents = len(agents)

	# Normalization constants: user-provided
	norm = {
		"UW": float(norm_constants.get("UW")) if norm_constants and "UW" in norm_constants else 1.0,
		"NW": float(norm_constants.get("NW")) if norm_constants and "NW" in norm_constants else 1.0,
		"NWA": float(norm_constants.get("NWA")) if norm_constants and "NWA" in norm_constants else 1.0,
	}

	# Load all ordered traces once
	traces_dir = in_dir / "traces"
	if not traces_dir.exists():
		raise ValueError(f"Trace directory not found: {traces_dir}")

	def load_records(pair_key: str) -> List[Dict[str, Any]]:
		records: List[Dict[str, Any]] = []
		p = traces_dir / f"{pair_key}.jsonl"
		if not p.exists():
			return records
		with p.open("r") as f:
			for line in f:
				line = line.strip()
				if not line:
					continue
				try:
					records.append(json.loads(line))
				except Exception:
					continue
		return records

	ordered_data: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
	for i, ai in enumerate(agents):
		for j, aj in enumerate(agents):
			key = f"{ai}__vs__{aj}"
			ordered_data[(i, j)] = load_records(key)

	rng = random.Random(random_seed)

	def bootstrap_sample(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
		if not items:
			return []
		return [items[rng.randrange(0, len(items))] for _ in range(len(items))]

	def ef1_from_record(rec: Dict[str, Any]) -> int:
		ef1 = rec.get("ef1", None)
		if isinstance(ef1, bool):
			return 1 if ef1 else 0
		return 0

	def ordered_stats(records: List[Dict[str, Any]]) -> Dict[str, float]:
		if not records:
			return {
				"row_mean": 0.0,
				"col_mean": 0.0,
				"uw_norm": 0.0,
				"nw_norm": 0.0,
				"nwa_norm": 0.0,
				"ef1_freq": 0.0,
			}
		sum_row = 0.0
		sum_col = 0.0
		sum_uw = 0.0
		sum_nw = 0.0
		sum_nwa = 0.0
		acc_count = 0
		ef1_count = 0
		for rec in records:
			p1 = float(rec.get("payoff1", 0.0))
			p2 = float(rec.get("payoff2", 0.0))
			sum_row += p1
			sum_col += p2
			# welfare (discounted)
			uw = p1 + p2
			nw = (p1 * p2) ** 0.5 if p1 >= 0.0 and p2 >= 0.0 else 0.0
			# NWA with discount applied to BATNAs based on round (if available)
			w1 = float(rec.get("b1", 0.0))
			w2 = float(rec.get("b2", 0.0))
			round_idx = rec.get("round", None)
			disc = 1.0
			if isinstance(round_idx, int) and round_idx >= 1:
				disc = discount_factor ** (round_idx - 1)
			s1 = max(0.0, p1 - w1 * disc)
			s2 = max(0.0, p2 - w2 * disc)
			nwa = (s1 * s2) ** 0.5
			sum_uw += uw / max(1e-12, norm["UW"])
			sum_nw += nw / max(1e-12, norm["NW"])
			sum_nwa += nwa / max(1e-12, norm["NWA"])
			if rec.get("accepted", False):
				acc_count += 1
				ef1_count += ef1_from_record(rec)

		n = float(len(records))
		ef1_freq = (ef1_count / max(1, acc_count)) if acc_count > 0 else 0.0
		return {
			"row_mean": sum_row / n,
			"col_mean": sum_col / n,
			"uw_norm": sum_uw / n,
			"nw_norm": sum_nw / n,
			"nwa_norm": sum_nwa / n,
			"ef1_freq": ef1_freq,
		}

	# Require MENE solver; no fallback
	try:
		from scenarios.bargaining.bargaining_env.mene_solver import milp_max_sym_ent_2p, compute_regret  # type: ignore
		import numpy as np  # type: ignore
	except Exception as e:
		raise RuntimeError(f"MENE solver dependencies unavailable: {e}")

	boot_results: List[Dict[str, Any]] = []

	for b in range(max(1, int(num_bootstrap))):
		# Build symmetric payoff matrix via bootstrap
		M = [[0.0 for _ in range(num_agents)] for _ in range(num_agents)]
		# Also precompute per-ordered normalized welfare metrics for agent-level aggregation
		W_uw = [[0.0 for _ in range(num_agents)] for _ in range(num_agents)]
		W_nw = [[0.0 for _ in range(num_agents)] for _ in range(num_agents)]
		W_nwa = [[0.0 for _ in range(num_agents)] for _ in range(num_agents)]
		W_ef1 = [[0.0 for _ in range(num_agents)] for _ in range(num_agents)]
		sample_cache: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
		stats_cache: Dict[Tuple[int, int], Dict[str, float]] = {}

		for i in range(num_agents):
			for j in range(num_agents):
				recs_ij = ordered_data[(i, j)]
				sample_ij = bootstrap_sample(recs_ij)
				stats_ij = ordered_stats(sample_ij)
				sample_cache[(i, j)] = sample_ij
				stats_cache[(i, j)] = stats_ij
				if i == j:
					M[i][j] = stats_ij["row_mean"]
				W_uw[i][j] = stats_ij["uw_norm"]
				W_nw[i][j] = stats_ij["nw_norm"]
				W_nwa[i][j] = stats_ij["nwa_norm"]
				W_ef1[i][j] = stats_ij["ef1_freq"]

		# Fill symmetric entries for i != j using both role datasets
		for i in range(num_agents):
			for j in range(num_agents):
				if i == j:
					continue
				row_stats = stats_cache.get((i, j))
				col_stats = stats_cache.get((j, i))
				row_mean = row_stats["row_mean"] if row_stats else 0.0
				col_from_rev = col_stats["col_mean"] if col_stats else 0.0
				M[i][j] = 0.5 * (row_mean + col_from_rev)

		# Solve MENE
		x_np = milp_max_sym_ent_2p(np.array(M), discrete_factors=100)
		reg_vec, nash_val, u_vals = compute_regret(x_np, np.array(M))
		regrets = [float(r) for r in reg_vec.tolist()]
		mixture = [float(p) for p in x_np.tolist()]

		# Aggregate welfare metrics vs MENE mixture for each agent
		agent_metrics: Dict[str, Dict[str, float]] = {}
		for i, ai in enumerate(agents):
			uw_i = 0.0
			nw_i = 0.0
			nwa_i = 0.0
			ef1_i = 0.0
			for j in range(num_agents):
				if i == j:
					# self-play: use i__vs__i only
					uw_ij = W_uw[i][i]
					nw_ij = W_nw[i][i]
					nwa_ij = W_nwa[i][i]
					ef1_ij = W_ef1[i][i]
				else:
					#, should all be same 
					uw_ij = 0.5 * (W_uw[i][j] + W_uw[j][i])
					nw_ij = 0.5 * (W_nw[i][j] + W_nw[j][i])
					nwa_ij = 0.5 * (W_nwa[i][j] + W_nwa[j][i])
					ef1_ij = 0.5 * (W_ef1[i][j] + W_ef1[j][i])
				uw_i += mixture[j] * uw_ij
				nw_i += mixture[j] * nw_ij
				nwa_i += mixture[j] * nwa_ij
				ef1_i += mixture[j] * ef1_ij
			agent_metrics[ai] = {
				"UW_norm": uw_i,
				"NW_norm": nw_i,
				"NWA_norm": nwa_i,
				"EF1_freq": ef1_i,
			}

		boot_results.append({
			"mixture": mixture,
			"regrets": regrets,
			"agent_metrics": agent_metrics,
		})

	# Summaries (means over bootstraps)
	def average_list(lst: List[List[float]]) -> List[float]:
		if not lst:
			return []
		k = len(lst[0])
		sums = [0.0] * k
		for v in lst:
			for t in range(k):
				sums[t] += v[t]
		return [x / len(lst) for x in sums]

	mixtures = [br["mixture"] for br in boot_results]
	regs = [br["regrets"] for br in boot_results]
	avg_mixture = average_list(mixtures)
	avg_regrets = average_list(regs)

	# Average agent metrics
	avg_agent_metrics: Dict[str, Dict[str, float]] = {}
	for ai in agents:
		acc = {"UW_norm": 0.0, "NW_norm": 0.0, "NWA_norm": 0.0, "EF1_freq": 0.0}
		for br in boot_results:
			m = br["agent_metrics"][ai]
			for k in acc:
				acc[k] += float(m[k])
		for k in acc:
			acc[k] /= len(boot_results) if boot_results else 1.0
		avg_agent_metrics[ai] = acc

	result = {
		"agents": agents,
		"bootstrap": {
			"num_bootstrap": num_bootstrap,
			"results": boot_results,
			"averages": {
				"mixture": avg_mixture,
				"regrets": avg_regrets,
				"agent_metrics": avg_agent_metrics,
			},
		},
		"params": {
			"discount_factor": discount_factor,
			"normalization": norm,
		},
	}
	(Path(output_dir) / "results.json").write_text(json.dumps(result, indent=2))
	return result


def _count_profiles(traces_dir: Path) -> int:
	"""Count available strategy profiles as number of trace files."""
	if not traces_dir.exists():
		return 0
	return len(list(traces_dir.glob("*.jsonl")))


def run_metagame_analysis(config: Dict[str, Any] | None = None) -> Dict[str, Any]:
	"""
	Run the full metagame analysis and return metrics in a standardized schema.

	Returns:
	{
		"summary": {...},
		"per_agent": [...],
		"error": {...optional...}
	}
	"""
	cfg = config or {}
	defaults = {
		"discount_factor": 0.98,
		"num_bootstrap": 100,
		"norm_constants": {"UW": 805.9, "NW": 378.7, "NWA": 81.7},
		"random_seed": 42,
	}
	try:
		input_dir = cfg.get("input_dir")
		output_dir = cfg.get("output_dir", "meta_game_analysis/results_bargaining")
		if not input_dir:
			raise ValueError("input_dir is required for metagame analysis")

		analysis_kwargs = {
			"input_dir": input_dir,
			"output_dir": output_dir,
			"discount_factor": cfg.get("discount_factor", defaults["discount_factor"]),
			"num_bootstrap": cfg.get("num_bootstrap", defaults["num_bootstrap"]),
			"norm_constants": cfg.get("norm_constants", defaults["norm_constants"]),
			"random_seed": cfg.get("random_seed", defaults["random_seed"]),
		}
		res = run_analysis(**analysis_kwargs)

		agents: List[str] = list(res.get("agents", []))
		avg_regrets: List[float] = res.get("bootstrap", {}).get("averages", {}).get("regrets", []) or []
		avg_agent_metrics: Dict[str, Dict[str, float]] = res.get("bootstrap", {}).get("averages", {}).get("agent_metrics", {}) or {}

		per_agent: List[Dict[str, Any]] = []
		for idx, agent in enumerate(agents):
			am = avg_agent_metrics.get(agent, {})
			per_agent.append(
				{
					"agent_name": agent,
					"mene_regret": float(avg_regrets[idx]) if idx < len(avg_regrets) else None,
					"nw_percent": float(am.get("NW_norm", 0.0)) * 100.0,
					"nwa_percent": float(am.get("NWA_norm", 0.0)) * 100.0,
					"uw_percent": float(am.get("UW_norm", 0.0)) * 100.0,
					"ef1_percent": float(am.get("EF1_freq", 0.0)) * 100.0,
				}
			)

		summary = {}
		if per_agent:
			summary = {
				"num_agents": len(per_agent),
				"num_profiles": _count_profiles(Path(input_dir) / "traces"),
				"mene_regret_mean": float(sum(pa["mene_regret"] for pa in per_agent if pa["mene_regret"] is not None) / max(1, sum(1 for pa in per_agent if pa["mene_regret"] is not None))),
				"nw_percent_mean": float(sum(pa["nw_percent"] for pa in per_agent) / len(per_agent)),
				"nwa_percent_mean": float(sum(pa["nwa_percent"] for pa in per_agent) / len(per_agent)),
				"uw_percent_mean": float(sum(pa["uw_percent"] for pa in per_agent) / len(per_agent)),
				"ef1_percent_mean": float(sum(pa["ef1_percent"] for pa in per_agent) / len(per_agent)),
			}
		else:
			summary = {
				"num_agents": 0,
				"num_profiles": 0,
				"mene_regret_mean": None,
				"nw_percent_mean": None,
				"nwa_percent_mean": None,
				"uw_percent_mean": None,
				"ef1_percent_mean": None,
			}

		return {
			"summary": summary,
			"per_agent": per_agent,
		}
	except Exception as e:
		return {
			"summary": {
				"num_agents": 0,
				"num_profiles": 0,
				"mene_regret_mean": None,
				"nw_percent_mean": None,
				"nwa_percent_mean": None,
				"uw_percent_mean": None,
				"ef1_percent_mean": None,
			},
			"per_agent": [],
			"error": {
				"type": type(e).__name__,
				"message": str(e),
			},
		}

