# Jenny’s member extras — connector 19.0.4.0.0

Deploy and **upgrade this existing module**, do not uninstall. Restart after the upgrade completes. This release adds fields and models, so restarting alone is insufficient.

Read `MEMBER_EXTRAS_TEST.md` included in this module for birthday credit, native gift-card programs/products, announcements and acceptance testing. No POS assets or native POS model overrides are added. Payment, balance calculation and redemption remain native.

Firebase is deferred; announcements currently reach the app inbox only. Odoo database integration tests are included but must be run on a disposable Odoo 19 instance before deployment to production.

---

Historical release notes follow.

## Verified registration update — 19.0.3.0.0

Upgrade the installed module before testing Android 0.5.0+9. Configure the signup program, sender, HTTPS account origin and policies in the website Customer App tab. See the included `SIGNUP_SETUP.md` for setup and validation limits.

# Jenny’s Rewards — Odoo 19.0.2.0.0

Companion for Jenny’s Flutter app 0.4.0+. Keeps native customer cards, loyalty history and inbox behavior; creates new unpaid native POS orders from authenticated customer baskets.

Select the existing restaurant POS in **Jenny’s Rewards → Settings → website → Customer App → Dine-in Point of Sale** and open a POS session. The app menu uses existing published products allowed in that POS. Staff assign/merge tables, send orders to kitchen preparation, apply rewards and settle bills with normal POS controls.

No POS assets, views or native POS model overrides are included. Internal basket/retry receipts do not replace native orders, stock, payment or loyalty records. Simple products are supported; configurable/weighted/tracked items are handled by staff.

Deploy the module folder in the existing custom addons repository, restart Odoo and **Upgrade** the module. Do not uninstall. Dependencies: website_sale_loyalty, pos_loyalty, pos_restaurant, portal, mail. The v1 app cart routes now require the newer APK. The native website store is unchanged.

Run tests only on a disposable database:

```sh
odoo-bin -d jennys_mobile_test -u spx_loyalty_mobile --test-enable --test-tags /spx_loyalty_mobile --stop-after-init
```

Full setup, deployment, limits and acceptance tests are in the source package’s `docs/DINE_IN_UPDATE.md`. Enterprise kitchen/checkout behavior and physical scanning require target-instance testing before production use.
