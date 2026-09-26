LINGUIST-X v78 — WORDLY SPLASH MORPH + DEVELOPER HANDOFF

PURPOSE
This release preserves the established passenger workflows and Home-screen design while adding one
explicitly approved launch presentation: a Wordly shared-element splash/morph. It carries forward the
v77 developer-handoff documentation and the v76 engineering hardening.

START HERE
  1. python3 start.py
  2. Open http://127.0.0.1:8765/
  3. The bottom of the right-side Mobile app checklist now links to:
     http://127.0.0.1:8765/developer-documentation.html

DEVELOPER DOCUMENTATION
- developer-documentation.html: comprehensive internal architecture/UX/API/security/testing/deployment guide.
- DEVELOPER_HANDOFF.md: continuation rules and safe-change workflow.
- Core Python modules now include responsibility/invariant docstrings throughout.
- index.html and passenger-only.html include render-neutral DEVNOTE source-map and section comments.
- Tests/config/service-worker files include maintainer notes where their purpose is non-obvious.

PASSENGER EXPERIENCE PRESERVATION
Outside the isolated v78 splash blocks, the passenger-only HTML/CSS/JS recovers the approved
v75/v77 passenger surface after removing DEVNOTE comments. v78 preserves all established passenger
workflows and the Home layout. Its only intentional passenger-facing change is the launch Wordly
shared-element splash/morph. The desktop-only internal checklist continues to include the Engineering
documentation link introduced in v77.
The service-worker cache name is bumped so local previews do not retain the older shell.

TRACKER
All six user-reported local fixture test groups are recorded as passed, including the v75 Test 5
retest. This does not convert fixture evidence into live-provider or contractual acceptance.
The mobile tracker remains 10/10 prototype tasks and 1/32 contractual mobile requirements done.

VALIDATION
- python3 -m unittest discover -s tests -v
- python3 quality/verify_v78.py
- developer documentation route is development-only in the ASGI runtime and returns 404 in production.

Do not deploy index.html publicly; production root uses passenger-only.html. Real provider media,
production infrastructure, load certification, native-device acceptance, and contractual acceptance
remain separate gates.

----- PREVIOUS RELEASE NOTES -----
LINGUIST-X v76 — PASSENGER EXPERIENCE PRESERVED, ENGINEERING HARDENED

START HERE: python3 start.py (same one-command local Demo + Integration experience).
All six user-reported manual test groups passed after v75's Test 5 correction.
The mobile tracker records 10/10 prototype items and 1/32 contractual items as done.
The changed checklist is embedded in index.html; the passenger screens and executable
code remain identical to v75. Read V76_ENGINEERING_REPORT.md and QA_RESULTS_v76.md.

For the optional production-style ASGI transport: install dependencies from
requirements-production.txt, run `python3 start_asgi.py` and see V76_ENGINEERING_REPORT.md. This codebase
is NOT yet proven multi-replica/production-capable; the P0/P1 engineering gates
and real-service/device acceptance remain open. Do not deploy externally.

NOTE: Legacy local flight/voice/weather API keys are no longer auto-recovered
from historical folders/ZIPs. If you relied on this, copy your keys into the
current .env or supply environment variables explicitly. No real keys ship.

----- HISTORIC V75 AND OLDER RELEASE NOTES (superseded where contradictory) -----
LINGUIST-X v75 — MOBILE GUEST ACCESS CORRECTION

Existing passenger app + outside-phone integration fixture + corrected mobile-only tracker.

SINGLE COMMAND (recommended): python3 start.py
This starts the same v75 server with both Demo and Integration Test available.
Use the right-side Translation source toggle; no second server or restart is needed.
The integration fixture supplies simulated test data, not live Wordly translation.
Advanced / previous commands remain supported:
  Demo only: python3 run.py
  With integration test fixture: LX_NO_SETUP=1 LX_ENABLE_FIXTURE=1 python3 run.py
Visit http://127.0.0.1:8765/ and switch to Integration in the right-side development panel.
Stop an older running local server with Ctrl+C before starting v75 on the same port.
Fixture is test data only; it is not Wordly and refuses LAN mode.

UI-09: done, per user's reported completion of six scanning tests.
MG-07: done, per explicit user approval of mobile in-app notifications.
Formal mobile tracker: 1/32 user-approved verified. Other contractual items still await full proof.

v75 QA status: User tests 1, 2, 3, 4 and 6 passed as reported. v74 Test 5 FAILED:
revoked/invalid/mismatched invitations displayed a warning but did not clearly block access.
v75 denies guest grants, state and event retrieval during negative fixture scenarios;
clears earlier grants on denied replacement joins; checks invite/flight/session binding;
and displays ACCESS BLOCKED in the translation panel. Public flight navigation is
still allowed: the important boundary is receiving protected translation data.
Automated negative tests pass; please rerun ONLY Test 5. This does not prove
production venue security or live Wordly delivery.
Mobile contract: 1/32 checked off (MG-07 user-approved); 10/10 prototypes completed.
Five manual test groups passing does not automatically verify composite contract items.

Read INTEGRATION_CONTRACT.md for supported routes, safe deployment and remaining dependencies.
Read TRACKER_MAINTENANCE.md for evidence and tracking rules.
Tests: python3 -m unittest discover -s tests -v

LINGUIST-X v73 — MOBILE APP DELIVERY TRACKER (INTERNAL)

Base: v72. Passenger experience, account-free gateway adapter, Demo / Integration toggle, and browser behavior are unchanged.

Open index.html for the internal desktop review with the collapsible right-side MOBILE APP CHECKLIST. The tracker includes 10 mobile prototype/test-harness tasks and the 32 mobile requirements in Exhibit C: A01–A12, 12 Gold areas, M AC 01–08. It excludes fleet, commissioning, remote support, standalone appliance/cloud work and overall contract gates. These belong in separate trackers.

Three distinct statuses are shown for applicable mobile requirements: UI (built/partial/not started/not applicable), Service (adapter/connected/not connected/not applicable), and Proof (verified/pending). An adapter is NOT a live integration. Contractual checkmarks require full measured evidence; this release changes scope and presentation, not the verified counts.

`requirements-progress.json` is the source of truth. Update reviewed statuses and evidence then run `python3 sync_progress.py` to embed the ledger into index.html. See TRACKER_MAINTENANCE.md. Neither the UI nor the toggle can self-approve a requirement.

Use passenger-only.html for a view without tracker or developer controls. This is still a preview; do not treat it as approved app-store or production deployment. No real Wordly / AES67 media has been connected.

SOURCE GAP: Exhibit A references Integrated Requirements Alpha Beta Gold v0.2, not provided separately with the files. Reconcile it when available.

----- PREVIOUS README -----
LINGUIST-X v66 — RESTORED SPATIAL TRANSITIONS
===========================================
Base: v65. All airline logo assets, flight search, confirmation, Live layout,
and inbox behavior are retained.

- Fix: entering-page opaque background had covered the v50 spatial growth layer.
  It is now transparent only during the material transition, allowing the
  selected control to grow into the destination surface.
- Fix: headings and CTAs retain their own early arrival; remove redundant
  parent opacity animation that hid the heading behind a second fade.
- Async/programmatic navigation uses a centered current-page origin if the
  real gesture is unavailable; normal tap-based transitions still start at
  the touched control.
- Shared scanner hero to camera morph and contextual heading dissolve remain.
- Respect browser/OS Reduced Motion and app-level Less Motion. Both deliberately
  skip spatial motion for accessibility.
- Cache version v66 prevents older transition CSS from lingering in the PWA.

LINGUIST-X v64 — CONSISTENT CENTERED LIVE HEADER
=================================================
Base: v63. The Inbox back control, direct logo-to-Home navigation, and all
other flight, translation, and glass features remain unchanged.

- Live header: language selector at far LEFT, mark at true horizontal CENTER,
  and ··· menu at far RIGHT, without overlapping any touch targets.
- All secondary-page marks, including the Live mark, share the exact 49 x 40
  CSS image box (43 x 36 on compact widths <= 359 px).
- Home's deliberately larger hero mark stays unchanged.
- New service-worker version replaces the cached v63 shell.

LINGUIST-X v62 — BOLD FLIGHT INPUT / DELTA IDENTITY / LOGO HOME NAVIGATION
==========================================================================
Base: v61. The original v56 home artwork/shadows, v59 liquid gate,
and v60 progressive flight search are preserved.

- Flight numbers typed in manual search use weight 780. Placeholder remains quiet.
- Delta Air Lines (DL / DAL) is bundled as vetted SVG artwork under
  airlines/custom/DL.svg and resolves locally, without external services.
  Korean Air (KE / KAL) remains bundled. The local vector is Delta's
  triangular icon, not its full wordmark.
- All eight header back arrows are removed. Every visible Linguist-X logo
  (welcome, all secondary headers, and Live) is a tap/click and keyboard
  shortcut to Home. The same logo transition is retained.
- The Inbox's "Back to live" is now "Listen live" and Privacy's "Back to
  preferences" is "Preferences". Both existing destinations remain reachable.
- Go to home has accessible labels in all six languages.
- New service-worker cache name ensures a fresh shell after updating.

LINGUIST-X v61 — EXPANDED AIRLINE LOGOS / QUIET FLIGHT CONFIRMATION
===================================================================
Base: v60 (progressive flight search) with v59 refractive-gate correction.

CONFIRMATION
- Replaces “Confirm you're following the correct departure” with a calm,
  direct question: “Is this the flight you’re looking for?”
- Replaces the single dark Continue/Confirm CTA with two equal-sized,
  softly differentiated neo buttons, styled to resemble the Live toolbar:
  “Yes, this is my flight” (very pale blue) and “No, change flight”
  (near-white). Yes moves to Live; No returns to flight selection.
- Both choices and the question are translated into the six app languages.

AIRLINE LOGOS
- Korean Air (KE) is now shipped locally as an HD SVG; KAL (ICAO) aliases to KE.
  This fixes missing Korean Air identity without requiring online image fetch.
- 89 curated SVG-source candidates cover major international airlines; vectors
  are fetched, checked, and cached the first time a carrier is encountered.
- An 82-airline built-in IATA/ICAO seed provides fallback lookup even when the
  remote airline directory cannot be downloaded.
- Existing dynamic upstream raster mapping still supports more carriers when
  network access permits. The source's 1,520 records contain 686 distinct
  usable IATA mappings in the observed snapshot, not 1,520 confirmed usable
  HD logos. Logos are not guaranteed for every airline.
- Additional vector assets in square artboards are rasterized at high device
  density and cropped to their nontransparent visible bounds, reducing tiny
  marks and clipping without stretching low-resolution images.
- A carrier's readable name stays visible when no valid logo can be shown.

LIBRARY INVENTORY
- AIRLINE_LOGOS.txt: readable list of 88 SVG candidates and 82 seed mappings.
- airlines/library.json: machine-readable list of those mappings.
- GET /api/airline-library: on-device inventory of bundled and cached SVGs,
  curated vector candidates, and the currently resolved remote directory count.
- Bundled guaranteed vectors: airlines/custom/KE.svg (Korean Air),
  airlines/custom/DL.svg (Delta Air Lines).

NOTE: The external catalog, SVG sources and PNG fallbacks are on-demand; they
require an internet connection until a mark has been cached. An optional .env
is not bundled. Airline logos are their owners' trademarks; inspect brand
and trademark requirements before production deployment.

RUN: Extract ZIP; run `python3 run.py`; open its displayed local URL.
Browser automation was blocked by the execution environment for v61. JS/Python
syntax, Korean Air vector XML, local image endpoint and catalog endpoint
were validated. Test appearance in target iPhone/Safari before sign-off.

-------------------------------------------------------------------

PREVIOUS VERSION NOTES:

LINGUIST-X v60 — PROGRESSIVE FLIGHT SEARCH
=========================================
Base: v59. The manual flight-search submit button is removed. As passengers type, matching flights are presented inline. Tap a resolved result to advance to the existing confirmation screen. Sample flights are explicitly marked; verified live results come from the same exact Aviationstack endpoint as v59 and are never automatically selected. Exact-code network lookups are debounced and only attempted for plausible flight numbers with at least two digits, preserving API quota. Rapid edits or navigation invalidate stale results. Scanner and live experiences remain unchanged.

Existing v59 notes:
LINGUIST-X v59 — LEGIBLE LIQUID GATE

This is a focused accessibility and appearance correction to v58.

The refraction is still real: the weather image behind the gate is aligned
with the flight card and displaced using SVG feDisplacementMap. However, v58's
insufficient milk tint let the dark night photo swallow the gray gate number
and CURRENT GATE label. v59 adds a calibrated pearl overlay OVER the optical
layer and BEHIND the information, with dark opaque typography, slightly
stronger label weight, and consistent colors during gate-change animations.

The result keeps the liquid-glass form, edge lighting, and environmental
context without making the gate read like a separate alarm or new UI style.

All other assets and code are unchanged from v58. Refer to the v58 package for
configuration/run.py requirements and integration notes.
LINGUIST-X v58 — SHADOW STABILITY / HD CARRIER MARKS / REFRACTIVE GATE
====================================================================
Base: exact v57 source, retaining every existing screen, backend integration, and v57 expanded flight details.

1. HOME: v56 and v57 contain the same two drop-shadow values. v58 keeps those
   precise values, preloads/decodes the mark, suppresses competing animation on
   the home image, and cleans up any lingering shared-logo flight on pageshow.
   This targets the reported first-render versus tab-return inconsistency.

2. AIRLINE MARKS: confirmation image stays fully contained with no forced 100%
   width/height, and the code retains its own space. Server now checks a trusted
   local airlines/custom/XX.svg or .png asset first, then an allowed vector
   source for EK (Emirates), then quality-gated catalog PNGs. The browser trims
   transparent bitmap padding and checks effective displayed pixel density;
   blurry marks are withheld rather than enlarged. Airlines still always
   display their readable names. The Emirates vector is fetched on demand and
   cached; its first retrieval requires internet. Other carriers without a
   suitably sharp asset may show name-only. To guarantee a specific logo,
   place a vetted SVG in airlines/custom/XX.svg. Third-party logos remain their
   owners' trademarks. SVG sources: Wikimedia Commons, Emirates Logo.svg.

3. LIVE GATE: the gate tile uses a weather-image sample aligned to the exact
   current flight card beneath it, displaced through an inline SVG filter
   (feTurbulence + feDisplacementMap). Separate liquid highlights/tint and an
   optical edge protect text contrast. The gate number, status and existing
   animations are not distorted. A less capable browser may display the static
   glass highlight instead of the displacement.

TESTING: Use python3 run.py from the extracted folder (Python 3.10+).
The shipped demo still needs your own optional .env settings. The .env is not
included. The SVG source requires network on first load; local .airline-cache
is created only at runtime. Refractive appearance should be checked on the
actual target iPhone/Safari before design sign-off.

====================================================================

Linguist-X v56 — Centered Logo Headers

Removed the section title beside the logo in all eight secondary page headers (Language, Find flight, Manual search, Scanner, Inbox, Preferences, Privacy, Confirmation). The logo remains centered at a consistent position within each header. The Live header remains unchanged, with the logo at left and language/menu controls at right. All in-page headings and the existing spatial logo transition remain unchanged. Updated the service-worker cache name for v56.

Linguist-X v55 — Elevated Home Logo

The welcome logo is larger and receives layered, soft drop shadows consistent with the application surfaces. Its shadow eases out/in during the existing shared-element header transition. Secondary-page logo size and all other visuals/functions are unchanged.

Linguist-X v54 — Animated Living Brain Orb + supplied logo refresh

The orb now paints changing luminous paths on a clipped canvas inside the static spherical edge. Pauses when hidden and honors Reduce Motion. The new user-provided blue A / green character logo uses a versioned URL to bypass cached old artwork.

Linguist-X v53 — Orb visibility, original logo, confirmation alignment

Fixes server route for living-orb.webp and upgrades the provided logo to a 2022 x 1350 transparent asset. Aligns confirmation card/button directly on the page grid. Existing flight and voice behavior remains unchanged.

Linguist-X v52 — Living Orb + Aesthetic Pass

Updated from v51. The orb image is bundled locally as living-orb.webp. v52 retains scanner, manual search, voice, and local-server integrations.

LINGUIST-X v51 — ONE-TAP PASSENGER FLOW
======================================
- Language selection: tap a row once to continue. The chosen row provides 210 ms of
  feedback and anchors the existing spatial transition to Find your flight.
  Dragging or stopping a scrolling list never chooses a language.
- With no Continue button, the six language rows are distributed through the
  available height. Short viewports retain natural scrolling and touch targets.
- A manual lookup with exactly one verified same-day departure goes directly to
  that flight's confirmation; multiple matches still show the selectable list.
  An unsuccessful lookup remains on the search screen with its feedback.
- Flight confirmation has one prominent action. The Back arrow returns to manual
  search or the scanner, depending on how the passenger reached confirmation.
- Spatial transitions and the scanner shared-element morph remain active; Reduced
  Motion retains the existing restrained behavior.
- Inbox and Preferences screens and interactions are unchanged.
- Existing local server and API-key configuration are unchanged. Your private
  .env is not included. To use your existing keys, copy your own .env locally.

Linguist-X Passenger v50 — Spatial Transitions

Changes: Flight selection cards return to their original upper position while retaining the v48 scan hero size. User-initiated navigation reveals destination views from the tapped control. Find ↔ Scanner uses a shared-element morph from the hero card to the camera viewport, and soft crossfades between headings. Header and logo retain their original geometry; Reduced Motion disables these animations. No changes to the Python server or API-key configuration.

LINGUIST-X v48 — SCAN HERO / FLIGHT FINDING
===========================================
- Replaces the two equally weighted Find your flight rows with a tall scan hero (~one-third viewport height) and a compact manual-search row.
- Adds a quiet, four-corner viewfinder preview with a small boarding-pass icon. No illustration, animation, new copy, or extra navigation.
- Anchors both methods toward the lower half of the screen, while the headline remains near the top and the sample preview stays in its separate footer.
- Includes compact-screen adjustments; scan and manual search retain their original navigation and localization.
- Versioned service-worker cache for clean refresh.

LINGUIST-X v47 — QUIET GATE UPDATE
================================
- Replaces the separate gate-update pill with a localized GATE UPDATED heading in the existing gate tile.
- The updated heading remains for the selected flight after the brief previous-gate reminder expires.
- On a new flight selection or demo reset, the label returns to CURRENT GATE.
- The old gate appears briefly as Previously B22; the existing animation and number centering remain.

LINGUIST-X v46 — CONTEXTUAL VOICE
================================

RUN
1. Extract ZIP; in the extracted folder run: python3 run.py
2. Open http://127.0.0.1:8765 (stop the previous version first).
3. Use your existing local .env file for AVIATIONSTACK_API_KEY,
   WEATHERAPI_KEY, and OPENAI_API_KEY; it is NOT included in this ZIP.
   Use HTTPS for remote-device microphone/camera testing.

NEW VOICE EXPERIENCE
- Announcement playback remains cached OpenAI TTS (coral voice).
- Once an announcement finishes playing, the microphone automatically opens
  for a 10-second follow-up window on the live screen.
- Opening Inbox automatically makes the microphone available. Each scroll,
  tap, key press, speech, or response refreshes its 45-second inactivity window.
  The microphone closes on inactivity, when leaving Inbox, or in background.
- Tap an Inbox announcement to put that announcement in conversation context.
- GPT-Live handles spoken clarification and questions in the selected language.
  Requests to repeat replay the original recorded announcement, not a rewrite.
- Flight answers use the selected flight snapshot, not a connected airport feed.
  Announcement and flight-status samples remain demonstrations.
- Actual microphone permission is controlled by the browser. If the voice
  connection is unavailable, normal reading and cached playback still work.

v40 — Expandable flight card: tap the card or Flight details; four source-conscious fields, responsive weather backdrop and reduced-motion support. Boarding time is not inferred from Aviationstack departure.

LINGUIST-X v38 — TEMPORARY GATE-CHANGE CONTEXT

1. Extract the ZIP, open Terminal in the extracted folder, and run python3 run.py.
2. Your keys stay local. To reuse configuration/audio, copy your existing .env and optional audio_cache folder into this folder; they are not included in this archive.
3. Open http://127.0.0.1:8765. Stop the older local server with Ctrl+C first.
4. Home has one meaningful CTA and a six-language animated welcome. Turn on Reduce Motion in Settings to show static Hello.
5. Every screen now carries the same top-logo identity. Consistent system typography, fewer competing surfaces and quieter controls are used app-wide.
6. The destination weather photos were optimized to WebP; flight state and the orb/X behavior were preserved.
7. Test prototype: simulated airport announcements and optional simulated flight-state scenarios are NOT real airport information. Verify operational changes with your airline.
8. SCANNER: Barcode and printed-flight-number recognition run concurrently; the first valid detection wins. A cropped JPEG from the visible scan region may be sent through your local server to OpenAI for printed-number recognition (up to three AI requests per scan session). The local Tesseract reader is a fallback when AI recognition is unavailable or inconclusive. Both detection methods look up a matching flight and show its origin and destination in a single on-camera confirmation sheet. Confirming proceeds directly to the live page; Scan again restarts capture. Barcode and manual entry remain available. Camera frames are not stored. OpenAI image input requires network access and may incur API costs. Check the displayed flight against airport signs.
9. Weather and live flight data require their respective local API integrations. For full camera/PWA function on iPhone, use HTTPS.

Do not publish the local test server or your .env.

V34 navigation: primary CTA and headline arrive promptly; supporting content follows within ~350 ms. The previous screen fades briefly under the new screen. Scanner camera/audio start without waiting. Animations respect OS Reduced Motion and the app Reduce Motion preference.

V35 DESIGN CHANGES
- The welcome logo remains centered and moves into the compact header during welcome-to-language navigation (reverses on return).
- Page counters removed and localized headers retained.
- Cancellation has a short, readable footer instead of a large takeover panel.
- Mild paired shadows and restrained neumorphism return throughout the interface; the orb stays on plain white.

V36 LOGO: Shared logo animates via measured left/top/width/height from the centered welcome artwork to the final header box, avoiding nonuniform stretching.


Version 37: Scan opens the camera directly. Barcode and printed OCR both resolve through the same route confirmation sheet; there is no second confirmation page. If multiple flights share a route, date/time helps distinguish them. Failed lookups never show an invented route or activate confirmation. Delay, gate change, boarding and diversion use legible status bands matching cancellation. The gate-change indicator is intentionally temporary: for 60 seconds show a quiet "Gate updated" badge, the previous gate, and the clear update band; from 60 seconds until three minutes show only the compact previous-gate reminder beneath the centered new gate; afterward return to the normal card. Both temporary cues can be dismissed without changing the current gate. A new verified change restarts this lifecycle, and normal re-renders do not. No indicator appears on initial flight load or when the gate has not changed. Automatic fake flight-state rotation is disabled for live Aviationstack flights.

V38 GATE CHANGE BEHAVIOR
- A valid change between two different gates starts the event. The current gate remains large and centered.
- 0–60 seconds: unobtrusive "Gate updated" badge at the top edge of the gate module, "Previously [gate]" beneath the current gate, and full readable explanation in the flight card.
- 60–180 seconds: the full band and badge disappear, leaving only the compact "Previously [gate]" reminder.
- After 180 seconds, or if the passenger taps the badge/reminder, the temporary context disappears; the new gate remains.
- Another gate change restarts the timer. Real flight updates must come from the live flight-data refresh; sample flight-state simulations remain samples.
- All six languages are supported; visual motion respects Reduced Motion.


V39 — QUIET MULTILINGUAL WELCOME
- Welcome has no supporting paragraph, keeping its large centered logo and Hello headline.
- Its single primary action says “Guide me” in six languages, synchronized with Hello.
- Text crossfades inside a fixed-size button; tapping works throughout the cycle.
- Accessible names remain stable in the selected language; reduced-motion mode holds English.
- Existing scanner, flight card, and back-to-home logo transition are unchanged.


v41: language changes crossfade smoothly; the expand chevron shares the checked-time row, and the orb scales to the available space.

V43 Manual lookup: field has safe inset focus ring and uppercase input in the app system font.


v44 — FLIGHT DATE FILTER
------------------------
Flight lookup now returns only flights scheduled to depart today in each
origin airport's local calendar day (using the provider's departure timezone).
The browser sends its local date only as a fallback when airport timezone data
is missing. Flights with no reliable departure date are omitted, rather than
shown as if they were today's. Flight numbers can be reused across dates.

If an older ZIP is still serving on port 8765, stop it (Control+C) and run
python3 run.py from this v44 folder. Reload the app to get the updated code.
Live provider data still depends on your Aviationstack plan and update cadence.


v57 — CARRIER IDENTITY & FULL FLIGHT DETAILS
- Confirmation: airline logo is placed to the right of the flight number (if available).
- The server queries a third-party airline identity catalog (1,520 records (959 have logo files; 716 have both a logo and IATA code))
  and fetches PNG logos on demand, caching successfully retrieved images locally.
  This is a connected/on-demand library, NOT an offline ZIP of 1,520 images.
  Internet is required for the initial retrieval of each airline mark.
- Airline names always remain visible, including offline and unsupported carriers.
- Logos are the trademarks of the respective airline owners. Catalog data and
  images: https://github.com/imgmongelli/airlines-logos-dataset
- Expanded flight card: all four detail cells are visible together, without
  internal scrolling. Very short screens may scroll the overall page.


v63: Live logo is anchored to the true horizontal center; language selector sits to the right alongside its unchanged menu button. Inbox gets one back-to-live arrow while the bottom Listen live control is removed. Both controls are localized and the logo still leads to Home.


v65 — AIRLINE IDENTITIES
14 bundled airline SVG assets; AA and AAL resolve locally. Remote logo.svg → icon.svg fallback for curated brands; all unavailable vectors remain a visible, non-brand code identity. Full inventory and limitations: AIRLINE_LOGOS.txt. No flight/search UI changes.


v69 WORDLY CREDIT FIX
--------------------
The Wordly-only credit is embedded into index.html as a high-resolution PNG data URI. It does not require /wordly-wordmark.png to resolve, so it remains visible when served from a nested path or opened directly. The local wordly-wordmark.png file is also retained as an optional asset.


v70 — Seamless logo return: fixed painted image geometry, GPU transform-only flight, gradual home shadow and 135ms matched-image handoff. Navigation and reduced-motion behavior preserved.
