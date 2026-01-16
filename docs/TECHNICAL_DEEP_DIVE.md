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

---

## 4. Chat/Query Response Structure

When querying a notebook, the response contains answer text with embedded citation markers (e.g., `[1]`, `[2, 3]`, `[5-7]`). These citation numbers are **indices into an internal citation list**, not direct indices into the notebook's source list.

### Response Structure (Query RPC)

Each response chunk is a `wrb.fr` payload containing JSON with the following top-level structure:

```
parsed[0]  - Answer metadata
  [0] - Answer text (string)
  [2] - Master list of source UUIDs used (not indexed by citation number)
  [4] - Annotations (text ranges with citation indices)

parsed[1]  - Citation list (array of citation entries)
  Each entry at index `i` corresponds to citation number `[i+1]`
  
parsed[2]  - Offset mapping (text range → citation indices)
```

### Citation Entry Structure

Each entry in `parsed[1]` (the citation list) at index `i` corresponds to citation `[i+1]`:

```json
[
  null,                    // [0]
  null,                    // [1]
  0.6925...,              // [2] Relevance score
  [[null, 13479, 14020]], // [3] Text offset range
  [...],                  // [4] Passage text and formatting
  [                       // [5] Source ID container
    [
      ["22e391d8-ddf4-..."]  // [5][0][0][0] = Source UUID
    ],
    "a0d8d307-..."
  ],
  ["b5ef2a72-..."]        // [6] Citation instance ID
]
```

**Key Path**: `citation_entry[5][0][0][0]` contains the Source UUID.

### Multiple Citations → Same Source

The backend creates a new citation entry for each **passage** cited, not each source. This means:
- Citation `[1]` might reference Source A, passage 1
- Citation `[2]` might reference Source A, passage 2
- Citation `[3]` might reference Source B

This explains why responses may contain `[18]` even when only 9 sources exist—there are 18 unique cited passages.

### Client Implementation

To display correct source titles:
1. Extract the citation list from `parsed[1]`
2. For each cited number in the answer text, look up `citation_list[num-1][5][0][0][0]` to get the Source UUID
3. Map the Source UUID to the source title using the notebook's source list

