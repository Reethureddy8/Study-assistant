"""12-question evaluation: run the assistant, then summarise hand-scored results.

Scoring axes (filled in by a human reviewer in the *_scored.csv files):
    correctness       yes | partial | no   (n/a for out-of-scope)
    grounded          yes | no             (n/a for out-of-scope)
    refused_when_oos  yes | no             (n/a for in-scope)
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Iterable

from .generation import StudyAssistant

EVAL_SET = [
    # Direct: wording close to the textbook
    {"id": 1, "category": "direct", "question": "What is displacement?"},
    {"id": 2, "category": "direct", "question": "What are the three kinematic equations of motion?"},
    {"id": 3, "category": "direct", "question": "What is uniform circular motion?"},
    {"id": 4, "category": "direct", "question": "What is average acceleration?"},
    {"id": 5, "category": "direct", "question": "State Newton's first law of motion."},
    {"id": 6, "category": "direct", "question": "What is the SI unit of force and how is it defined?"},
    # Paraphrased: same concepts, everyday wording
    {"id": 7, "category": "paraphrased", "question": "Why does a fielder pull hands back while catching a fast cricket ball?"},
    {"id": 8, "category": "paraphrased", "question": "If an object moves in a circle at constant speed, is it accelerating?"},
    {"id": 9, "category": "paraphrased", "question": "What decides how far a car travels after brakes are applied?"},
    # Out of scope: must be refused (the last one sounds answerable on purpose)
    {"id": 10, "category": "out_of_scope", "question": "What is photosynthesis?"},
    {"id": 11, "category": "out_of_scope", "question": "Explain the water cycle."},
    {"id": 12, "category": "out_of_scope", "question": "Calculate the value of g on the surface of the Moon."},
]

RAW_FIELDS = [
    "id", "category", "question", "answer", "chunk_ids_cited",
    "top1_chunk_id", "top1_section", "top1_similarity", "all_retrieved",
]


def run_evaluation(assistant: StudyAssistant, questions: Iterable[dict] = EVAL_SET) -> list[dict]:
    rows = []
    for item in questions:
        answer = assistant.ask(item["question"])
        top = answer.retrieved[0] if answer.retrieved else None
        rows.append({
            "id": item["id"],
            "category": item["category"],
            "question": item["question"],
            "answer": answer.text,
            "chunk_ids_cited": ", ".join(answer.cited_ids),
            "top1_chunk_id": top.chunk_id if top else "",
            "top1_section": top.chunk.section if top else "",
            "top1_similarity": top.score if top else "",
            "all_retrieved": str([r.chunk_id for r in answer.retrieved]),
        })
    return rows


def write_csv(rows: list[dict], path: Path, fields: list[str] = RAW_FIELDS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def summarize(scored_rows: Iterable[dict]) -> dict:
    """Count results on the three axes from a hand-scored CSV."""
    rows = list(scored_rows)
    in_scope = [r for r in rows if r["category"] != "out_of_scope"]
    oos = [r for r in rows if r["category"] == "out_of_scope"]
    correctness = Counter(r["correctness"] for r in in_scope)
    return {
        "in_scope": len(in_scope),
        "correct": correctness["yes"],
        "partial": correctness["partial"],
        "wrong": correctness["no"],
        "grounded": sum(r["grounded"] == "yes" for r in in_scope),
        "out_of_scope": len(oos),
        "refused": sum(r["refused_when_oos"] == "yes" for r in oos),
    }


def format_summary(summary: dict) -> str:
    n, m = summary["in_scope"], summary["out_of_scope"]
    return "\n".join([
        f"Correct      {summary['correct']}/{n}",
        f"Partial      {summary['partial']}/{n}",
        f"Wrong        {summary['wrong']}/{n}",
        f"Grounded     {summary['grounded']}/{n}",
        f"OOS refused  {summary['refused']}/{m}",
    ])
