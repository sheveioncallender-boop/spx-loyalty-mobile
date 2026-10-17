# Test instance setup — Odoo 19

This connector requires Odoo 19 with custom Python addon installation: Odoo.sh or a self-hosted installation. Confirm the hosting type before installation. The module does not require an Enterprise API key in the mobile app.

## Install

1. Back up the test database using the host’s usual process.
2. Extract `spx_loyalty_mobile.zip`. The extracted `spx_loyalty_mobile` folder must be inside an Odoo addons path, alongside the existing addons. On Odoo.sh, commit it to the test/staging branch’s custom addons repository.
3. Restart the Odoo service/build, update the Apps list in developer mode, then install **Jenny's Rewards** (technical name `spx_loyalty_mobile`, previously **SPX Loyalty Mobile Connector**). For an existing installation, use **Upgrade**, then fully refresh the browser. The manifest declares `website_sale_loyalty`, `pos_loyalty`, `pos_restaurant`, `portal` and `mail`; Odoo resolves the native dependencies.
4. Open **Website → Configuration → Websites**, select the exact test website, and open its **Customer App** tab. Enable the customer app, set the brand name and select the existing Jenny’s loyalty program(s). The selected programs must belong to this company/website or be shared with it.
5. Verify the website domain is configured correctly, uses a trusted HTTPS certificate, and routes to the intended database. Use that exact domain in the developer build configuration, without `/web` or `/shop` in the address. Set the database there too; customers only enter their email and password. See `BUILD.md`.

## Prepare a customer

1. Choose an individual customer contact and grant normal portal access through Odoo’s existing portal invitation process.
2. For this initial beta, use a dedicated test customer without multi-factor sign-in. The connector does not bypass Odoo’s MFA; the app currently stops at an incomplete MFA session.
3. Ensure the existing loyalty card is assigned to that **exact contact**, not a different company contact. The connector deliberately does not inherit another contact’s balance through a commercial parent.
4. If the program normally creates a card after the first qualifying purchase, follow that native workflow. The app will show an empty card state until a real card exists. Do not invent a balance in the app.
5. Select **Dine-in Point of Sale** in the website Customer App tab. Publish existing menu products and mark them available in that POS. Open a POS session. See `DINE_IN_UPDATE.md` for the new unpaid-order workflow and test sequence.

## In-store scanning

Upgrade **Jenny's Rewards** (`spx_loyalty_mobile`) to `19.0.2.0.0` on the test instance. The native `pos_loyalty` dependency supplies Odoo’s existing POS card lookup and rewards integration. There is no separate mobile points ledger, earn endpoint or POS JavaScript patch.

### Configure the till

1. In the POS configuration, enable **Promotions, Coupons, Gift Card & Loyalty Program** if it is not already enabled. Open the existing Jenny’s program under **Point of Sale → Products → Discount & Loyalty**. Keep its type **Loyalty Cards** and enable **Point of Sale**. Ensure its POS restrictions include Jenny’s till (an empty list allows all eligible tills), and check currency, pricelist, dates, products and earning rules. Use this same program in the website’s **Customer App** configuration.
2. Use the customer’s existing card assigned to their exact portal contact. The mobile barcode is the exact Odoo code, including punctuation and case. Do not add a prefix, strip hyphens, replace it with a contact barcode or create a second card for the app. If a customer has several cards for the same program, verify which card the native POS updates before deployment.
3. Check the POS’s barcode nomenclature. Native Odoo-generated loyalty codes start with `044`; the standard **Coupon & Gift Card Barcodes** rule has type `coupon`, encoding `any`, pattern `043|044`, and sequence `50`. Ensure this rule exists in the nomenclature actually used by the till and runs before a catch-all product rule. For GS1 tills, configure an appropriate standard fallback nomenclature for these non-GS1 card codes. For previously customised card codes, add a narrowly matching coupon rule for their actual pattern; do not change the stored codes or route every product barcode to loyalty.
4. Use a POS scanner that supports Code 128 and can read phone displays. Verify it sends the exact code with no added character prefix and the normal end-of-scan terminator. Test on the actual scanner; older laser-only hardware may require manual entry instead.
5. Reload/reopen the POS after changing modules or configuration.

### Customer and cashier flow

1. Customer: open **My card → Scan at Jenny’s**. The card flips to reveal its barcode. Use **Enlarge barcode** if needed. Preview mode uses a sample card and cannot earn real points; sign in to the test instance for a real test card.
2. Cashier: scan before completing payment on the POS product screen. Odoo’s coupon handler calls native `activateCode`, which looks up `loyalty.card.get_loyalty_card_partner_by_code`, selects that customer on the order and updates native rewards. Confirm the correct customer is shown on the order, especially if another customer was selected previously.
3. Cashier: complete the eligible sale normally. Odoo’s configured loyalty rules control earning and redemption. A scan alone is not a purchase or a points award, and does not prove that a program is eligible at this till.
4. Customer: tap **Show card front**, or close the enlarged scan screen, to refresh the app balance and history. If the POS has not synced yet, pull to refresh after it reconnects. A live lookup requires the POS to reach Odoo; offline lookup/synchronisation must be tested separately.
5. If scanning fails, the cashier can use the POS **Enter Code** action with the exact displayed/copied card number, or select the correct customer through the normal POS customer flow.

### POS acceptance checks on the test instance

- Compare the app’s decoded barcode with the exact native card code, then scan using Jenny’s actual phone/scanner combination. Confirm the linked customer is selected.
- Scan the same card twice before payment. Confirm no points have been added merely for scanning. Complete one qualifying sale and confirm the configured points post once to the correct native card, then appear after app refresh.
- Repeat with customer B and with a different customer already on the order. Confirm no points go to customer A by mistake.
- Test ineligible products/orders, expired or inactive cards/programs, insufficient points, an unknown code and a program not enabled for this POS. The app does not override Odoo’s decisions.
- Test an eligible redemption, cancellation and refund through native POS. Compare the resulting card/history with the app.
- Verify brightness and screen-awake behavior on Android, including closing the screen and backgrounding the app.

Native source reference: [Odoo 19 POS loyalty scan flow](https://github.com/odoo/odoo/blob/19.0/addons/pos_loyalty/static/src/app/services/pos_store.js), [default coupon barcode rule](https://github.com/odoo/odoo/blob/19.0/addons/pos_loyalty/data/default_barcode_patterns.xml). These paths were inspected in the supplied local Odoo 19 source. Physical till and Enterprise test database acceptance remain pending.

## Messages and email

Administrators can use **Jenny’s Rewards → Messages** to create an inbox message for a specific customer and website. The message appears on the next in-app refresh. Tapping it marks it read for that customer.

For promotional email, the customer first opts in under **You → Email preferences**. An administrator can then use **Queue email** on that message. Odoo’s configured outgoing mail service and mail queue send it. The email action is deduplicated on the message; delivery success must be checked in the normal Odoo mail queue.

Native order receipts and loyalty communication plans retain their existing behavior. Firebase push is not configured or sent by this initial module.

## Dine-in acceptance tests

Follow `DINE_IN_UPDATE.md`. Ordering now creates unpaid native POS orders; staff control table assignment, kitchen dispatch, rewards and payment. There is no eCommerce checkout in this APK.

## Odoo database tests

Run against a disposable test database with the correct addons paths configured:

```bash
odoo-bin -d jennys_mobile_test -i spx_loyalty_mobile \
  --test-enable --test-tags /spx_loyalty_mobile --stop-after-init
```

Use `-u spx_loyalty_mobile` for an already installed test database. These tests require an actual Odoo/PostgreSQL environment. Python/XML checks alone do not prove installation or live Enterprise compatibility.

## Integration contract

All companion endpoints use authenticated POST JSON-RPC 2.0. Authenticate with native `/web/session/authenticate`; send its `session_id` cookie. No admin API key is embedded in the app.

| Prefix | Endpoint | Purpose |
|---|---|---|
| `/spx/mobile/v1/` | `bootstrap` | Existing customer, cards, points, rewards, native history and inbox |
| `/spx/mobile/v1/` | `preferences`, `messages/read` | Existing preference/inbox behavior |
| `/spx/mobile/v2/dine-in/` | `catalog` | Published products from the selected native POS menu and pricing |
| `/spx/mobile/v2/dine-in/` | `cart` | Read basket, native quote, availability and last submission receipt |
| `/spx/mobile/v2/dine-in/` | `cart/add`, `cart/update` | Edit only this customer’s pending basket, with revision checks |
| `/spx/mobile/v2/dine-in/` | `submit` | Validate quote and create one new native unpaid order, or return prior receipt |
| `/spx/mobile/v2/dine-in/` | `orders` | Exact customer’s native POS bills for this website’s selected POS |

The v1 catalog/cart mutation routes are retired. No endpoint accepts customer identity, table assignment, payment, price, tax, point award or native POS order IDs from the app. There is no automatic append/merge logic and no replacement loyalty ledger.
