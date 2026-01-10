# NLM CLI - Todo List

## UX Issues
- [x] `nlm notebook get` output is raw and "not nice". Now fixed with structured parsing and pretty-printed tables. <!-- id: 4 -->

## Login Issues

- [ ] `nlm login --legacy` succeeds but subsequent commands report "Cookies have expired". Investigate cookie persistence or `browser-cookie3` caching. <!-- id: 1 -->
- [ ] **Session Tracking**: Track `last_login_time` in profile to warn user when session is likely expired (~20 min). Distinguish between stale API response and auth expiration. <!-- id: 5 -->

## Potential Improvements
- [ ] Investigate if auto-refresh of authentication is viable for long-running sessions. <!-- id: 2 -->
- [ ] Improved error handling when CDP fails to launch Chrome. <!-- id: 3 -->
