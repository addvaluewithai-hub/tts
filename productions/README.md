# Productions

Agent-authored deterministic video source lives here:

```text
productions/<job-id>/video/
```

This is **not** the human input inbox. The agent creates/updates production source after reading `input/<job-id>/direction.md` and after authoritative audio timing is ready.

Every production can have a different visual design, but the generic factory workflows expect:

```text
productions/<job-id>/video/
  template.tpl              # recommended editable root source; do not keep a second root .html
  styles.css                # optional/custom
  timeline.js               # optional/custom deterministic timeline
  scripts/
    build-from-audio.mjs     # required
    prepare-assets.sh        # optional
```

`build-from-audio.mjs` receives `FACTORY_JOB_ID` and must create at least:

```text
index.html
build-meta.json
```

The build should read synchronized audio/timing from:

```text
assets/audio/<job-id>.wav
assets/audio/<job-id>.transcript.json
```

The workflows materialize those files from the repository's `final/` audio state.

Minimum `build-meta.json` contract:

```json
{
  "duration": 123.456,
  "transcript_sha256": "...",
  "scenes": [
    {"index": 1, "start": 0, "end": 12.3, "duration": 12.3}
  ],
  "finalHolds": [11.65],
  "riskBeats": [2.4]
}
```

`scenes` are editorial video scenes. They do not have to match audio part count.

See `introduce-yourself/` for a fully approved reference production and `docs/PRODUCTION_PLAYBOOK.md` for the hard QA/render rules.
