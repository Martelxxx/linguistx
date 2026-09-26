# Linguist-X Passenger v77 — developer handoff report

## What changed

v77 turns the v76 passenger codebase into a substantially more maintainable handoff without changing the approved passenger experience.

### In-source documentation

The nine core Python runtime modules now have developer-facing module/class/function/method documentation throughout. The comments focus on intent, invariants, security boundaries, state ownership, failure semantics, and extension rules rather than narrating obvious syntax.

`index.html` and `passenger-only.html` now contain render-neutral `DEVNOTE` comments describing the source map, visual-baseline rule, DOM contract, application-state rules, localization, navigation/motion, Live-screen sensitivity, Demo truthfulness, flight discovery, scanner lifecycle, and Integration/guest lifecycle.

Tests, CI, service worker, Python packaging, production requirements, environment template, Docker candidate, and ignore files also include maintainer notes where their purpose could otherwise be misunderstood.

### Engineering documentation page

`developer-documentation.html` documents the passenger app end to end: product invariants, setup, architecture, file ownership, frontend/backend models, translation gateway contract, browser-facing APIs, security/privacy, guest lifecycle, providers, PWA/cache policy, accessibility, testing, checklist governance, deployment path, safe-change protocol, troubleshooting, and known open production gates.

The bottom of the desktop-only Mobile app checklist links to this page as **Engineering documentation ↗**. The passenger-only file has no visible link, and the ASGI production runtime intentionally returns 404 for the internal page.

### Handoff rules

`DEVELOPER_HANDOFF.md` is the concise repository entry point for a new engineer. It identifies product invariants, source-of-truth files, architectural boundaries, security rules, and the required safe-change workflow.

## UX preservation

No intentional passenger UX or functional changes were made. After removing only the new `DEVNOTE` comments, `passenger-only.html` is byte-for-byte identical to the approved v75/v76 baseline. The service-worker cache version was bumped so a local installed preview does not continue serving an older shell.

## Checklist correction

The internal ledger now reflects the user’s confirmed Test 5 retest: all six manual local fixture groups are recorded as user-passed. No additional contractual requirement was marked complete solely because those fixture tests passed.
