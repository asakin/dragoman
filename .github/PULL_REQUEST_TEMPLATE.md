<!-- Thanks for sending a PR! Quick checklist below. -->

## Summary

<!-- One paragraph: what changes and why. Link the issue if there is one. -->

## How to verify

<!-- Steps a reviewer can run locally to see the change in action. Commands welcome. -->

```bash
# e.g.
pip install -e .
dragoman <subcommand> ...
```

## Checklist

- [ ] All commits are signed off (`git commit -s`) — DCO required, see [CONTRIBUTING.md](../CONTRIBUTING.md).
- [ ] Manually verified with a smoke test (`dragoman --help`, the modified subcommand, or `dragoman ask` against a real provider).
- [ ] README updated if behavior or contracts changed.
- [ ] No new dependencies added without justification.
- [ ] Dragoman remains tool-less (no agent loop, no shell execution, no `bash` capability).
- [ ] Agent file (`templates/dragoman.md`) untouched, OR changes called out explicitly with rationale.

## Notes for the reviewer

<!-- Anything non-obvious: design trade-offs, follow-ups deferred, related issues. -->
