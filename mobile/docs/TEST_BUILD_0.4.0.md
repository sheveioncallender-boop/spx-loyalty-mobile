# Jenny’s Android test build

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
