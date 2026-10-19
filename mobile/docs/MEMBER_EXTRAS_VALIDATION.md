# Birthday management and automatic cards — 23 September 2026

Android 0.7.1+14; connector 19.0.4.1.0.

- Flutter static analysis: no issues.
- 24 distinct focused widget tests passed across member extras, account access, dine-in and automatic refresh. The added automatic-card test initially needed to scroll to its lazy-built description; after correcting that test, all three member-extras tests passed. A separate rendered capture passed and was visually inspected.
- Four isolated Python validation tests passed. Python AST/compilation, duplicate-method checks, XML parsing, manifest file references and ACL CSV checks passed. Date-boundary checks include leap day and year rollover.
- Release APK ZIP integrity and Android signature verification passed.
- Package net.spxcorp.jennys_rewards; version 0.7.1 / 14; ARM64; minimum API 24; target API 36.
- Same test certificate SHA-256: 0ee55af36b3c0a84442078f7dc58a3e33b660b69a06a8a72e520548c1af33d8f.
- APK SHA-256: f9264dcf1c46229178a24251ad6f4d861f4567bc58e128d2ff88d18042fae716; bytes: 20414576.
- Connector branch: codex/member-extras-19.0.4; commit 436c265e587c9980073daa659ea51b85e09a3256. Main was not changed.
- PR: https://github.com/sheveioncallender-boop/spx-loyalty-mobile/pull/1

Not executed here: Odoo/PostgreSQL ORM integration tests, Cloudpepper upgrade, native POS/payment redemption, SMTP, physical Android testing or iOS build. Run the supplied Odoo tests on a disposable Odoo 19 database. No live instance or customer messages were changed. Firebase/background push remains deferred.
