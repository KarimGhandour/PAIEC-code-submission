import json
_LABELED_EXCERPT_CHARS=300
_RESOLUTION_CRITERIA="Your probability estimate should be P(the target model answers this item correctly on a single attempt)."

def build_question(subject: dict, item: dict, labeled: list | None = None) -> dict:
    """Combine all target fields with compact examples from the same subject.

    Returns only the text the predictor needs. Corpus loading and run-log
    management belong to the retrieval layer and agent, respectively.

    Revealed examples must match the complete visible subject dictionary.
    Each includes only a verdict and item-text excerpt to keep context short;
    unlike the target item, examples omit item features and interactors.
    Excerpts provide evidence for reasoning, not keys for matching outcomes.
    """
    target = subject.get("normalized_name") or "unknown model"
    content = item.get("item_content", "")

    bg_lines = [
        "AI model's settings:",
        f"- Provider: {_format_field(subject.get('provider'))}",
        f"- Release date: {_format_field(subject.get('release_date'))}",
        f"- Access date: {_format_field(subject.get('access_date'))}",
        f"- Harness setting: {_format_field(subject.get('harness'))}",
        f"- Harness version: {_format_field(subject.get('harness_version'))}",
        f"- Reasoning effort level: {_format_field(subject.get('reasoning_effort'))}",
        f"- Other features (if available): {_format_field(subject.get('subject_features_extra'))}",
        "",
        "Item the subject must answer:",
        f"- Question: {_format_field(content)}",
        f"- Any features of the question (if available): {_format_field(item.get('item_features'))}",
        "",
        "Extra information (if available)",
        f"- Interactor (other components): {_format_field(item.get('interactors'))}",
    ]
    observations = []
    for (observed_subject, observed_item), label in labeled or []:
        if observed_subject != subject:
            continue
        verdict = "CORRECT" if float(label) >= 0.5 else "INCORRECT"
        excerpt = (
            " ".join(observed_item["item_content"].split())[:_LABELED_EXCERPT_CHARS]
            or "(item text unavailable)"
        )
        observations.append(f"- [{verdict}] {excerpt}")
    if observations:
        bg_lines += [
            "",
            (
                "Revealed outcomes from this subject on trials "
                "from the same hidden evaluation:"
            ),
        ] + observations

    return {
        "question": (
            f"What is the probability the AI model '{target}', "
            f"with the following settings, answers the item below "
            f"correctly (on a single attempt)?"
        ),
        "background": "\n".join(bg_lines),
        "resolution_criteria": _RESOLUTION_CRITERIA,
    }

def _format_field(value) -> str:
    """Render a metadata value, marking empty or missing fields explicitly."""
    text = str(value).strip() if value is not None else ""
    return text if text and text.lower() not in ("nan", "none") else "No information"
