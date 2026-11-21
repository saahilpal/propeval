from __future__ import annotations

from typing import Any


def detect_verbosity_inflation(
    baseline_turns: list[dict[str, Any]],
    candidate_turns: list[dict[str, Any]],
    threshold_pct: float = 25.0,
) -> dict[str, Any]:
    """Detect length-bloat / verbosity reward gaming.

    AlpacaEval 2.0 (Dubois et al., 2024) proved LLM judges systematically favor
    longer responses regardless of factual precision.
    If the candidate prompt inflated average turn length by > threshold_pct
    without factual gain, it is flagged for verbosity inflation.
    """
    base_lengths = [len(t.get("agent_turn", "")) for t in baseline_turns if t.get("agent_turn")]
    cand_lengths = [len(t.get("agent_turn", "")) for t in candidate_turns if t.get("agent_turn")]

    base_avg = sum(base_lengths) / max(len(base_lengths), 1)
    cand_avg = sum(cand_lengths) / max(len(cand_lengths), 1)

    if base_avg == 0:
        delta_pct = 0.0
    else:
        delta_pct = ((cand_avg - base_avg) / base_avg) * 100.0

    is_inflated = delta_pct > threshold_pct

    return {
        "is_inflated": is_inflated,
        "delta_pct": round(delta_pct, 2),
        "baseline_avg_chars": round(base_avg, 1),
        "candidate_avg_chars": round(cand_avg, 1),
        "flag": "VERBOSITY_INFLATED" if is_inflated else "NORMAL",
    }


def compute_position_flip_rate(
    pairwise_results: list[dict[str, Any]],
    instability_threshold: float = 0.10,
) -> dict[str, Any]:
    """Compute position-swap flip rate (Wang et al., 2023).

    If swapping (A, B) to (B, A) changes the winner or creates contradictory
    verdicts in > instability_threshold of pairs, the benchmark has high position bias.
    """
    total_pairs = len(pairwise_results)
    if total_pairs == 0:
        return {
            "total_pairs": 0,
            "flipped_pairs": 0,
            "flip_rate": 0.0,
            "is_unstable": False,
        }

    flips = 0
    for r in pairwise_results:
        # Expected keys: winner_normal ('A'|'B'|'TIE'), winner_swapped ('A'|'B'|'TIE')
        # where in swapped run, 'A' corresponds to original 'B'
        w_norm = r.get("winner_normal")
        w_swap = r.get("winner_swapped")

        if w_norm and w_swap:
            # If normal said A won, swapped should say B won to be consistent
            if w_norm == "A" and w_swap != "B":
                flips += 1
            elif w_norm == "B" and w_swap != "A":
                flips += 1
            elif w_norm == "TIE" and w_swap != "TIE":
                flips += 1

    flip_rate = flips / total_pairs
    return {
        "total_pairs": total_pairs,
        "flipped_pairs": flips,
        "flip_rate": round(flip_rate, 4),
        "is_unstable": flip_rate > instability_threshold,
    }


def detect_judge_disagreement(
    layer1_pass: bool,
    layer2_pass: bool,
    layer3_pass: bool | None,
) -> dict[str, Any]:
    """Detect Judge-vs-Deterministic Disagreement (Sharma et al., 2023).

    Flags cases where an LLM judge hallucinated a PASS on a turn that violated
    Layer 1 (DNC, invented tool action) or Layer 2 (RERA date / property facts).
    """
    deterministic_pass = layer1_pass and layer2_pass
    if layer3_pass is None:
        return {
            "has_disagreement": False,
            "hallucinated_pass": False,
            "deterministic_pass": deterministic_pass,
            "layer3_pass": None,
        }

    # If deterministic checks failed but LLM judge said pass -> Hallucinated Pass
    hallucinated_pass = (not deterministic_pass) and layer3_pass

    return {
        "has_disagreement": hallucinated_pass,
        "hallucinated_pass": hallucinated_pass,
        "deterministic_pass": deterministic_pass,
        "layer3_pass": layer3_pass,
        "flag": "JUDGE_DISAGREEMENT_HALLUCINATED_PASS" if hallucinated_pass else "CONCORDANT",
    }
