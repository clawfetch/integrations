# Changelog

All notable changes to `@clawfetch/ai-sdk` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - Unreleased

### Added
- `clawfetchTools(options)` returning Vercel AI SDK v7 tools for every paid ClawFetch endpoint: fetch, render, extract, research, parse, domains/check, domains/suggest.
- Tool descriptions state the per-call USDC price.
- Options: `privateKey` (falls back to `CLAWFETCH_PRIVATE_KEY`), `client`, `maxChars`.
- `createClawFetchClient(options)` helper.
