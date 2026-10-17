# Jenny’s connector 19.0.4.4.2 and Android 0.8.0+15

This is the next test release, built on member extras 19.0.4.1.0 / Android 0.7.1+14. It is not cleared for the live customer database until the lifecycle and business-flow tests below pass on a disposable Odoo 19 instance.

## What changed

- `spx_loyalty_mobile` owns the customer API, authentication extension, app actions, screens and scheduled jobs.
- `spx_loyalty_mobile_data` owns the persistent app tables and `spx_*` fields. It contains no business methods, HTTP controllers or scheduled jobs. It is an explicit installed dependency, not abandoned tables or a backup.
- Ordinary uninstall of **Jenny’s Rewards** keeps the data dependency installed. Reinstall uses the same app record IDs, birthday history, delivery history, preferences and website configuration.
- **Jenny’s Rewards → Uninstall options** defaults to **Keep app data for reinstall**. **Remove app settings and history** additionally requires an acknowledgement, then opens Odoo’s native uninstall impact preview for both Jenny’s modules.
- Either choice retains native contacts, portal users, products, sales/POS orders, payments, loyalty cards/points and gift-card balances. Full removal deletes app-only metadata and fields, including birthdays stored only in the app field and app consent metadata. Native sent-mail history remains, with obsolete app-record links detached.
- Uninstall invalidates temporary registration/recovery links and cancels pending app email and scheduled announcements. It does not cancel native sales, POS or payment activity. Reinstall does not resume previously queued app announcements.
- Customer app screens contain no server/database selector or test controls. Deployment is controlled by the publisher. A different configured origin or database clears the previous device login, pending signup and embedded website cookies. Ordinary updates to the same deployment preserve matching login state.

## Existing installations: upgrade before uninstalling

1. Deploy **both addon folders from this repository** to the test server. Use the updated `codex/member-extras-19.0.4` branch.
2. Refresh Odoo’s Apps list and **upgrade `spx_loyalty_mobile`**. Odoo installs its new data dependency automatically. Do not uninstall the old 19.0.4.1.0-or-earlier version first: that version does not have the retention design.
3. The data dependency’s pre-install hook changes schema ownership in place. It does not copy, recreate, renumber or export business records.
4. Verify the expected versions and record IDs before testing uninstall. Keep both addon folders available while the data dependency remains installed, including while the connector is uninstalled.

Fresh instances: install **Jenny’s Rewards**; its data dependency installs automatically. Open **Jenny’s Rewards → App setup**. No demo contacts, products, balances or old-instance data are installed.

## Birthday starter selected on first setup (19.0.4.4.2)

The first setup guide preselects birthday credit: 50 in the website currency, valid for 21 days, for verified app members. Administrators can change the amount or select Keep current / set up later before Apply. Opening the guide or installing/upgrading the module does not issue credit or activate a program. Apply creates the dedicated native birthday program and enables its hourly birthday check. Reopening setup, upgrading or reinstalling preserves existing birthday choices, including disabled rewards.

Birthday processing reads the existing customer contact: the configured stored Date field takes priority, with the signup Birthday field as fallback. Dates and contacts are not copied or replaced. Credits use native Odoo cards, balances and redemption, with one birthday award per customer/company/year. Purchased gift cards stay separate.

## Setup display correction (19.0.4.4.1)

The deployed guide revealed missing labels beside its policy and final-review checkboxes. Both now have explicit labels. Native program and outgoing-email actions also clear the website picker's `create=False` context so administrators can see the normal creation controls. Odoo access rights remain in force. Upgrade Jenny’s Rewards after pulling this correction; no customer data or reward rules change.

## Four-step setup (19.0.4.4.0)

Open **Jenny’s Rewards → App setup**. One website opens the guide directly; for multiple websites, choose the website and click **Guided setup**. The administrator follows four short screens with Back and Continue:

1. **Connect:** confirm the detected HTTPS address, app name, currency and app enablement. Existing choices are loaded; an ambiguous address or restaurant POS is not guessed.
2. **Benefits:** choose a loyalty template or an existing/custom native program. The loyalty starters offer points for a percentage discount or a fixed discount, with editable earning rate, threshold and value. Optional gift cards start at 50, 100 and 200 in the website currency. Birthday credit starts at 50 with 21-day validity and is preselected on first setup; existing installations keep their saved choices. These are starting values for the administrator to review, not approved customer rules. Gift-card options default to keeping current settings. Native **Create and Edit** remains available for custom programs and saves those native records immediately.
3. **Customers:** optionally enable signup with approved terms/privacy, sender and policy version. Select a restaurant POS for ordering. Signup may stay off until mail and policies are ready.
4. **Review:** see exactly what will be created, published, connected or left unchanged; acknowledge the choices and click **Apply setup**. Template programs/products are created only here. Applying setup creates no customer accounts, loyalty cards, balances, emails or orders. Newly enabled birthday scheduling can issue credits on its next normal scheduled run; the review shows its audience and amount.

After Apply, the setup checklist shows remaining email, menu and app checks. **Guided setup** reopens the guide; advanced settings and native program editing remain available. Configuration checks are not delivery or device tests. Publisher connection export remains on the saved checklist, outside the customer app.

New templates are company/website/currency scoped. Their POS availability is restricted to the selected restaurant POS; without a POS selected, new programs have POS use off. Native Sales and website checkout are enabled. Gift products are service products and use native company tax defaults; verify prices, taxes, payment configuration and checkout before selling. Gift templates require matching company/website currencies; use existing products/pricelists for other currency configurations. Birthday credit uses a separate gift-card program with no sale-trigger rules.

Repeat setup reuses the recorded template program and keeps edited native rules, product prices and publication state. Archived or incompatible retained programs cause a useful error instead of silently creating replacements. Concurrent/stale guides are rejected before creating business records. The template IDs live in namespaced configuration keys: connector uninstall retains them, explicit full data removal clears them while leaving native programs/products/cards/balances intact. After full app-data removal, select existing native programs to reconnect them.

Deploy both updated addon folders and **upgrade Jenny’s Rewards**, without uninstalling. The data-addon change only extends its existing removal hook; it adds no persistent schema or installation data. No Android rebuild is needed when the instance address stays the same.

Validation: Python/XML parsing, addon imports against official Odoo 19 and 15 database-free validation/security/escaping tests pass. Ten native wizard tests are supplied in `tests/test_setup_wizard.py`, alongside the earlier seven setup tests. The GitHub **Odoo setup checks** workflow installs the module and runs these tests on a disposable PostgreSQL database. Its result must be reviewed before treating the native install/ORM checks as passed. This does not replace real upgrade/uninstall/reinstall, email delivery, native POS/payment and device acceptance tests.

## Previous checklist update (19.0.4.3.0)

The overview now puts **Open setup checklist** first. With one available website, it opens that website directly; with several, the administrator chooses one. The screen groups connection/loyalty and member signup into two tabs and shows the next action for each feature.

1. Use **Use detected settings** to fill blank connection, program and restaurant-POS fields only when the choice is unambiguous. Existing selections are kept. With several websites, the global Odoo URL is never borrowed for another website. This action does not enable the app/signup, create programs or change earning/reward rules.
2. Review **Connection and loyalty**, choose the existing loyalty-card program and enable the app. **Manage loyalty programs** opens native Odoo with the correct program type and website/company defaults. The program picker filters by type, active state, company and website and disables quick creation, avoiding Odoo's unrelated default promotion type.
3. Complete **Member signup** with the new-member program, an authorized email sender, policy version, and approved terms/privacy text. Enable signup when these are complete. Missing-field errors now identify the specific next actions. Customer-facing failures remain generic.
4. Review email delivery and ordering. The checklist does not send email, authenticate to SMTP or submit orders. No configured mail-server record is reported as a warning rather than proof that host-provided mail cannot work. A configured server still requires a delivery test. Ordering needs published POS products and an open register; staff retain control of kitchen dispatch and payment.
5. The publisher downloads the matching **Publisher connection file** and tests the configured app. **Optional features** contains birthday credit and gift cards; these do not block basic loyalty setup.

An automatic promotion (even one named “Loyalty”) is not a loyalty-card program. Setup does not convert existing promotions, duplicate discounts, invent points/redemption rules, publish products, supply policy text or configure SMTP credentials. These are instance-specific business choices.

For existing installations, deploy this branch and upgrade **Jenny’s Rewards**; do not uninstall to receive the setup improvements. The passive data addon remains at 19.0.4.2.0. No Android rebuild is needed for these administrator-only setup changes when the instance address is unchanged.

Validation: the updated addon imports against official Odoo 19 source, all addon Python/XML parses, and seven database-free tests of the actual signup validation, public error boundary, HTML escaping and administrator guard pass. Seven additional native ORM regression tests are included in `spx_loyalty_mobile/tests/test_setup.py`; they require an isolated PostgreSQL-backed Odoo database and have not been executed here. Native view installation, the setup screen in a running registry, and the full lifecycle/device checks still require test-instance verification.

Use the same addon package on compatible Odoo 19 Community or Enterprise installations with the declared native dependencies. Cloudpepper/Odoo.sh database routing, website domains, SMTP and native POS/payment configuration remain the host’s responsibility. An HTTPS address alone cannot configure those services.

## Publisher-side app connection

In **Jenny’s Rewards → App setup → Publisher connection file**, enter the website's public HTTPS origin, without `/odoo`. The database is read from this instance. Download `jennys-connection.json` and save the account-link address. Return to App setup for the remaining checklist. For multiple websites, Odoo must map the chosen host to the correct website.

Keep the connection file outside Git. It contains address/database identifiers only; no administrator password or API key belongs in an APK.

```bash
python3 mobile/tools/build_connected_app.py --config /private/jennys-connection.json --flutter /path/to/flutter
```

The builder checks the connector, website-enabled state and database name before building. It rejects redirects. It performs no signup, login, payment or customer mutation. Supply the existing test certificate using the `JENNYS_TEST_KEYSTORE` environment variable; the key stays outside Git. An old APK keeps its built-in address until a matching update is installed. There is no customer-visible connection setup.

The recovered Android/iOS Flutter source is now under `mobile/`. Android 0.8.0+15 uses the existing application ID and test signing identity. iOS remains source only; macOS/Xcode signing and device validation are still required. Production signing and store release are separate from this test build.

## Required Odoo acceptance checks

Run on test data only. Record IDs, balances and counts before and after each phase; comparisons are test evidence, not a backup or migration process.

1. Upgrade the previous connector with existing member, birthday, gift-delivery, submission and inbox records. Check IDs, dates, website program links and native balances are identical.
2. Uninstall **connector only**, restart, and confirm normal website/shop, login, POS, payment and accounting remain usable. Confirm app endpoints, app menus, jobs and authentication extension are absent; the passive data module remains installed.
3. Reinstall the connector. Verify the same records and settings return, a birthday already awarded this year is not issued again, and a previously sent gift is not sent again.
4. Test explicit full removal separately. Confirm both Jenny’s modules are uninstalled; `spx_mobile_*` tables, relation tables, app fields, views, ACLs, actions and jobs are removed. Confirm native customers, accounts, orders, payments, cards, codes and balances remain unchanged. Reinstall should have fresh app settings without creating duplicate native business records.
5. Test sign-in/verification, existing contact reuse, loyalty reads, gift display, POS order submission, table/kitchen flow, payment and native points updates. Verify another account cannot read the member’s records.
6. Install an APK built for a different test instance. Confirm old sessions/signup receipts are not reused and no connection controls appear. Test the final customer deployment on the selected host before live release.

Automated Odoo cases in `spx_loyalty_mobile/tests/test_lifecycle.py` cover the removal defaults/permissions, connection file, and preservation hook. They do not replace the actual uninstall/reinstall process across registry reloads. Local structural checks confirm all original fields and business methods survived the split; they cannot prove live-instance compatibility.

## Validation recorded on October 15, 2026

- Five structural regression checks passed: exact preservation of original field declarations and business methods, passive retained schema, ownership manifest, and XML/ACL references. Python syntax, XML parsing and manifest paths passed.
- Flutter 3.47.4 analysis passed. The complete Flutter suite had 56 passing tests and two failures. The same two failures were reproduced on the unchanged recovered 0.7.1 source: outdated visual snapshots and an old sign-in button label in `test/app_test.dart`. No goldens were regenerated to hide these differences. The four new deployment-isolation tests passed.
- The initial Android build attempt was blocked by a required Flutter engine download. That environment issue was resolved; the connected build and delivery are recorded below.
- The Odoo test database is not available in this workspace. Actual install/upgrade/uninstall/reinstall, native website/POS/payment behaviour and physical-device tests are pending. The GitHub change remains a draft test branch.

## Connected Android build — October 17, 2026

- Built and delivered `Jennys-Android-0.8.0-arm64.apk` (**0.8.0+15**, ARM64, 20,411,600 bytes) using the publisher's supplied connection file for the new Cloudpepper test instance. Connection files and signing keys remain outside Git.
- The read-only connector check passed: API version 1, customer app enabled, and database name matched. The new HTTPS origin and database were also verified inside the compiled APK.
- APK signature and 16 KiB ZIP alignment checks passed. Application ID remains `net.spxcorp.jennys_rewards`; the signing certificate matches the previous test APK, allowing an in-place update.
- APK SHA-256: `f07e95d8c637b2e91fd2e1fe3757f9cbb7d106c5bc3ab91d73c8464e723b64e9`.
- The new instance's signup configuration endpoint still reports registration disabled. Complete the signup configuration before testing new account creation. This is separate from the enabled app connection.
- Physical-device flows and actual Odoo upgrade/uninstall/reinstall acceptance checks remain pending. This is a test APK; no production deployment or customer mutations were performed.
