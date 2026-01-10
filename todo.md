# NLM CLI - Todo List

## ✅ Completed

- [x] `nlm notebook get` output is raw and "not nice". Now fixed with structured parsing and pretty-printed tables.
- [x] **Mind Map Deletion Bug**: Success reported but artifact persisted in backend. Fixed by implementing two-step RPC sequence (`AH0mwd` + `cFji9` sync) and filtering tombstone entries from list.
- [x] **Research Status Bug**: Fixed status code mapping (6=completed, not 2).
- [x] **Auto-refresh tokens**: Implemented in `_refresh_auth_tokens()` - CSRF/session ID auto-refreshed on Code 16 errors.
- [x] **Session expiry warning**: Handled - clear error message tells user to run `nlm login`.
- [x] **Comprehensive `--ai` documentation**: 378 lines of verified CLI reference.
- [x] **PyPI Publishing**: Published as `notebooklm-cli` with automated GitHub Actions workflow.
- [x] **Legacy login removed**: `--legacy` mode used browser-cookie3 which reads stale cookies from Chrome's SQLite. CDP is the only reliable method.
- [x] **Branding**: Added a new futuristic/cyberpunk logo to the README.
- [x] **Documentation**: Complete README rewrite with comprehensive installation, commands, AI integration, aliases, and proper docs links.

## 🔴 Open Items

### Potential Improvements
- [ ] Add `nlm notebook create --from-research "query"` shortcut for one-command research workflow.
- [ ] Consider adding `--wait` flag to generation commands to poll until completion.
