# MeetingOwnerLens

Review **existing** AI-drafted meeting action items before sending them to a team. MeetingOwnerLens compares a `task,owner` CSV with a speaker-labeled transcript using a real local sentence-embedding model and checks the claimed owner against a user-provided roster. It reports the closest utterance, time and line for human verification. It never creates, assigns, emails or syncs tasks.

## Who and what

For a PM or meeting organizer who already has a draft action list. Their repeated job is to check that the work and person named in the draft reflect the meeting, rather than trusting a polished AI summary. The tool flags out-of-roster names, weak text anchors, a closest utterance from a different speaker, and absence of explicit first-person wording. A `candidate_alignment` is **not approval**: it simply meets these narrow signals.

## Install and demonstrate

Python 3.11+ and [uv](https://docs.astral.sh/uv/) are required. The first run downloads `sentence-transformers/all-MiniLM-L6-v2` (Apache-2.0); subsequent inference can use the local cache. There is no paid model API and this CLI does not upload meeting text.

```sh
uv sync --python 3.11 --extra test
uv run meeting-owner-lens examples/demo-transcript.txt examples/demo-actions.csv examples/demo-roster.txt --out review.local.md --json-out review.local.json
uv run pytest -q
```

The **fictional** sample has three draft tasks: Alice's deck commitment, a checklist assigned to Bob despite Alice's utterance, and a budget item assigned to Carol even though Carol is not on the supplied roster. Inspect both reports and the transcript before making any change. Your own transcript must use one `M:SS Speaker: utterance` or `H:MM:SS Speaker: utterance` per nonblank line. Roster is one name per line; actions CSV has `task,owner` headers. The local files are not modified.

## Limits and privacy

- Semantic similarity is uncalibrated and is **not** a probability that a task or owner is correct. Short, paraphrased, indirect, sarcastic or multilingual statements may be missed or mis-ranked. English is the tested language. The first-person detector is only a narrow heuristic.
- The roster is **user-supplied**, not an authenticated meeting join log. The speaker labels can be wrong. A cited utterance may describe a task without committing to it; only participants can confirm ownership.
- Input profile is deliberately small: up to 300 utterances, 100 actions, a 2 MB transcript. The CLI does not transcribe audio or parse arbitrary Zoom/Teams exports. Convert those to the stated format first.
- Reports contain verbatim snippets of meeting speech and may be sensitive. Store them locally, and never commit real private transcripts or outputs to a public repository. Follow your organization's recording/consent rules.

## Product decision

[A PM's August 2026 account](https://www.reddit.com/r/projectmanagement/comments/1w0383c/please_tell_me_honestly_how_long_it_takes_you_to/) describes spending substantial time verifying AI meeting notes; [a September 2026 report](https://www.reddit.com/r/MyAIAssistant/comments/1wli9fz/my_meetingnotes_ai_invented_action_owners_who/) describes invented owners; [a July 2026 meeting-tool issue](https://github.com/silverstein/minutes/issues/523) addresses summaries drifting after transcript edits. These support a recurring review problem, not demand for this exact CLI.

[Fluent](https://becomefluent.io/tools/meeting-action-items/) is a free hosted action extractor with source lines; [Orblex](https://orblex.app/tools/meeting-notes-to-action-items) advertises a similar generator but says its form is currently unavailable; [minutes](https://github.com/silverstein/minutes) is an integrated local-first meeting app. The unvalidated distinction here is an independent **post-hoc** check of another tool's draft against a roster and transcript without cloud processing or task dispatch. More evidence and counterevidence are in [RESEARCH.md](RESEARCH.md).

MIT licensed original code; the third-party embedding model retains its Apache-2.0 license. Its weights are not committed here.
