# Dine-in and Takeaway — Android 0.10.0+19

This adds a service choice to **Order → View order → Your order**, above the basket items.
The choice appears only after an administrator enables an appropriate native preset.

## Existing Odoo flow

Both choices create an unpaid native POS order for the signed-in customer.
Staff review the order, use the normal Send action for kitchen preparation, apply
eligible rewards or gift cards, and settle it through existing POS payment methods.
The app's existing Pay action becomes available when staff prepare online payment.
Takeaway does not assign a table. Dine-in table assignment and merging remain with staff.
No immediate checkout, automatic kitchen dispatch, payment overrides or loyalty rules
are introduced. Submitting a basket does not award points.

## Upgrade and configure

Use branch `codex/member-extras-19.0.4`.

1. Close POS browser tabs, pull/rebuild on the test instance, then upgrade
   **Jenny's Customer App Data** to **19.0.4.3.0** before upgrading
   **Jenny's Rewards** to **19.0.4.6.0**. Retain the installed Native POS Checkout addon.
2. In native POS configuration, use the existing Dine-in default preset and an
   existing Takeaway preset in Available presets. Presets must be enabled.
   Do not replace the current Dine-in default with Takeaway.
3. In **Jenny's Rewards → App setup → Connection and loyalty**, select the existing
   preset in **App Takeaway preset**, then save. Address-required, return and
   scheduled presets are rejected. The preset's pricelist and fiscal position
   must be compatible with the website company.
4. Reopen POS and install Android **0.10.0+19** over the existing test app.
   The APK must retain the existing sideload signing certificate and configured instance.

No native preset or POS configuration is created or changed by the connector.
The service preference belongs to the customer's website-specific basket, and
defaults to Dine-in on upgrade. Changing it invalidates the previous quote and
recalculates prices/taxes using Odoo. An interrupted submit retries the original
key/quote. A removed Takeaway preset blocks submission and lets the customer
switch back to Dine-in; it never silently substitutes a Dine-in order.

## Acceptance on the test instance

1. Add one TT$15 demo lime juice. Open View order, choose Takeaway, review the
   total and place once. Leave unpaid for inspection.
2. In POS, verify the customer, native Takeaway preset, Takeaway order name,
   no table, unpaid total, and exactly one order. The kitchen should receive it
   only after the staff member uses Odoo's normal Send action.
3. Settle through the existing POS flow. Verify one payment, one native loyalty
   award and the matching refreshed app balance/history.
4. Repeat with Dine-in and confirm the current staff-controlled table/payment flow.
5. Check interruption/retry and a preset with different prices or fiscal position.

Local and CI checks supplement this test; they do not establish acceptance in
the Enterprise instance or on the physical Android device. Physical barcode
scanner, refund, session-closing, iOS and production-release checks remain separate.
