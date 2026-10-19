# Jenny’s Android test build — 0.4.1+8

- Connector **19.0.2.0.1** corrects internal note serialization and includes an upgrade repair for app-linked orders with legacy plain-text notes.
- Android **0.4.1+8** adds native Order received / Paid / Cancelled statuses to You → Your orders.
- **13 targeted Flutter tests passed**: 5 dine-in and 8 automatic-refresh tests. These cover order-state refresh, native-price response changes, loyalty discount descriptions and required points, points balance, offline/resume and stale-read protection.
- **15 Python boundary tests passed**. Native OrderDisplay/TagsList note-consumer test also passed for corrected submissions and migrated notes, and reproduced the old failure.
- Dart analysis, Python/XML parsing and manifest references passed.
- Actual Flutter order-status screen rendered at 393 × 900 and visually checked.
- Release APK built; ZIP integrity, package/version and Android v2 signature verified. Same test signer as app 0.4.0+7.
- Target test origin/database and status messages verified in the compiled app.
- Package: net.spxcorp.jennys_rewards; ARM64; minimum Android API 24; target API 36.
- Bytes: 20190596; SHA-256: `34195b4b69d986c5f2498e03a35a170a0717fd069e52cde0d99980dec1bb7b02`.
- Certificate SHA-256: `0ee55af36b3c0a84442078f7dc58a3e33b660b69a06a8a72e520548c1af33d8f`.
- This update was not deployed by the assistant. Native migration on PostgreSQL and the full Enterprise POS/table/kitchen/payment/points workflow still need the user's test-instance acceptance check.
