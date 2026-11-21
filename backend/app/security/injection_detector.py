from __future__ import annotations

import re
from typing import Any

INJECTION_PATTERNS: list[re.Pattern] = [
    # Delimiter breakout patterns
    re.compile(r"<\s*/?\s*(?:transcript|system|user|assistant|instruction|context)", re.IGNORECASE),
    re.compile(r"<\s*transcript_[a-f0-9]+", re.IGNORECASE),
    # Control tokens
    re.compile(r"<\|(?:im_start|im_end|system|user|assistant|endoftext)\|>", re.IGNORECASE),
    re.compile(r"\[/?(?:INST|SYS)\]", re.IGNORECASE),
    re.compile(r"<<(?:SYS|SYSTEM)>>", re.IGNORECASE),
    # Instruction overrides & jailbreaks
    re.compile(r"\b(?:system\s+override|ignore\s+(?:all\s+)?previous\s+(?:instructions|rules))\b", re.IGNORECASE),
    re.compile(r"\b(?:disregard\s+(?:all\s+)?prior\s+(?:rules|commands))\b", re.IGNORECASE),
    re.compile(r"\b(?:return\s*\{.*\"passed\"\s*:\s*true.*\}|output\s+JSON\s+only\s+with\s+passed)\b", re.IGNORECASE),
    re.compile(r"\b(?:you\s+are\s+now\s+in\s+developer\s+mode|DAN\s+mode|jailbreak)\b", re.IGNORECASE),
    # Prompt leak queries
    re.compile(r"\b(?:print\s+(?:your\s+)?system\s+(?:prompt|message|instructions)|repeat\s+the\s+words\s+above)\b", re.IGNORECASE),
]


def detect_prompt_injection(text: str) -> dict[str, Any]:
    """Microsecond CPU regex classifier to detect adversarial prompt injections and evasion attacks."""
    if not text:
        return {
            "is_injection": False,
            "matched_patterns": [],
            "risk_score": 0.0,
        }

    matched: list[str] = []
    for pattern in INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            matched.append(match.group(0))

    is_injection = len(matched) > 0
    # Risk score between 0.0 and 1.0 based on matched patterns
    risk_score = min(1.0, len(matched) * 0.35)

    return {
        "is_injection": is_injection,
        "matched_patterns": matched,
        "risk_score": round(risk_score, 2),
        "threat_level": "CRITICAL" if risk_score >= 0.7 else ("SUSPICIOUS" if is_injection else "BENIGN"),
    }
