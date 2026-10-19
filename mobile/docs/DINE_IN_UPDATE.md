# Jenny’s dine-in update — test instance guide

App **0.4.1+8** · Connector **19.0.2.0.1** · Odoo **19 Enterprise**

## Upgrade on Cloudpepper

### POS order-opening fix — connector 19.0.2.0.1

The previous connector wrote `internal_note` as plain text. Odoo 19's native order display parses it as a JSON list of note tags, causing a white screen when an app order was selected. This release writes the expected `[{"text": "…", "colorIndex": 0}]` format. It also includes a post-upgrade migration that converts malformed plain-text notes on orders referenced by app submission receipts. The existing note text is retained; valid JSON notes and unrelated POS orders are left alone. No order items, totals, customer links, tables, preparation state, payments or points are changed by the repair.

1. Close the POS browser tabs during this upgrade; keep the POS session open in Odoo.
2. Deploy this updated module folder through the existing Cloudpepper process.
3. In Odoo **Apps**, find **Jenny’s Rewards** (`spx_loyalty_mobile`) and choose **Upgrade**. The connector version is **19.0.2.0.1**. Upload/restart alone does not run the repair.
4. Reopen POS, refresh with **Ctrl+Shift+R**, then select the existing app order in **Orders**. Do not submit the same basket again to test this repair.
5. Confirm its items and total, then continue with the normal staff table/preparation/payment flow.

The server fix also works with Android **0.4.0+7**. Install the included **0.4.1+8** APK for the order-status display below. If the existing order still opens a blank screen, capture the first red browser Console error after selecting it; do not clear POS site storage or delete the order.

### Customer order status — Android 0.4.1+8

Open **You → Your orders**. The page reads the customer's native POS records for the selected restaurant and updates on the existing foreground refresh cycle (about 15 seconds while connected), or when returning to the app.

| App status | Native POS state | Meaning |
|---|---|---|
| Order received | draft | The order has reached POS and the bill is still open. Pay with staff after the meal. |
| Paid | paid or done | POS payment is completed; done is Odoo's posted state. |
| Cancelled | cancel | Odoo has marked the order cancelled. |

The app does not infer Preparing, Ready or Served from an unpaid bill. Table assignment, preparation and payment remain native staff actions. History follows existing customer-linked bills: after a native merge, the remaining bill must still have the correct customer selected. Deleted source orders are not displayed as separate current bills and do not expose another guest's bill through an old receipt.

Test once with a small order: check Order received, take payment through POS, then confirm Paid after the app refreshes. Use a separate unpaid test order to check native cancellation and the Cancelled badge.

### Prices, discounts and loyalty changes

The same refresh cycle reads product/pricelist prices and basket totals, loyalty reward descriptions and required points, card balances and recent activity. Reopening/resuming the app also requests fresh data. POS pricing and tax routines recalculate the basket server-side and a changed submission quote must be reviewed before an order is created. A displayed reward is an offer subject to native eligibility; staff apply it during POS checkout. The app does not award points or apply loyalty discounts independently. Odoo controls the saved reward description shown in the app as well as its point requirement.

### Initial dine-in setup

1. Back up the test database. Update the existing custom-addon repository with the folder from `spx_loyalty_mobile.zip`. The repository/addons path must contain `spx_loyalty_mobile/__manifest__.py` directly under the module folder.
2. Deploy/restart that test instance through your existing Cloudpepper process. In Odoo Apps, upgrade **Jenny’s Rewards** (`spx_loyalty_mobile`). Do not uninstall the module. The new native dependency is `pos_restaurant`; no Enterprise files are redistributed in the ZIP.
3. Open **Jenny’s Rewards → Settings**, select the website for `jennys.spxcorp.site`, then **Customer App**. Keep your existing enable/brand/loyalty settings and select the restaurant in **Dine-in Point of Sale**. Save.
4. Open that POS session. Keep its usual floor/tables, payment methods, preparation display, product categories, pricelist and loyalty settings. Reload the POS after the addon upgrade. The app does not configure these for you.
5. Install the new APK over 0.3.2/0.3.3/0.4.0. Sign in as the existing test customer. The barcode/card and points should remain the same. An app still on 0.3.1 needs a fresh installation because of the old signing-certificate change.

Upgrade both pieces together. Old app basket endpoints now return an update message so an older APK cannot place a new eCommerce basket through this connector. Existing Odoo website shopping is not modified. Any older website baskets remain native records; they are not converted to POS bills automatically.

## Menu and pricing

Use products already in Odoo. An item appears when it is active, saleable, published for this website and included in the selected POS’s native available-product/category domain. Set **Available in POS** on a test product if needed. POS categories and sequence control the app menu. No product import, duplication or hardcoded live price is required.

The app shows tax-inclusive item estimates from native POS pricing. It uses allowed customer pricelists/fiscal positions and native default preset overrides. Order totals and taxes are calculated with native POS/account tax methods. Staff may change the bill or apply eligible rewards during normal service/checkout.

This update submits simple items only. Products needing a configurator, combos, scale input or lot/serial selection remain visible with **Order with our team**. The app does not send a guessed configuration or open an eCommerce checkout. If your default preset is a scheduled, return or address-required mode, use a suitable existing dine-in configuration for this test; the app does not change native settings.

## Service flow

1. The signed-in customer adds items and taps **Place order**. There is no customer table or payment selection.
2. The connector creates a normal **draft/unpaid `pos.order`**, with the customer’s exact partner/contact, a native order reference, no payment lines and no table. Its native order name is **App · Customer name**.
3. Staff open it from the POS order list, confirm the guest and use the existing **Transfer/Merge** action to assign or combine it with the table’s bill.
4. Staff use the normal POS **Order / Send** preparation action. The configured Enterprise preparation display/printers handle it. The app’s **Order received** message means accepted into POS, not that cooking has started.
5. After the meal, staff check the bill’s customer, apply any eligible native rewards and take payment normally. Odoo calculates/posts points under the configured program; the app reads the resulting balance/history.
6. Any additional basket submitted from the app creates another unpaid order for staff to merge. This avoids automatic edits to a live staff bill and requires no custom POS controls.

The login already identifies an app order. Scanning the card is optional for that order; normal customer search and loyalty-code scanning remain available. Scanning alone is never an earn event. When combining orders from multiple guests, confirm the intended customer/loyalty holder on the resulting bill: native POS rewards follow the selected bill/customer. The app does not split or reassign loyalty points.

## Test before using the live database

- Submit one simple item. Confirm exactly one unpaid order, correct customer, product, quantity, tax and total; no table/payment/points award yet.
- Assign the table using existing controls, send to kitchen, and confirm one correctly routed preparation ticket with the right items.
- Add a second basket and merge it normally. Confirm quantities, totals, customer and kitchen changes remain correct, without duplicate preparation.
- Settle the bill normally. Compare native points/reward usage and history with the app after its foreground refresh. Test an eligible redemption and a normal refund/cancellation.
- Change a price after the basket was viewed, before sending. The customer must review the fresh total rather than silently submitting a stale quote. Unpublish/remove an item from the POS menu and confirm it cannot be submitted.
- Interrupt the phone connection during submission. Use **Check order again** without rebuilding the basket. The same submission must create at most one bill. Repeat after staff have merged the source order.
- Close the POS session and confirm app ordering is unavailable. Reopen a session, refresh and try again.
- Sign in as customer B. Verify B cannot see A’s card, messages, basket or order details. Verify customer selection before payment after merging.
- Test your actual taxes, pricelist discounts, cash rounding, scanner, preparation display and any installed third-party extensions. Run the included Odoo database tests on a disposable test copy, not the live database.

## Submission and recovery behavior

The customer basket is not a sale/POS order until submitted. Each edit changes a revision key. Server pricing produces a quote tied to the customer, website, destination, session and exact lines/totals. Submission revalidates those values and the open session inside the transaction.

A locked basket and a unique submission receipt protect retries. The receipt, native order and basket clear commit together. A retry returns the saved receipt even if staff subsequently merged/deleted the source order. The connector never retrieves another guest’s merged bill through that old receipt.

Read refresh runs in the foreground about every 15 seconds and on resume/tab changes. It is polling, not background push. No mutation is automatically retried by the app; an interrupted submission retains its key for an explicit retry. Server receipts also allow the app to recognize a successful submission on refresh.

## Validation status

The implementation has local Dart/widget/API checks, Python controller-boundary checks and Python/XML parsing. Native ORM/HTTP tests are included in the addon but were not executed here because a running Odoo/PostgreSQL service is unavailable. Installation, native table merging, Enterprise kitchen dispatch, payment and final loyalty posting still require the above test-instance checks. No deployment to your server or live data has been performed.
