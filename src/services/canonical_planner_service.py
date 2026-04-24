def classify_unit_action(mastery_lcb: float) -> str:
    if mastery_lcb >= 0.8:
        return "skip"
    if mastery_lcb >= 0.5:
        return "quick_review"
    return "deep_practice"
