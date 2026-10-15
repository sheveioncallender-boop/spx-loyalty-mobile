# Jenny’s / Odoo 19 compatibility review — dine-in update

13 September 2026 · App **0.4.1+8** · Connector **19.0.2.0.1**

## Scope and status

This update was compared with official Odoo 19 source at revision `0055716c4f2672a6a083a90c08efede14375e8b2`. The native order/POS/restaurant/pricing contracts were inspected locally. This establishes source-level alignment, not proof of installation or compatibility with Jenny’s exact Enterprise patch level and installed custom addons.

The user confirmed sign-in, native card assignment, published products and receipt of a new unpaid app order in POS. Selecting that order produced a blank screen. The connector's plain-text internal note was reproduced failing in the pinned native Odoo OrderDisplay reader. Connector 19.0.2.0.1 fixes new note serialization and includes a scoped migration for existing affected app orders. Installation of this fix and successful opening of the repaired order still require confirmation on the test instance.

## POS note repair verification

- **15 Python validation/controller-boundary tests passed**, including the submitted note shape, preservation of existing text, valid-note preservation, repair scoping and idempotency. These use boundary doubles, not PostgreSQL.
- `node odoo/test_pos_note_compat.mjs /path/to/odoo19` passed against the source revision above. It executes the unmodified native `OrderDisplay.getInternalNotes()` and `TagsList` getter, reproduces rejection of the old payload and accepts both the corrected controller output and migration output. It does not render a full Owl POS screen.
- The native ORM submission test now also asserts the saved note format; the Odoo database tests and the full Enterprise POS/kitchen/checkout flow were not run locally.
- App **0.4.1+8** adds clear native order-status cards in the existing Your orders page. The five dine-in Flutter tests pass, including foreground refresh through draft, paid, done and cancel on the same order. The real status screen was rendered at 393 × 900 and visually checked. Other app screens and the approved branding remain unchanged.
- Dart analysis passed. No POS JavaScript asset, native POS model override or new POS button was added.
- All eight automatic-refresh Flutter tests passed: changed prices, changed loyalty reward descriptions/required points, removal of rewards, points after offline/resume, menu pagination, unpublished products, inbox and order-history refresh. Together with the five dine-in tests, **13 targeted Flutter tests passed** for this update.

| Area | Current implementation |
|---|---|
| Authentication | Native Odoo session; individual portal customer; enabled website; exact customer/company scope. |
| Catalogue | Existing native POS available-product/category domain, plus active/published/website/company filters. Native POS categories/sequence; no product duplication. |
| Pricing | Native pricelist product-price lookup, POS customer fiscal position and preset priorities, native tax-included price adjustment, native POS line tax calculation and order `_compute_prices()`. Unsaved native records quote the basket without creating a bill. |
| Submission | A server-built payload goes to native `pos.order.sync_from_ui()`. A fresh UUID creates a new draft order with the authenticated partner, configured POS/session, no table and no payments. Existing staff bills are never automatically edited. |
| Kitchen and tables | Staff use native Transfer/Merge and preparation actions. This connector does not dispatch kitchen tickets, assign tables or replace Enterprise preparation models. |
| Payment and loyalty | Entirely handled at native POS checkout. No app reward application, points writes, payment lines, invoice validation or stock picking is performed on submission. |
| Retries | Basket revision, server quote, transaction lock and unique receipt. Replays return the original receipt even if native merging removes the original order. Separate guests cannot retrieve each other’s receipt/basket or a merged bill via an old foreign key. |
| UI/backend extensions | App UI retained. Website connector settings and internal basket/receipt models added; no POS assets/views and no native POS model overrides. |
| Cloudpepper package | Normal addon folder with manifest at `spx_loyalty_mobile/__manifest__.py`; suitable for the existing custom-addons Git repository. Deploy/restart and upgrade the installed module. |

## Limits to validate on the test instance

Only simple published POS products can be submitted. Configurable products, combos, weighed and tracked items remain staff-assisted. Scheduled, return and address-required presets are rejected by this dine-in adapter. This is not a delivery or web-checkout implementation.

Check actual configuration: pricelists, automatic fiscal positions, tax-included/excluded products, rounding, default preset, exact website/company/POS, open session and user rights. Installed overrides that act only in website/POS controllers or JavaScript are not automatically executed by this server adapter; review them individually.

Run the included native ORM and HTTP tests against a disposable database, then test real POS receipt, table merging, kitchen routing, normal payment, rewards, refunds and points refresh. Test interruptions/retries and concurrent submissions on PostgreSQL. None of those target-instance checks were performed here; no compatibility guarantee for all Enterprise/custom combinations is implied by the local tests.

Do not connect the live database until the acceptance sequence in `DINE_IN_UPDATE.md` passes.

## Official source references

- [Native order synchronization, line taxes and order totals](https://github.com/odoo/odoo/blob/0055716c4f2672a6a083a90c08efede14375e8b2/addons/point_of_sale/models/pos_order.py)
- [Native restaurant order matching](https://github.com/odoo/odoo/blob/0055716c4f2672a6a083a90c08efede14375e8b2/addons/pos_restaurant/models/pos_order.py)
- [Customer pricelist/fiscal-position priorities](https://github.com/odoo/odoo/blob/0055716c4f2672a6a083a90c08efede14375e8b2/addons/point_of_sale/static/src/app/models/pos_order.js)
- [Native product availability domain](https://github.com/odoo/odoo/blob/0055716c4f2672a6a083a90c08efede14375e8b2/addons/point_of_sale/models/product_template.py)
- [Native automatic customer fiscal position](https://github.com/odoo/odoo/blob/0055716c4f2672a6a083a90c08efede14375e8b2/addons/point_of_sale/models/res_partner.py)
- [Restaurant Transfer/Merge workflow](https://www.odoo.com/documentation/19.0/applications/sales/point_of_sale/restaurant.html)
- [Enterprise preparation display](https://www.odoo.com/documentation/19.0/applications/sales/point_of_sale/extra/preparation.html)
