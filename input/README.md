# Input inbox

`input/` is the only place humans or agents should add a new video job.

The factory may contain many job folders, but **only the job named in `input/ACTIVE` is processed**. We intentionally do one production at a time for now.

## Minimum job package

```text
input/<job-id>/
  job.yaml
  direction.md
  transcript/
    01-part.txt
    02-part.txt
    ...
```

Required:

- `job.yaml` — small machine-readable identity and production settings.
- `direction.md` — natural-language creative/teaching/brand direction for the video agent.
- `transcript/` — short numbered TTS source parts in playback order when audio is enabled.

Optional:

```text
  pronunciation-map.json
  assets/
  references/
  data/
```

Put anything job-specific in this folder. Do not put lesson-specific rules in the repository-wide `AGENTS.md`.

## Activate a job

Set `input/ACTIVE` to exactly the folder name:

```text
lesson-02-family-and-friends
```

Do not switch `ACTIVE` to another job until the current final video artifact is published or the job is intentionally abandoned.

## Transcript rules

- Prefer short, stable numbered files. They are TTS retry/retake boundaries, **not a promise that video scene count equals audio part count**.
- Do not use per-file character limits as normal production control. The global TTS maximum is only an internal safety net.
- Preserve pronunciation/performance markup that is intentionally authored. Do not casually rewrite IPA, `<lang>`, `<phoneme>`, or bracketed performance directions.
- For a one-voice production, use `voice:` in front matter rather than a one-item `speakers:` list.
- `Speaker 1:`-style labels are role markers, not spoken copy. Prefer omitting them for new single-speaker jobs.

## Source of truth

`input/<job-id>/` is the human/agent source package. `transcripts/`, `audio/`, `done/`, `final/`, `productions/`, QA manifests, and render artifacts are factory-managed or agent-generated production state.
