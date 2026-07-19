# Security Policy

## Scope

This covers the Swarm Agent configuration for OpenCode. The swarm runs locally and uses free API models — no user data is sent to external services beyond the model API endpoints.

## Known Security Notes

- **GITHUB_TOKEN**: now reads from `{env:GITHUB_TOKEN}` in opencode.json instead of a hardcoded PAT. Set `export GITHUB_TOKEN="ghp_..."` in your shell profile.
- **Filesystem MCP**: scoped to `~/.config/opencode/` — the agent cannot read/write outside this directory
- **All evaluation documents are auto-generated**: do not treat them as third-party audits

## Reporting

If you discover a security issue, please open a GitHub issue and avoid public disclosure until addressed.
