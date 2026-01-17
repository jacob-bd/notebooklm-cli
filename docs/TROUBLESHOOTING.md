# Troubleshooting

Common issues and solutions for the NotebookLM CLI.

## Quick Reference

| Error | Solution |
|-------|----------|
| "Cookies have expired" | Run `nlm login` |
| "Notebook not found" | Check ID with `nlm notebook list` |
| "Research already in progress" | Use `--force` flag or import existing results |
| Chrome doesn't launch | Ensure Chrome is installed and in your PATH |
| "nodename nor servname provided" | Network access blocked (see [Codex Users](#openai-codex-users)) |

---

## Authentication Issues

### Cookies Expired

**Error:** `Cookies have expired` or `Authentication failed`

**Solution:** Re-authenticate by running:
```bash
nlm login
```

NotebookLM sessions typically last ~20 minutes. If you're scripting or automating, you may need to re-authenticate periodically.

### Chrome Doesn't Launch

**Error:** Chrome doesn't open during `nlm login`

**Solutions:**
1. Ensure Google Chrome is installed
2. Check Chrome is in your PATH
3. Close any existing Chrome instances that may conflict
4. Try running with verbose output: `nlm login --debug` (if available)

---

## Network Issues

### OpenAI Codex Users

If you're using `nlm` from [OpenAI Codex CLI](https://github.com/openai/codex) and get DNS errors like:

```
Error: Request failed: [Errno 8] nodename nor servname provided, or not known
Hint: Check your internet connection.
```

**Cause:** Codex runs commands in a sandboxed environment that **blocks network access by default**.

**Solution:** Add the following to `~/.codex/config.toml`:

```toml
[sandbox_workspace_write]
network_access = true
```

Alternatively, run individual commands with full network access:
```bash
codex exec --sandbox danger-full-access "nlm notebook list"
```

---

## Source Issues

### Research Already in Progress

**Error:** `Research already in progress`

**Solutions:**
1. Wait for the current research to complete: `nlm research status <notebook-id>`
2. Import existing results: `nlm research import <notebook-id> <task-id>`
3. Force a new research: `nlm research start "query" --notebook-id <id> --force`

### Source Not Found

**Error:** `Source not found`

**Solutions:**
1. Verify the source ID: `nlm source list <notebook-id>`
2. Check if you're using the correct notebook
3. Ensure the source wasn't deleted

---

## Content Generation Issues

### Artifact Still Generating

**Error:** Status shows "in_progress" for a long time

**Solution:** Check studio status periodically:
```bash
nlm studio status <notebook-id>
```

Generation times vary:
- Audio podcasts: 2-5 minutes
- Reports/flashcards: 30-60 seconds
- Deep research: 4-5 minutes

### Generation Failed

**Error:** Artifact status shows "failed"

**Solutions:**
1. Ensure you have at least one source in the notebook
2. Check if NotebookLM service is available
3. Try regenerating the content

---

## Getting Help

If your issue isn't listed here:

1. Check the [GitHub Issues](https://github.com/jacob-bd/notebooklm-cli/issues)
2. Run `nlm --ai` to see the full command reference
3. Open a new issue with details about your error
