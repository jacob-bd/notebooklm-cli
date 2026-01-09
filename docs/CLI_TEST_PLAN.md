# NotebookLM CLI - Comprehensive Test Plan

**Purpose:** Verify all CLI commands work correctly before GA release.  
**Version:** v0.1.0  
**Last Updated:** 2026-01-09

---

## Prerequisites

```bash
# Install CLI
cd /path/to/notebooklm-cli
pip install -e .

# Verify installation
nlm --version

# Authenticate (required before running tests)
nlm login
nlm login --check  # Should show "Notebooks found: N"
```

---

## Test Configuration

```bash
# Hardcoded test resources
export TEST_YOUTUBE_URL="https://www.youtube.com/watch?v=d-PZDQlO4m4"
export TEST_URL="https://en.wikipedia.org/wiki/Artificial_intelligence"

# Rate limiting (wait between API calls to avoid hitting limits)
export TEST_THROTTLE_MS="${TEST_THROTTLE_MS:-2000}"  # 2 seconds between calls
```

---

## Pre-Test Setup (Interactive)

Before running tests, you'll need to provide a Google Drive document that you can edit.

### Step 1: Provide Your Drive Document

**Why?** The staleness/sync test requires modifying a document to verify the CLI detects changes.

```
Please provide a Google Drive document or slide deck URL that you can edit:
Example: https://docs.google.com/document/d/1KQH3eW0hMBp7WKukQ1oURhnW-SdOT1qq-kEZaVLWGB8/edit
```

Extract the document ID from the URL and set it:
```bash
export TEST_DRIVE_DOC_ID="<your-doc-id>"
export TEST_DRIVE_DOC_TITLE="My Test Document"
export TEST_DRIVE_DOC_TYPE="doc"  # Options: doc, slides, sheets, pdf
```

### Step 2: Remember the Freshness Test

> **⚠️ IMPORTANT:** Later in the test (Group 10), you will be asked to:
> 1. Make a small edit to your Drive document
> 2. Verify the CLI detects it as "stale"
> 3. Sync the document
> 4. Verify it's now "fresh"
>
> Keep your Drive document open in another tab!

---

## Test Execution Flow

The tests are ordered for optimal execution:

1. **Setup** - Auth verification, create test notebook
2. **Early Background Tasks** - Start deep research (takes 3-5 min)
3. **Source Tests** - Add URL, text, YouTube, Drive sources
4. **Query Tests** - Chat and query functionality
5. **Generation Tests** - Audio, video, reports, etc.
6. **Research Tests** - Check deep research status, import
7. **Drive Sync** - Interactive staleness check
8. **Cleanup** - Delete test notebook

---

## Test Group 1: Authentication

### Test 1.1 - Help: Login
```bash
nlm login --help
```

**Expected output includes:**
- `--legacy / -l` - browser-cookie3 fallback
- `--browser / -b` - browser selection for legacy mode
- `--manual / -m` - import from file
- `--check` - validate current auth
- `--profile / -p` - profile name
- `--file / -f` - cookie file path

---

### Test 1.2 - Functionality: CDP Login
```bash
nlm login
```

**Expected:**
- Chrome browser launches
- Message: "Using Chrome DevTools Protocol"
- No keychain prompt on macOS
- Success: "Cookies: N extracted"
- Success: "CSRF Token: Yes"

---

### Test 1.3 - Functionality: Check Valid Auth
```bash
nlm login --check
```

**Expected:**
- Makes real API call (not just file check)
- Shows: "Authentication valid!"
- Shows: "Notebooks found: N" (N > 0)

---

### Test 1.4 - Functionality: Check Invalid Auth
**Setup:** Corrupt or delete credentials

```bash
rm -rf ~/Library/Application\ Support/nlm/profiles/test-invalid
nlm login --check -p test-invalid
```

**Expected:**
- Exit code: 2
- Error about missing profile or auth failure
- Hint to run `nlm login`

---

## Test Group 2: Setup (Create Test Notebook)

### Test 2.1 - Create Test Notebook
```bash
nlm notebook create "NLM CLI Test - $(date +%Y%m%d-%H%M%S)"
```

**Expected:**
- Success message with title
- Shows notebook ID

**Capture:** `NOTEBOOK_ID=<id>`

---

### Test 2.2 - Verify Notebook Creation
```bash
nlm notebook get $NOTEBOOK_ID
```

**Expected:** Shows notebook with 0 sources

---

## Test Group 3: Start Deep Research (Background Task)

> **IMPORTANT:** Deep research takes 3-5 minutes. We start it early and check results later.

### Test 3.1 - Start Deep Research
```bash
nlm research start "artificial intelligence applications" --mode deep --notebook-id $NOTEBOOK_ID
```

**Expected:**
- Research started
- Shows task ID
- Message about ~5 minute duration

**Capture:** `DEEP_TASK_ID=<task_id>` (we'll check this in Test Group 9)

---

## Test Group 4: Source Management

### Test 4.1 - Add URL Source
```bash
nlm source add $NOTEBOOK_ID --url $TEST_URL
```

**Expected:** Source added, shows title

**Throttle:** `sleep 2`

---

### Test 4.2 - Add YouTube Source
```bash
nlm source add $NOTEBOOK_ID --url $TEST_YOUTUBE_URL
```

**Expected:** YouTube source added

**Throttle:** `sleep 2`

---

### Test 4.3 - Add Text Source
```bash
nlm source add $NOTEBOOK_ID --text "This is a test document about machine learning and neural networks." --title "Test Text Document"
```

**Expected:** Text source added with custom title

**Throttle:** `sleep 2`

---

### Test 4.4 - Add Drive Document Source
```bash
nlm source add $NOTEBOOK_ID --drive $TEST_DRIVE_DOC_ID --title "$TEST_DRIVE_DOC_TITLE" --type doc
```

**Expected:** Drive source added

**Note:** For staleness testing later, users need an editable document.

**Throttle:** `sleep 2`

---

### Test 4.5 - List Sources
```bash
nlm source list $NOTEBOOK_ID
```

**Expected:**
- Table with 4 sources
- Columns: ID, Title, Type

**Capture:** `SOURCE_ID=<first_source_id>` for later tests

---

### Test 4.6 - List Sources JSON
```bash
nlm source list $NOTEBOOK_ID --json
```

**Expected:** Valid JSON array with 4 items

---

### Test 4.7 - List Sources Quiet
```bash
nlm source list $NOTEBOOK_ID --quiet
```

**Expected:** 4 lines, each with just a UUID

---

### Test 4.8 - Get Source Details
```bash
nlm source get $SOURCE_ID
```

**Expected:** Source details with title, type

---

### Test 4.9 - Describe Source (AI Summary)
```bash
nlm source describe $SOURCE_ID
```

**Expected:**
- AI-generated summary
- Keywords list

---

### Test 4.10 - Get Source Content
```bash
nlm source content $SOURCE_ID
```

**Expected:** Raw text content (no AI processing)

---

## Test Group 5: Notebook Operations

### Test 5.1 - Notebook List Variations
```bash
# Default
nlm notebook list

# JSON
nlm notebook list --json

# Quiet (IDs only)
nlm notebook list --quiet

# Title format
nlm notebook list --title

# Full columns
nlm notebook list --full
```

**Expected:** Each format works correctly

---

### Test 5.2 - Describe Notebook
```bash
nlm notebook describe $NOTEBOOK_ID
```

**Expected:**
- AI-generated summary of sources
- Suggested topics

---

### Test 5.3 - Rename Notebook
```bash
nlm notebook rename $NOTEBOOK_ID "NLM CLI Test - Renamed"
```

**Expected:** Success message with new title

---

## Test Group 6: Query & Chat

### Test 6.1 - Basic Query
```bash
nlm notebook query $NOTEBOOK_ID "What topics are covered in these sources?"
```

**Expected:**
- AI response
- Shows conversation ID

**Capture:** `CONVERSATION_ID=<conv_id>`

---

### Test 6.2 - Follow-up Query
```bash
nlm notebook query $NOTEBOOK_ID "Tell me more about AI" --conversation-id $CONVERSATION_ID
```

**Expected:** Response uses conversation context

---

### Test 6.3 - Chat Configuration
```bash
# Learning guide mode
nlm chat configure $NOTEBOOK_ID --goal learning_guide

# Custom prompt
nlm chat configure $NOTEBOOK_ID --goal custom --prompt "Answer in bullet points"

# Response length
nlm chat configure $NOTEBOOK_ID --response-length shorter
```

**Expected:** Each configuration succeeds

---

### Test 6.4 - Chat Error Case
```bash
nlm chat configure $NOTEBOOK_ID --goal custom
```

**Expected:** Error: "--prompt is required when goal is 'custom'"

---

## Test Group 7: Content Generation

> **Throttling Reminder:** Wait 2-5 seconds between generation calls to avoid rate limits.

### Test 7.1 - Create Audio (Brief)
```bash
nlm audio create $NOTEBOOK_ID --format brief --length short --confirm
```

**Expected:** Audio generation started

**Throttle:** `sleep 5`

---

### Test 7.2 - Create Report
```bash
nlm report create $NOTEBOOK_ID --format "Briefing Doc" --confirm
```

**Expected:** Report generation started

**Throttle:** `sleep 5`

---

### Test 7.3 - Create Quiz
```bash
nlm quiz create $NOTEBOOK_ID --count 2 --difficulty 2 --confirm
```

**Expected:** Quiz generation started

**Throttle:** `sleep 3`

---

### Test 7.4 - Create Flashcards
```bash
nlm flashcards create $NOTEBOOK_ID --difficulty medium --confirm
```

**Expected:** Flashcards generation started

**Throttle:** `sleep 3`

---

### Test 7.5 - Create Mind Map
```bash
nlm mindmap create $NOTEBOOK_ID --title "Test Mind Map" --confirm
```

**Expected:** Mind map created

---

### Test 7.6 - List Mind Maps
```bash
nlm mindmap list $NOTEBOOK_ID
```

**Expected:** Shows created mind map

---

### Test 7.7 - Check Studio Status
```bash
nlm studio status $NOTEBOOK_ID
```

**Expected:** Lists all generated artifacts with status

---

## Test Group 8: Fast Research (Complete Cycle)

### Test 8.1 - Start Fast Research
```bash
nlm research start "machine learning basics" --mode fast --notebook-id $NOTEBOOK_ID
```

**Expected:**
- Research started
- Estimated time: ~30 seconds

**Capture:** `FAST_TASK_ID=<task_id>`

---

### Test 8.2 - Check Fast Research Status
```bash
nlm research status $NOTEBOOK_ID --max-wait 60
```

**Expected:**
- Status: completed
- Sources found: ~10

---

### Test 8.3 - Import Fast Research Sources
```bash
nlm research import $NOTEBOOK_ID $FAST_TASK_ID --indices 0,1,2
```

**Expected:** 3 sources imported

---

## Test Group 9: Deep Research (Check Background Task)

### Test 9.1 - Check Deep Research Status
```bash
# By now, deep research from Test 3.1 should be complete
nlm research status $NOTEBOOK_ID --max-wait 120
```

**Expected:**
- Status: completed
- Sources found: ~40+
- Report available

---

### Test 9.2 - Import Deep Research Sources
```bash
nlm research import $NOTEBOOK_ID $DEEP_TASK_ID
```

**Expected:** All sources imported

---

## Test Group 10: Drive Sync (Interactive)

> **⚠️ USER INTERACTION REQUIRED**
>
> This test requires you to modify the test Drive document to trigger staleness detection.

### Test 10.1 - Check Initial Freshness
```bash
nlm source stale $NOTEBOOK_ID
```

**Expected:** Shows Drive sources with freshness status (likely all fresh)

---

### Test 10.2 - Modify Drive Document

**⏸️ PAUSE: Please modify your test Drive document now:**
1. Open: https://docs.google.com/document/d/$TEST_DRIVE_DOC_ID
2. Add or change some text
3. Wait 10 seconds
4. Continue with Test 10.3

---

### Test 10.3 - Check Staleness After Edit
```bash
nlm source stale $NOTEBOOK_ID
```

**Expected:** Modified source shows as stale

---

### Test 10.4 - Sync Stale Sources
```bash
nlm source sync $NOTEBOOK_ID --confirm
```

**Expected:** Stale sources synced

---

### Test 10.5 - Verify Sync
```bash
nlm source stale $NOTEBOOK_ID
```

**Expected:** All sources now fresh

---

## Test Group 11: Delete Source (Mid-Test)

### Test 11.1 - Delete One Source
```bash
nlm source delete $SOURCE_ID --confirm
```

**Expected:** Source deleted

---

## Test Group 12: Cleanup (LAST)

### Test 12.1 - Delete Test Notebook
```bash
nlm notebook delete $NOTEBOOK_ID --confirm
```

**Expected:** Notebook and all contents permanently deleted

---

## Quick Copy-Paste Test Script

```bash
#!/bin/bash
# NLM CLI Test Script
set -e

# Config
TEST_YOUTUBE_URL="https://www.youtube.com/watch?v=d-PZDQlO4m4"
TEST_DRIVE_DOC_ID="1KQH3eW0hMBp7WKukQ1oURhnW-SdOT1qq-kEZaVLWGB8"
TEST_URL="https://en.wikipedia.org/wiki/Artificial_intelligence"
THROTTLE=2

echo "=== NLM CLI Test Suite ==="
echo ""

# Auth check
echo "1. Checking auth..."
nlm login --check
sleep $THROTTLE

# Create notebook
echo "2. Creating test notebook..."
RESULT=$(nlm notebook create "CLI Test $(date +%H%M%S)" 2>&1)
echo "$RESULT"
NOTEBOOK_ID=$(echo "$RESULT" | grep -oE '[0-9a-f-]{36}' | head -1)
echo "NOTEBOOK_ID=$NOTEBOOK_ID"
sleep $THROTTLE

# Start deep research early
echo "3. Starting deep research (background)..."
nlm research start "AI trends 2025" --mode deep --notebook-id $NOTEBOOK_ID
sleep $THROTTLE

# Add sources
echo "4. Adding sources..."
nlm source add $NOTEBOOK_ID --url "$TEST_URL"
sleep $THROTTLE
nlm source add $NOTEBOOK_ID --url "$TEST_YOUTUBE_URL"
sleep $THROTTLE
nlm source add $NOTEBOOK_ID --text "Test content" --title "Test Doc"
sleep $THROTTLE
nlm source add $NOTEBOOK_ID --drive "$TEST_DRIVE_DOC_ID" --title "Test Drive Doc" --type doc
sleep $THROTTLE

# List sources
echo "5. Listing sources..."
nlm source list $NOTEBOOK_ID

# Query
echo "6. Querying notebook..."
nlm notebook query $NOTEBOOK_ID "Summarize these sources"
sleep $THROTTLE

# Generate content
echo "7. Generating audio..."
nlm audio create $NOTEBOOK_ID --format brief --length short --confirm
sleep 5

# Check studio
echo "8. Checking studio status..."
nlm studio status $NOTEBOOK_ID

# Fast research
echo "9. Fast research..."
nlm research start "machine learning" --mode fast --notebook-id $NOTEBOOK_ID
sleep $THROTTLE
nlm research status $NOTEBOOK_ID --max-wait 60

# Check deep research
echo "10. Checking deep research..."
nlm research status $NOTEBOOK_ID --max-wait 120

# Cleanup
echo ""
read -p "Press Enter to delete test notebook or Ctrl+C to keep it..."
nlm notebook delete $NOTEBOOK_ID --confirm

echo "=== Tests Complete ==="
```

---

## Summary Checklist

After completing all tests, verify:

- [ ] Authentication works (CDP login, --check validates)
- [ ] All `--help` commands show correct options
- [ ] All CRUD operations work (create, read, update, delete)
- [ ] All output formats work (table, JSON, quiet, title, full)
- [ ] All source types work (URL, YouTube, text, Drive)
- [ ] Query and chat configuration work
- [ ] All content generation works (audio, report, quiz, flashcards, mindmap)
- [ ] Research works (fast and deep modes)
- [ ] Drive sync detects staleness and syncs
- [ ] Confirmation prompts work as expected
- [ ] Error messages are clear and helpful
- [ ] Rate limiting doesn't cause failures (with throttling)

---

## Rate Limiting Guidelines

To avoid API rate limits during testing:

| Operation Type | Recommended Delay |
|---------------|-------------------|
| Source operations | 2 seconds |
| Content generation | 5 seconds |
| Research operations | 2 seconds |
| Query operations | 2 seconds |

For automated testing, implement exponential backoff on 429 errors.
