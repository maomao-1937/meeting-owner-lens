"""Parse declared inputs and review action-owner alignment conservatively."""

from __future__ import annotations

import csv
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


CUE_RE = re.compile(r"^(?P<time>(?:\d+:)?\d{1,2}:\d{2})\s+(?P<speaker>[^:]{1,80}):\s+(?P<text>.+)$")
COMMITMENT_RE = re.compile(r"\b(?:I['’]?ll|I will|I can|I am going to|I['’]?m going to)\b", re.I)


@dataclass(frozen=True)
class Cue:
    time: str
    speaker: str
    text: str
    line: int


@dataclass(frozen=True)
class Action:
    task: str
    owner: str


@dataclass(frozen=True)
class Review:
    task: str
    claimed_owner: str
    status: str
    best_time: str
    best_speaker: str
    best_line: int | None
    best_excerpt: str
    similarity: float | None
    reason: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def parse_transcript(path: Path) -> list[Cue]:
    if path.stat().st_size > 2_000_000:
        raise ValueError("Transcript exceeds 2 MB")
    cues: list[Cue] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw.strip():
            continue
        match = CUE_RE.fullmatch(raw.strip())
        if not match:
            raise ValueError(f"Transcript line {line_number}: expected M:SS Speaker: utterance")
        cues.append(Cue(match["time"], match["speaker"].strip(), match["text"].strip(), line_number))
        if len(cues) > 300:
            raise ValueError("Transcript exceeds 300 utterances")
    if not cues:
        raise ValueError("Transcript has no utterances")
    return cues


def parse_roster(path: Path) -> set[str]:
    names = [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if not names or len(names) > 100:
        raise ValueError("Roster must contain 1–100 names")
    keys = [name.casefold() for name in names]
    if len(keys) != len(set(keys)):
        raise ValueError("Roster contains duplicate names")
    return set(keys)


def parse_actions(path: Path) -> list[Action]:
    actions: list[Action] = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not {"task", "owner"}.issubset(reader.fieldnames):
            raise ValueError("Actions CSV needs task,owner columns")
        for line_number, row in enumerate(reader, 2):
            task = (row.get("task") or "").strip()
            owner = (row.get("owner") or "").strip()
            if not task:
                raise ValueError(f"Actions CSV line {line_number}: task is required")
            actions.append(Action(task, owner))
            if len(actions) > 100:
                raise ValueError("Actions CSV exceeds 100 items")
    if not actions:
        raise ValueError("Actions CSV has no tasks")
    return actions


def semantic_matrix(actions: Sequence[Action], cues: Sequence[Cue]) -> list[list[float]]:
    """Compute real local pretrained sentence-embedding cosine similarities."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    vectors = model.encode([action.task for action in actions] + [cue.text for cue in cues],
                           normalize_embeddings=True, convert_to_numpy=True)
    return (vectors[:len(actions)] @ vectors[len(actions):].T).tolist()


def audit(actions: Sequence[Action], cues: Sequence[Cue], roster: set[str],
          matrix: Sequence[Sequence[float]], min_similarity: float = 0.35) -> list[Review]:
    if len(matrix) != len(actions) or any(len(row) != len(cues) for row in matrix):
        raise ValueError("Similarity matrix dimensions do not match inputs")
    if not 0 <= min_similarity <= 1:
        raise ValueError("min_similarity must be between zero and one")
    reviews: list[Review] = []
    for action, row in zip(actions, matrix):
        best_index = max(range(len(cues)), key=lambda index: row[index])
        best = cues[best_index]
        score = float(row[best_index])
        owner = action.owner.casefold()
        if not owner:
            status, reason = "owner_unassigned", "Draft action has no owner; do not infer one."
        elif owner not in roster:
            status, reason = "owner_not_in_roster", "Claimed owner is absent from the supplied roster."
        elif score < min_similarity:
            status, reason = "weak_anchor", "No transcript utterance cleared the semantic review threshold."
        elif best.speaker.casefold() != owner:
            status, reason = "review_owner", "Closest utterance has a different speaker; this may be context, not commitment."
        elif not COMMITMENT_RE.search(best.text):
            status, reason = "review_commitment", "Closest owner utterance lacks an explicit first-person commitment."
        else:
            status, reason = "candidate_alignment", "Closest utterance is from the owner and contains first-person wording; verify manually."
        reviews.append(Review(action.task, action.owner, status, best.time, best.speaker,
                              best.line, best.text[:500], round(score, 4), reason))
    return reviews
