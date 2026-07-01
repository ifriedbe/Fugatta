# Tab Logbook — Safari Extension

Tracks every browser tab you open: title, URL, page description, and the
exact time it was opened and closed. Export the whole log to a nicely
formatted `.xlsx` file (colored header, hyperlinked URLs, date columns,
alternating row shading, autofilter) with one click from the toolbar popup.

## How it works

- `background.js` (a Manifest V3 service worker) listens for `tabs.onCreated`
  / `tabs.onUpdated` / `tabs.onRemoved` and keeps a log of every tab in
  `chrome.storage.local` (open tabs get `closedAt: null`, closed tabs get a
  timestamp).
- `content.js` runs on every page, reads `<meta name="description">` (or the
  `og:description` fallback), and reports it back so each row gets a real
  description instead of being blank.
- `popup.html` / `popup.js` show a live summary (open / closed / total) and a
  preview table, and the **Export to Excel** button builds the workbook with
  [ExcelJS](https://github.com/exceljs/exceljs) (bundled locally in
  `Resources/vendor/exceljs.min.js` — no network calls, works offline) and
  downloads it as `tab-log-YYYY-MM-DD.xlsx`.
- **Clear Log** wipes the stored history if you want to start fresh.

This was built and tested (tab tracking, description scraping, popup
rendering, and the actual `.xlsx` export/download) against the Chromium
WebExtensions API, which Safari Web Extensions implement — so the extension
code itself is Safari-ready as-is. Turning it into an installable Safari
extension just requires wrapping it with Xcode (Apple doesn't allow building
`.app`/App Store extension bundles outside of macOS/Xcode).

## Package it for Safari (requires a Mac with Xcode)

1. Copy the `safari-extension/Resources` folder to your Mac.
2. Open Terminal and run:
   ```
   xcrun safari-web-extension-converter /path/to/Resources
   ```
   This generates a ready-to-build Xcode project that wraps the extension in
   a native Safari App Extension container.
3. Open the generated `.xcodeproj` in Xcode, select your Team under
   *Signing & Capabilities* for both targets (the app and the extension),
   and hit **Run**. This installs the container app; the extension will
   appear (disabled by default) in the shortcut app it creates.
4. Enable it: **Safari → Settings → Extensions → Tab Logbook** (check the
   box), and grant it permission to run on the websites you want tracked.
   For development, also enable **Safari → Settings → Advanced → Show
   Develop menu**, then **Develop → Allow Unsigned Extensions** if you're
   running an unsigned build.
5. Click the Tab Logbook icon in the toolbar any time to see the live count
   and hit **Export to Excel**.

To distribute it via the Mac App Store instead of running it locally, archive
the generated Xcode project and submit it through App Store Connect as you
would any other Safari extension.

## Notes / limitations

- Tab "opened" time is recorded from when the extension first sees the tab —
  tabs open before the extension was installed are logged retroactively with
  the install time as their open time.
- If Safari or your Mac restarts while tabs are open, those tabs will still
  show correctly since the log lives in persistent extension storage, not
  memory.
- The description column depends on the site providing a meta description
  tag; not all pages have one, in which case it's left blank.
