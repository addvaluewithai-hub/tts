# Visual approvals

A final render is allowed only after authoritative QA **and manual image review**.

Create:

```text
approvals/<job-id>/APPROVED
```

with at least:

```text
source_sha=<exact production source commit>
transcript_sha256=<exact build-meta transcript hash>
visual_review=all_full_resolution_scene_holds_opened
reviewed_at=<UTC timestamp>
notes=<what was manually reviewed>
```

The reviewer must actually open every scene final, every risk screenshot, and every full-duration progression strip from the authoritative QA artifact.

If the production source SHA or transcript hash changes, the approval is stale and must be recreated after a new QA/manual review pass.
