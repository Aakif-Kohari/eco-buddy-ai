from typing import Any

from contamination_simulator import check_contamination, get_contamination_penalty

# Standard waste streams
WASTE_STREAMS = {
    "recycling": {"name": "Recycling", "color": "#2ca02c", "icon": "♻️"},
    "compost": {"name": "Compost", "color": "#8c564b", "icon": "🌱"},
    "landfill": {"name": "Landfill", "color": "#7f7f7f", "icon": "🗑️"},
    "hazardous": {"name": "Hazardous", "color": "#d62728", "icon": "⚠️"},
}


def process_waste_log(items: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Processes a list of waste items, checks for contamination, and calculates stream analytics.
    """
    stream_totals = {
        "recycling": 0.0,
        "compost": 0.0,
        "landfill": 0.0,
        "hazardous": 0.0,
    }
    contamination_warnings = []
    total_weight = 0.0
    contaminated_weight = 0.0

    for item in items:
        weight = item.get("weight_kg", 0.0)
        stream = item.get("stream", "landfill")
        item_name = item.get("name", "Unknown Item")

        total_weight += weight

        # Check for contamination
        is_contaminated, reason = check_contamination(item_name, stream)

        if is_contaminated:
            contaminated_weight += weight
            contamination_warnings.append(
                {
                    "item": item_name,
                    "stream": stream,
                    "reason": reason,
                    "weight_kg": weight,
                }
            )
            # Contaminated recycling/compost is diverted to landfill
            effective_stream = "landfill"
        else:
            effective_stream = stream

        if effective_stream in stream_totals:
            stream_totals[effective_stream] += weight

    # Calculate Recycling Efficiency Score (0-100)
    # Base score is 100, reduced by contamination penalty
    base_recycling = (
        stream_totals["recycling"] + contaminated_weight
    )  # What was intended to be recycled
    if base_recycling > 0:
        contamination_ratio = contaminated_weight / base_recycling
        penalty = get_contamination_penalty(contamination_ratio)
        efficiency_score = max(0, 100 - penalty)
    else:
        efficiency_score = (
            100.0 if total_weight == 0 else 50.0
        )  # Neutral if no recycling attempted

    return {
        "total_weight_kg": round(total_weight, 2),
        "stream_breakdown": {k: round(v, 2) for k, v in stream_totals.items()},
        "contamination_warnings": contamination_warnings,
        "contaminated_weight_kg": round(contaminated_weight, 2),
        "recycling_efficiency_score": round(efficiency_score, 1),
    }


def get_waste_stream_metadata() -> dict[str, Any]:
    """Returns metadata for UI rendering of waste streams."""
    return WASTE_STREAMS
