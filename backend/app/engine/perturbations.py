from __future__ import annotations

import random
import re
from typing import Any

# Domain 8 kHz Indian Telephony ASR Homophones & Confusion Pairs
ASR_CONFUSION_MAP: dict[str, list[str]] = {
    "crore": ["core", "krod", "crore"],
    "cr": ["core", "cr"],
    "lakh": ["luck", "lack", "lak", "lakh"],
    "lac": ["luck", "lack", "lac"],
    "bhk": ["bk", "phk", "bhk"],
    "possession": ["position", "posession", "possession"],
    "carpet": ["carpit", "corpet", "carpet"],
    "rera": ["reera", "raira", "rera"],
    "wakad": ["walked", "waakad", "wacad", "wakad"],
    "gurugram": ["gurgaon", "gurugram"],
    "hazar": ["hazaar", "azar", "hazar"],
    "peti": ["patti", "peti"],
    "khoka": ["koka", "khoka"],
}

# Colloquial Hindi/Hinglish postpositions subject to acoustic transmission drop in 8 kHz telephony
HINDI_POSTPOSITIONS: set[str] = {"mein", "ka", "ki", "ke", "tak", "se", "ko"}


def perturb_telephony_asr(
    text: str,
    noise_rate: float = 0.25,
    seed: int = 42,
    drop_postpositions: bool = True,
) -> str:
    """Apply domain-specific 8 kHz Indian telephony ASR confusion perturbations."""
    rng = random.Random(seed)
    words = text.split()
    perturbed_words: list[str] = []

    for word in words:
        cleaned_lower = re.sub(r"[^a-zA-Z]", "", word).lower()

        # Check postposition drop with a lower probability
        if drop_postpositions and cleaned_lower in HINDI_POSTPOSITIONS and rng.random() < (noise_rate * 0.4):
            continue

        if cleaned_lower in ASR_CONFUSION_MAP and rng.random() < noise_rate:
            confusions = ASR_CONFUSION_MAP[cleaned_lower]
            replacement = rng.choice(confusions)
            # Preserve trailing punctuation if any
            if word and not word[-1].isalnum():
                replacement += word[-1]
            perturbed_words.append(replacement)
        else:
            perturbed_words.append(word)

    return " ".join(perturbed_words)


def simulate_barge_in_truncation(
    text: str,
    barge_in_word_limit: int = 5,
    cut_pct: float | None = None,
) -> str:
    """Simulate user cutting off or interrupting during agent speech (<300ms barge-in)."""
    words = text.split()
    if not words:
        return text

    if cut_pct is not None and 0.0 < cut_pct < 1.0:
        cutoff = max(1, int(len(words) * (1.0 - cut_pct)))
        return " ".join(words[:cutoff]) + " -- [interrupted]"

    if len(words) > barge_in_word_limit:
        return " ".join(words[:barge_in_word_limit]) + " -- [interrupted]"

    return text


def apply(
    text: str,
    noise_profile: str | dict[str, Any] | None = None,
    seed: int = 42,
    is_barge_in: bool = False,
) -> str:
    """Convenience pipeline dispatcher for ASR perturbation and barge-in.

    Matches: perturbations.apply(buyer_raw.text, job.scenario.asr_noise_profile, seed=seed)
    """
    if not text:
        return text

    noise_rate = 0.25
    drop_postpositions = True
    barge_in_limit = 5

    if isinstance(noise_profile, dict):
        noise_rate = float(noise_profile.get("noise_rate", 0.25))
        drop_postpositions = bool(noise_profile.get("drop_postpositions", True))
        barge_in_limit = int(noise_profile.get("barge_in_word_limit", 5))
    elif isinstance(noise_profile, str):
        if noise_profile == "clean" or noise_profile == "none":
            noise_rate = 0.0
        elif noise_profile == "light":
            noise_rate = 0.10
        elif noise_profile == "heavy":
            noise_rate = 0.40

    out = text
    if noise_rate > 0.0:
        out = perturb_telephony_asr(
            out,
            noise_rate=noise_rate,
            seed=seed,
            drop_postpositions=drop_postpositions,
        )

    if is_barge_in:
        out = simulate_barge_in_truncation(out, barge_in_word_limit=barge_in_limit)

    return out


class ASRPerturbationEngine:
    def __init__(self, seed: int = 42):
        self.seed = seed

    def perturb(self, text: str, error_rate: float = 0.25) -> str:
        return perturb_telephony_asr(text, noise_rate=error_rate, seed=self.seed)

