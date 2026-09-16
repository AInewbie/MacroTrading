from __future__ import annotations


COMPONENT_VALUES = {
    "P": {0.0, 0.5, 1.0},
    "F": {0.0, 0.5, 1.0},
    "M": {0.0, 0.5, 1.0},
    "C": {0.0, 0.5, 1.0},
    "X": {0.0, 0.5, 1.0},
}


def validate_components(components: dict[str, float]) -> None:
    missing = set(COMPONENT_VALUES) - set(components)
    if missing:
        raise ValueError(f"missing WATCH-v1 components: {sorted(missing)}")
    for key, allowed in COMPONENT_VALUES.items():
        value = float(components[key])
        if value not in allowed:
            raise ValueError(f"{key}={value} is not in {sorted(allowed)}")
    risk = float(components.get("R", 0))
    if risk not in {0.0, 1.0, 2.0}:
        raise ValueError("R must be 0, 1, or 2")


def watch_v1_score(components: dict[str, float]) -> float:
    """Return the deterministic WATCH-v1.0 score."""
    validate_components(components)
    raw = (
        25 * components["P"]
        + 25 * components["F"]
        + 20 * components["M"]
        + 20 * components["C"]
        + 10 * components["X"]
        - 10 * min(2, components["R"])
    )
    return max(0.0, min(100.0, float(raw)))


def score_band(score: float) -> str:
    if score < 45:
        return "Exploratory watch"
    if score < 70:
        return "Research review"
    return "Priority research"

