# Accessibility checks

The interface offers light, dark and system appearance settings. Preferences
stay in browser storage; if storage is blocked, the control still works for the
current page. The system option follows operating-system changes. A small
initialisation script applies the saved appearance before the page paints.

Keyboard support includes a skip link, visible focus, native form controls and
dialogs, Escape to close source evidence, focus restoration, and a keyboard
scrollable comic. Source tabs support Arrow keys, Home and End. Step changes
focus the new heading. Reduced-motion and forced
colour preferences are respected. Audio sources have editable transcripts;
video practice uses reviewed captions or pasted transcripts. Microphone use is
optional and typed replies remain available.

## Repeatable browser audit

`scripts/test_accessibility_browser.mjs` uses mocked API responses; it never
records audio or calls an AI provider. Install Playwright and axe-core 4.14.0 in
your development test environment, start the app on port 3000, then run:

```powershell
$env:CHROME_PATH='C:\Program Files\Google\Chrome\Application\chrome.exe'
# Optional when axe-core is outside node_modules:
$env:AXE_SCRIPT_PATH='.runtime/browser/axe.min.js'
node scripts/test_accessibility_browser.mjs
```

The tool writes `.runtime/accessibility-audit.json` and screenshots. Set
`A11Y_TEST_URL=https://the-rehearsal-lab.vercel.app` to check the published UI.
The URL guard permits only localhost:3000 and that exact production origin.

The November 11 release was checked with Chrome and axe-core against WCAG A/AA
rules available in the tool, plus its best-practice rules. All 26 scans passed:
setup, library, audio sample, plan, chat with voice controls expanded, source
dialog, review, video import, audio upload, OCR dialog, and mobile setup in
English, German and Spanish, in both themes. Each view was also checked for
horizontal page overflow at 320 CSS pixels with increased text spacing.
The audit checks theme persistence, live system-theme changes, keyboard access
to the skip link, and Escape/focus restoration for the source dialog.

These checks are evidence of tested behaviour, not a WCAG conformance claim.
Screen-reader testing with NVDA/VoiceOver, additional browsers, actual device
and microphone testing, and third-party YouTube/PDF player accessibility still
need manual verification. Generated source text and AI responses also require
review; automated scans cannot judge their readability or accuracy.
