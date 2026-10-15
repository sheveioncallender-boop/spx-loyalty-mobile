# Validation — app 0.4.0+7 / connector 19.0.2.0.0

The new controller guard tests pass with isolated boundaries (13 total including validation/image/legacy checks). Four new Flutter checks cover successful single-flight submission without points changes, explicit retry with the same key/quote, changed-price review, and rejection of a late stale basket key. Native ORM/HTTP tests are included for unpaid order creation, replay after deletion/merging, zero totals, changed prices, unpublished products, cross-customer isolation and retired legacy endpoints.

A running Odoo/PostgreSQL service is unavailable locally. The included ORM/HTTP tests have not been executed. The local test evidence must not be described as a real POS/kitchen/payment test. No server deployment was performed. The acceptance sequence in `DINE_IN_UPDATE.md` is required before production use.

## Final local verification — 0.4.0+7

- Dart static analysis: no issues found.
- Flutter tests: **27 passed**, including the four new ordering tests and existing card/motion/activity/refresh/layout/API checks.
- Python validation/controller-boundary tests: **13 passed**. These execute isolated boundary doubles, not the Odoo ORM.
- Addon Python/XML parsing and manifest file references: valid.
- APK release build succeeded; archive integrity and Android v2 signature verified.
- Package `net.spxcorp.jennys_rewards`; version `0.4.0` / code `7`; ARM64; minimum API 24; target API 36.
- APK bytes: 20190432; SHA-256: `e0fa5e1463b0b067c943f53e2a729c0004f0d8d1631fd5c2a4c8120eb1de8e96`.
- Test certificate SHA-256: `0ee55af36b3c0a84442078f7dc58a3e33b660b69a06a8a72e520548c1af33d8f`. Same signer as 0.3.2 and 0.3.3.
- Compiled test origin/database and `/spx/mobile/v2/dine-in/submit` verified; the old `/shop/checkout` path is absent from the compiled app library.
- Native Odoo ORM/HTTP tests, Cloudpepper installation, real kitchen dispatch, table merge, checkout and points posting **not executed here**. Complete the provided test-instance sequence before using live data.



---

# Verification record — 13 September 2026

## Recent activity update: Android 0.3.3+6

- Added the Recent activity menu under You and My card, with a native balance
  summary, card issue date, earned/used filters, chronological month groups,
  animated expandable descriptions, and automatic refresh while open.
- Static analysis: no issues. All 23 Flutter tests pass. New checks cover both
  earned and used values on one record, negative adjustments, card filtering,
  changes to open details/balance, empty/removed-card states at 1.5x text size,
  and conversion of native UTC timestamps to device-local time.
- Actual Flutter screen renders were visually inspected with bundled fonts.
  Two existing card goldens were intentionally updated for the new menu row;
  the other existing screen goldens pass unchanged.
- The companion addon remains 19.0.1.3.1. No backend routes, privileges,
  business data or native points calculations were changed in this release.
- Live-instance history, earning/redemption and physical device behavior still
  need acceptance testing. New automated tests use a simulated API.


## Historical APK identity — 0.3.3+6

- File: `Jennys-Android-0.3-arm64.apk`.
- Package: `net.spxcorp.jennys_rewards`; version name `0.3.3`, version code `6`.
- ARM64; minimum API 24, target API 36; 20190432 bytes.
- SHA-256: `750b39832d0e5f36424bfe806f1090988facc4868f3c7a7c83f5c3213ad589a1`.
- Android v2 signature and ZIP integrity verified; signer SHA-256:
  `0ee55af36b3c0a84442078f7dc58a3e33b660b69a06a8a72e520548c1af33d8f`.
- Certificate matches 0.3.2+5, allowing an in-place Android update.
- Test origin/database and new activity-screen strings were verified in the
  compiled application library. No live deployment was performed.

## Earlier automatic refresh update: 0.3.2+5 / connector 19.0.1.3.1

- Passed: Dart static analysis with no issues and all 20 Flutter tests on
  Flutter 3.47.4 / Dart 3.13.3. The existing visual goldens also pass unchanged.
- Seven new widget tests cover automatic product edits while retaining search
  and scroll position; card balances after network recovery and app resume;
  preventing old reads from replacing a successful cart write; retaining loaded
  catalogue pages; disabling an unpublished product in its open sheet; keeping
  the selected card consistent when memberships change; and live inbox/order-history updates. The API boundary is simulated in these
  tests; they are not HTTP or Odoo integration tests.
- Six controller guard checks pass, including stable image URLs that change
  when a product or its template is updated. These execute the actual controller
  methods with boundary doubles, without an Odoo ORM/database.
- User-confirmed on the preceding build: sign-in, native card assignment with
  zero points, and publication of a product visible after manual refresh.
- Still requires the test device/instance: new polling behavior over real HTTP,
  image-cache refresh after the addon upgrade, POS earning/redemption, physical
  barcode scanning, checkout/payment, and installed custom-module compatibility.

## Earlier APK identity — 0.3.2+5

- File: `Jennys-Android-0.3-arm64.apk`
- Package: `net.spxcorp.jennys_rewards`; version `0.3.2`, version code `5`.
- Minimum Android: 7.0 / API 24; target API 36; architecture `arm64-v8a`.
- Size: 20190120 bytes.
- SHA-256: `2fc4df2a2514c52a0955be7b87bfd5cb4bbab11033f3c925e5b54aa6f66bffa4`.
- APK archive integrity and Android v2 signature verified using SDK tools.
- Certificate SHA-256: `0ee55af36b3c0a84442078f7dc58a3e33b660b69a06a8a72e520548c1af33d8f`.
- Test origin `https://jennys.spxcorp.site` and database `jennys.spxcorp.site`
  were verified in the compiled application library.
- This uses a new test-signing certificate. Remove the earlier Android test
  app, install this build and sign in again. Server-side Odoo records remain
  intact. Upgrade the Odoo addon normally; do not uninstall it.
- Native Odoo/physical-device verification remains outstanding for this new
  automatic-refresh build; the test results above use a simulated API.

## Earlier verification record — 8 September 2026

## Completed locally

- Connected build **0.3.1+4**: compiled with the supplied origin `https://jennys.spxcorp.site` and database `jennys.spxcorp.site`. Both values were verified in the compiled application library. The APK has version code 4 and the same test-signing certificate as the prior APK, allowing an in-place test update.
- Public endpoint check: `/web/login` returned HTTP 200 over verified HTTPS. The installed `/spx/mobile/v1/bootstrap` returned JSON-RPC `odoo.http.SessionExpiredException` for an unauthenticated request, as expected. This establishes endpoint reachability, not successful customer authentication or loyalty/ordering behavior.
- Branding release **19.0.1.3.0**: existing logo and licensed fonts are packaged, the launcher uses a real PNG icon, and native navigation actions are declared. Python/XML parsing, manifest asset paths, menu/action references and JavaScript syntax were checked. The preview browser blocks local pages/files, so the new Owl overview has not been visually or interactively verified in a browser or a running Odoo session. Verify the upgrade and all five overview shortcuts on the test instance.

- Compatibility follow-up: connector `19.0.1.2.0` adds native product/website availability checks and validates newly created cart ownership. Four input-validation and five controller-guard tests pass. The guard tests use boundary doubles and do not exercise the ORM. Three HTTP/ORM integration tests were added but have not run. See `COMPATIBILITY.md` for the pinned Odoo source revision and exact review limits.

- Android APK built successfully in release mode with test signing. The APK signature and archive integrity verify. The package contains only ARM64 native libraries, with a matching Flutter engine/application.
- Dart static analysis: no issues.

- Thirteen Flutter widget/API tests pass, including a 360 × 800 Android layout, navigation, cart add/remove behavior, the non-QR membership card, HTTPS origin/redirect protection and no automatic retry of an uncertain mutation. Added checks cover exact card-code bytes, enlarged scan view, refresh on closing, manual-entry fallback, email/password-only sign-in and customer-friendly errors. Additional motion tests cover the intermediate 3D rotation, stable card layout, rapid reversal and immediate reduced-motion display.
- Welcome, home, menu, rewards, card, scan, enlarged scan and sign-in screens were rendered using the actual Flutter widgets and bundled fonts. The PNGs were visually inspected. They are screen renders, not speculative design mockups.
- Independent ZXing-C++ decoding of the actual Flutter PNG renders recovered the exact Code 128 payload from the card’s reverse, normal scan view, enlarged view and native-code fixture, including spaces, hyphens and case. This validates rendered barcode content, not physical scanner compatibility.
- Four Python request-validation tests pass for record identifiers, finite/bounded quantities, removal quantities and mutation keys.
- Addon Python syntax, XML structure and manifest file references are valid.
- Odoo method names, route types and relevant model fields were checked against the local Odoo 19 source: native session authentication, `request.cart`, website pricing, cart updates and native loyalty reward application. The existing POS coupon handler identifies the loyalty card’s partner through `get_loyalty_card_partner_by_code` and selects that customer; the addon uses this unmodified native flow. An additional database test for exact mobile/POS lookup and no points change on repeated lookups is included but has not been executed without Odoo/PostgreSQL.

## Requires the target environment

The user confirmed installation of the earlier addon on the Odoo 19 Enterprise test database, and its public customer endpoint responds. The branding upgrade to `19.0.1.3.0` has not been deployed by this workflow. Included ORM/security tests still require a real Odoo/PostgreSQL test environment and have not been executed here.

A live customer sign-in, card scan, eligible sale, points posting and refresh must still be tested on Jenny’s target POS and scanner. The supplied APK is now configured for the user’s test instance; connection identifiers remain developer build settings, not customer input fields.

Physical Android testing is also still needed for secure storage, the native WebView cookie bridge, payment-provider navigation, network interruption, session expiry, barcode scanning and temporary brightness/screen-awake restoration. A successful APK build by itself does not prove those device integrations.

Firebase push is not configured. Native Odoo email delivery depends on the test server's outgoing mail setup and customer consent. Store publishing, production signing and iOS validation have not been performed.

## APK identity

- File: `Jennys-Android-0.3-arm64.apk`
- Package: `net.spxcorp.jennys_rewards`
- Version: `0.3.1` / version code `4`
- Minimum Android: 7.0 / API 24
- Target Android API: 36
- Architecture: `arm64-v8a`
- Size: 20190120 bytes
- SHA-256: `8d3620ee6b74527166cef7fa24e966cdc999e0560abc5b3a65b784d7201f4c3c`
