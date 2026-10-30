from pathlib import Path

import pytest

from meeting_owner_lens.core import (Action, Cue, audit, parse_actions, parse_roster,
                                     parse_transcript)


def test_parse_valid_inputs(tmp_path: Path) -> None:
    transcript = tmp_path / "meeting.txt"
    actions = tmp_path / "actions.csv"
    roster = tmp_path / "roster.txt"
    transcript.write_text("00:00 Alice: I will send it.\n\n01:30 Bob: Okay.\n", encoding="utf-8")
    actions.write_text("task,owner\nSend it,Alice\n", encoding="utf-8")
    roster.write_text("Alice\nBob\n", encoding="utf-8")
    assert len(parse_transcript(transcript)) == 2
    assert parse_transcript(transcript)[1].line == 3
    assert parse_actions(actions) == [Action("Send it", "Alice")]
    assert parse_roster(roster) == {"alice", "bob"}


@pytest.mark.parametrize("value", ["Alice: no time\n", "00:00 no speaker\n", ""])
def test_invalid_transcript(tmp_path: Path, value: str) -> None:
    file = tmp_path / "meeting.txt"
    file.write_text(value, encoding="utf-8")
    with pytest.raises(ValueError):
        parse_transcript(file)


def test_duplicate_roster_rejected(tmp_path: Path) -> None:
    file = tmp_path / "roster.txt"
    file.write_text("Alice\nalice\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        parse_roster(file)


def test_missing_task_rejected(tmp_path: Path) -> None:
    file = tmp_path / "actions.csv"
    file.write_text("task,owner\n,Alice\n", encoding="utf-8")
    with pytest.raises(ValueError, match="task"):
        parse_actions(file)


def test_audit_statuses() -> None:
    cues = [Cue("00:00", "Alice", "I'll send the deck.", 1),
            Cue("00:10", "Bob", "I will update the checklist.", 2),
            Cue("00:20", "Alice", "We discussed the budget.", 3)]
    actions = [Action("Send deck", "Alice"), Action("Update checklist", "Alice"),
               Action("Budget", "Carol"), Action("Discuss budget", ""),
               Action("Unknown deliverable", "Bob"), Action("Discuss budget", "Alice")]
    matrix = [[0.9, 0.2, 0.1], [0.1, 0.9, 0.1], [0.1, 0.1, 0.9],
              [0.1, 0.1, 0.9], [0.1, 0.2, 0.1], [0.1, 0.1, 0.9]]
    rows = audit(actions, cues, {"alice", "bob"}, matrix)
    assert [row.status for row in rows] == ["candidate_alignment", "review_owner", "owner_not_in_roster",
                                             "owner_unassigned", "weak_anchor", "review_commitment"]
    assert rows[0].best_line == 1


def test_bad_matrix_dimensions() -> None:
    with pytest.raises(ValueError, match="dimensions"):
        audit([Action("A", "Alice")], [Cue("00:00", "Alice", "Hello", 1)], {"alice"}, [[]])
