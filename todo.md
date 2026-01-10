# NLM CLI - Todo List

## UX Issues
- [ ] `nlm notebook get` output is raw and "not nice". Needs a pretty-printed table or structured format for single notebook details. <!-- id: 4 -->

## Login Issues

- [ ] `nlm login --legacy` succeeds but subsequent commands report "Cookies have expired". Investigate cookie persistence or `browser-cookie3` caching. <!-- id: 1 -->

## Potential Improvements
- [ ] Investigate if auto-refresh of authentication is viable for long-running sessions. <!-- id: 2 -->
- [ ] Improved error handling when CDP fails to launch Chrome. <!-- id: 3 -->
