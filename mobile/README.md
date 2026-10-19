# Jenny’s 0.8.0+15 — publisher-controlled connection

The customer app has no connection selector or test controls. Build it for the approved Odoo instance using `tools/build_connected_app.py` and the connection file from the connector’s administrator screen. A changed origin/database resets old device sessions and signup receipts; same-instance updates preserve matching sign-in state.

Use connector **19.0.4.2.0**, including its passive data dependency. See `../INSTALL_AND_RETENTION.md` for upgrade order, uninstall options and test gates. The historical notes below describe previous versions.

---

# Jenny’s — birthday management and automatic gift cards 0.7.1+14

Upgrade connector **19.0.4.1.0** before testing this APK. Use feature branch **codex/member-extras-19.0.4**, not main, in the [existing repository](https://github.com/sheveioncallender-boop/spx-loyalty-mobile/pull/1). Connector commit: `436c265e587c9980073daa659ea51b85e09a3256`. This app archive omits the Git-backed Odoo module. See [setup and test steps](docs/MEMBER_EXTRAS_TEST.md).

Adds Customer Birthdays, Birthday Settings, manual issue controls and links to Odoo’s native balance/expiry controls. Existing contact birthday fields can be selected without copying data. Administrators can see nonmember birthdays and choose the automatic audience. The app displays assigned native gift cards automatically, with no code-entry step. Odoo still generates codes and controls payment, balances and redemption.

Firebase/background push remains deferred. This is an Android test build; Cloudpepper module-upgrade and native transaction checks still need to run on your test instance. Ordering, POS, table assignment and kitchen behavior are unchanged.

---

# Jenny’s — 0.6.0+12, iOS test preparation

The iOS project now includes Jenny’s app icon and launch branding, saved-login Keychain configuration, a native account-page cookie bridge, and temporary scan-screen brightness support. It shares the existing Android design, onboarding, account and ordering code. The deployment target is iOS 15.0, intended for iPhone X and newer supported iPhones; physical-device compatibility still needs testing.

Start with **[iPhone test setup](docs/IOS_TEST_SETUP.md)**. This package contains source, not a signed IPA. Building and installing on an iPhone requires macOS/Xcode and Apple code signing. No Apple team or signing credentials are included. Forty focused Flutter checks passed locally, including three iPhone-sized layouts; native Swift tests are supplied but have not run in Xcode.

The existing Android APK and all Odoo connector files remain unchanged. No Odoo module upgrade is needed for this iOS preparation.

## Android test update 0.6.0+12

This app update adds a four-page first-use introduction to the loyalty card, rewards, dine-in ordering and recent activity. It uses Jenny’s two newly supplied evening photographs on the introduction, welcome, home and restaurant sections. The launch screen has a matching navy background; the introduction supports swiping, Skip, sign-in and account creation, reduced motion and larger text.

Install the new ARM64 APK over the existing 0.5.2 test app. Signed-in customers continue to Home. Replay the introduction through **You → Discover the app**. A new installation shows the introduction before account entry; skipping or completing it is remembered on that installation.

The connector remains **19.0.3.0.4**, included unchanged in this source archive. **No Odoo upgrade is needed for 0.6.0.** Account verification, duplicate-email checks, password recovery, POS submission and loyalty rules keep their existing implementation. This APK still connects to the approved Jenny’s test instance and uses the existing test signing certificate.

See `docs/FIRST_LAUNCH.md` for this update and its test steps, and `docs/SIGNUP_SETUP.md` for the working account setup. Android has been built and checked locally; physical-device and iOS release testing remain separate. The notes below document the earlier dine-in release.

## Earlier dine-in update: 0.4.1+8

The approved Flutter design, photography, Manrope fonts, card flip/barcode, points activity and automatic refresh are retained. This update replaces app web checkout with dine-in submission to Odoo 19’s native POS.

## What changes

- A submitted basket creates a new **unpaid native POS order**, under the signed-in customer’s exact contact.
- Staff find the order by its customer name/reference, assign a table or use normal Transfer/Merge, then send it to preparation and collect payment after the meal.
- Each additional submitted basket is another native order. Staff merge it as appropriate. The connector does not guess a table or append to a bill someone is editing.
- Existing Odoo products supply the menu: published on this website, active, saleable and available under the selected POS’s native product/category rules. No replacement product database is created.
- Native POS pricelists, customer fiscal positions, preset priorities and tax routines price the basket. A changed quote requires review before submission.
- Loyalty remains native. The app reads balances/history; staff apply eligible rewards in POS. Submitting or scanning does not award points.
- An immutable, customer-scoped receipt prevents duplicate submissions, including after native order merging deletes a source order.
- Customer screens contain no database/server selector and no payment, delivery or table-selection flow.

The addon contains **no POS JavaScript, no POS view changes and no overrides of pos.order, pos.order.line, pos.config or pos.session**. Its internal basket/receipt records are connector metadata, not separate business orders or a loyalty ledger.

## Install and test

Upgrade `spx_loyalty_mobile` to **19.0.2.0.1** first, then install Android **0.4.1+8** for the clearer order status display. In **Jenny’s Rewards → Settings → your website → Customer App**, choose **Dine-in Point of Sale**, save, and open a session at that POS. See `docs/DINE_IN_UPDATE.md` for the complete test sequence.

Connector **19.0.2.0.1** fixes the blank POS screen when selecting an app order. Internal notes now use Odoo 19's native JSON tag format. Its upgrade migration converts legacy plain-text notes only on orders linked to this connector's submission receipts, preserving their text and leaving valid notes unchanged. Close POS browser tabs during the module upgrade, then reopen POS and check the existing order. The server repair also works with app 0.4.0+7. No POS frontend customization is needed.

Android **0.4.1+8** shows clear **Order received**, **Paid** and **Cancelled** badges in **You → Your orders**, alongside the bill amount, reference and date. States follow the existing native POS records, refreshing while the page is open and on app resume. Received means an unpaid order has arrived, not that kitchen preparation has started. Jenny’s existing app design and loyalty flow are retained.

The packaged APK connects to the supplied test origin `https://jennys.spxcorp.site`, database `jennys.spxcorp.site`. It uses the same test signing certificate as app 0.3.2 and 0.3.3, allowing an in-place update. The APK is ARM64, minimum Android 7.0. It is not a Google Play release. The separate signing archive is not included in source.

**Try the preview** uses sample data only. The new sample submission demonstrates the flow without sending anything to Odoo or changing real points.

## Current bounds

Simple products can be submitted. Configurable items, combos, weighed products and lot/serial-tracked items ask the customer to order with staff; they never redirect to web checkout. Scheduled, return and address-required presets are not accepted by this dine-in adapter. Use an existing appropriate dine-in preset/default on the test POS.

Kitchen dispatch, table merging, payment, discounts and point posting need an end-to-end check in Jenny’s actual Odoo 19 Enterprise test instance. Local tests do not prove Enterprise behavior, installed third-party addon compatibility or hardware scanning. Do not move this build to the live database until those checks pass.

Email/inbox, card assignment and native loyalty setup retain their previous behavior. Firebase background push, the final account lifecycle/privacy work, production release signing/store listing and the iOS release remain outside this update. iOS source is included; no iOS binary was built.

See `docs/ODOO_SETUP.md`, `docs/BUILD.md`, `docs/VALIDATION.md`, `docs/COMPATIBILITY.md` and `docs/TEST_SIGNING.md`.
