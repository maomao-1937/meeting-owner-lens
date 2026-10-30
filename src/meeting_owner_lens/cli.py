"""CLI for a deliberately non-automatic meeting-owner review aid."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import audit, parse_actions, parse_roster, parse_transcript, semantic_matrix


def render_report(reviews: list[dict[str, object]]) -> str:
    lines = ["# MeetingOwnerLens review", "", "Source-linked suggestions, not verified assignments.", ""]
    for index, review in enumerate(reviews, 1):
        lines += [f"## {index}. {review['task']}", "", f"- Claimed owner: {review['claimed_owner'] or '(none)'}",
                  f"- Status: `{review['status']}`", f"- Closest transcript cue: line {review['best_line']}, "
                  f"{review['best_time']} — {review['best_speaker']}: {review['best_excerpt']}",
                  f"- Similarity: {review['similarity']} (uncalibrated)", f"- Why review: {review['reason']}", ""]
    lines += ["Confirm with the people involved and the source recording before sharing or assigning work.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review draft action owners against a declared roster and transcript")
    parser.add_argument("transcript", type=Path)
    parser.add_argument("actions_csv", type=Path)
    parser.add_argument("roster", type=Path)
    parser.add_argument("--out", type=Path, default=Path("review.local.md"))
    parser.add_argument("--json-out", type=Path, default=Path("review.local.json"))
    parser.add_argument("--min-similarity", type=float, default=0.35)
    args = parser.parse_args(argv)
    try:
        cues = parse_transcript(args.transcript)
        actions = parse_actions(args.actions_csv)
        roster = parse_roster(args.roster)
        matrix = semantic_matrix(actions, cues)
        reports = [review.to_dict() for review in audit(actions, cues, roster, matrix, args.min_similarity)]
        args.out.write_text(render_report(reports), encoding="utf-8")
        args.json_out.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for report in reports:
            print(f"{report['status']}: {report['task']} | {report['claimed_owner'] or '(none)'}")
        print(f"Reports: {args.out}, {args.json_out}")
        return 0
    except (OSError, ValueError) as error:
        print(f"MeetingOwnerLens: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
