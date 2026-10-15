# Jenny’s connector 19.0.4.2.0 and Android 0.8.0+15

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

Fresh instances: install **Jenny’s Rewards**; its data dependency installs automatically. Select the instance’s own website, loyalty/gift programs and POS. No demo contacts, products, balances or old-instance data are installed.

Use the same addon package on compatible Odoo 19 Community or Enterprise installations with the declared native dependencies. Cloudpepper/Odoo.sh database routing, website domains, SMTP and native POS/payment configuration remain the host’s responsibility. An HTTPS address alone cannot configure those services.

## Publisher-side app connection

In **Jenny’s Rewards → App connection**, select the website and enter its public HTTPS origin, without `/odoo`. The database is read from this instance. Download `jennys-connection.json` and save the account-link address. Enable the customer app and set its existing programs/POS. For multiple websites, Odoo must map the chosen host to the correct website.

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
- The Android build was attempted using the recovered test signing identity, but an environment proxy denied a required Flutter engine artifact download. No new APK has been delivered from this run. The new instance URL/database have not yet been supplied, so no connected deployment has been built.
- The Odoo test database is not available in this workspace. Actual install/upgrade/uninstall/reinstall, native website/POS/payment behaviour and physical-device tests are pending. The GitHub change remains a draft test branch.
