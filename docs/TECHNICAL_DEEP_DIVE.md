# NotebookLM Technical Deep Dive: Research & Mind Map Protocols

This document captures technical discoveries made during the development of the NotebookLM CLI and MCP server, specifically regarding undocumented RPC behaviors and status codes.

## 1. Research Protocol (RPC: `e3bVqc`)

When polling for research status, NotebookLM returns a complex nested array. The status of a research task is indicated by a specific integer code at index `task_info[4]`.

### Status Code Mapping
- **`2`**: `IN_PROGRESS`. The task is active, but results are not yet finalized.
- **`6`**: `COMPLETED`. The research session has finished, and all discovered sources are available for import.
- **`NO_RESEARCH`**: Indicated by an empty response or `null` task identifiers.

### Task Structure Discovery
The response structure for `poll_research` (RPC `e3bVqc`) is:
```json
[
  "task_id",
  [
    "notebook_id",
    ["query", 1],
    1,
    [
      [
        ["url", "title", "snippet", type_code, ...]
      ],
      "overall_summary"
    ],
    status_code
  ]
]
```
- **Note**: `type_code` in the source list determines if a source is Web (`1`), Drive (`2`, `3`, `8`), or an internal Deep Report (`5`).

---

## 2. Mind Map Protocol

Mind Maps behave differently from other Studio artifacts (Audio/Video). They require a two-step synchronization process for mutations and have a unique storage mechanism.

### Mutation: Deletion Sequence
To fully delete a Mind Map and prevent "ghost" entries in the backend list, two RPCs must be called in order:

1. **`AH0mwd` (Logical Delete)**:
   - **Payload**: `[notebook_id, null, [mind_map_id], [2]]`
   - This marks the artifact as deleted but doesn't immediately remove it from the persistent list (`cFji9`).

2. **`cFji9` (Commit/Sync)**:
   - **Payload**: `[notebook_id, null, [seconds, microseconds], [2]]`
   - **Crucial**: The `[seconds, microseconds]` timestamp MUST be the artifact's specific creation timestamp, retrieved from a previous `LIST_MIND_MAPS` call.
   - Calling this "commits" the state change.

### Tombstone Behavior in `LIST_MIND_MAPS` (RPC: `cFji9`)
Even after deletion, the backend often returns a "tombstone" entry in the list to maintain synchronization history.
- **Active Entry**: `["uuid", [metadata...]]`
- **Deleted Entry (Tombstone)**: `["uuid", null, 2]`
- **Action**: Clients must filter out entries where the second index (`metadata`) is `null`.

---

## 3. General Implementation Notes

### Build Label (`bl`)
The `bl` query parameter in `batchexecute` requests is critical for mutations. 
- **Effect**: If the `bl` is significantly outdated (e.g., several weeks old), mutations like research starts or artifact deletions may fail silently or return `400 Bad Request`.
- **Recommendation**: Periodically update the hardcoded default `bl` to match the latest web client version. Current observed working `bl`: `boq_labs-tailwind-frontend_20260108.06_p0`.

### Batch Import (RPC: `LBwxtb`)
When importing research sources, use the batch import RPC rather than adding sources individually. This handles MIME types correctly and is much more efficient.
- **Payload**: `[None, [1], task_id, notebook_id, source_array]`
- **Source Format**: Web sources use `[None, None, [url, title], ..., 2]`. Drive sources use `[[doc_id, mime_type, 1, title], ..., 2]`.
