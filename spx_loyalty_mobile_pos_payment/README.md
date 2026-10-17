# Native POS checkout from the app

## Android 0.9.2 / Jenny's Rewards 19.0.4.5.2

Paid order cards show native POS payment methods, amounts, dates, and separate
change/refund lines. Card receipts include the brand and last four digits when
recorded by Odoo. Scotia details follow the exact POS payment → accounting
payment → verified transaction relation, so existing paid orders also work.
The customer API exposes a fixed receipt allowlist, never raw terminal receipts,
full card numbers, cardholder names, bank approval data or payment tokens.
Pending orders do not display editable POS payment lines as completed payments.
Order ownership, company and POS scope remain enforced by the existing endpoint.

The in-person POS acceptance test exposed a second native payment path: POS UI
sync writes payment lines directly, bypassing `add_payment`. Refresh app-linked
receipt/display metadata after native `_process_saved_order` as well, once Odoo
has calculated the paid amount and completed its ordinary workflow. Regression
tests cover partial and full cash payment through `sync_from_ui`, a repeated
submission, and exclusion of unrelated orders. No payment, accounting or loyalty
logic is replaced. The upgrade repairs the same display on existing app bills.

Upgrade **Jenny's Rewards** to **19.0.4.5.2** after deployment and install Android
**0.9.2+18** over the previous test build. No Scotia update is required.

## Android 0.9.1 / Jenny's Rewards 19.0.4.5.1

The home screen now has a visible **Your orders & bill** card. It opens the
existing orders screen and its cashier-prepared Pay action. The shortcut under
You remains available. Dine-in payment readiness is unchanged.

App-created orders now receive the native five-character receipt code. After
native `add_payment`, the app integration refreshes only the stored difference
display for orders linked to an app submission, using Odoo's paid-minus-total
formula. It does not create another payment or alter taxes, totals, accounting,
payment state or loyalty. Other POS orders are unaffected.

Upgrading **Jenny's Rewards** to **19.0.4.5.1** repairs the stale difference and
missing receipt codes on existing app-linked orders. The repair is idempotent
and preserves existing codes. Reload the POS after upgrading to see repaired
receipt metadata. No separate Scotia update is required.

This optional adapter depends on Jenny's Rewards and Odoo's `pos_online_payment`.
It adds no persistent models, POS methods, payment transactions or accounting overrides.

## Dine-in flow in Android 0.9.0

1. The customer orders from the app. Odoo receives its existing unpaid POS order.
2. Staff confirms the table, sends preparation and manages the meal as usual.
3. When the final bill is ready, the customer can pay with **any configured POS payment method**, or choose online payment through Scotia.
4. For app payment, staff selects the existing **Scotiabank Online** method and presses native **Validate** once. Keep the POS browser and payment request open.
5. The customer opens **You → Your orders**, refreshes if needed, and taps **Pay**. The same native `/pos/pay` checkout opens; the customer does not need to scan their own phone.
6. After checkout, **Back to my orders** refreshes the native bill and loyalty balance. Closing checkout alone never marks anything paid.

The Pay action is offered only for an owned draft bill in the configured website/company/POS, with an open session, a positive valid cashier-prepared next payment amount and an eligible published online provider. Order history never carries payment tokens. The authenticated handoff rechecks ownership and readiness before issuing Odoo's native token. No customer-supplied amount, currency, provider or partner is accepted.

For Jenny's, the native online POS method should allow the configured Scotia provider. Its sandbox USD simulation remains test-only. Other in-person methods are untouched. Use the separately tested PayBridge POS Completion companion for automatic native loyalty completion; it currently requires the POS browser to remain open.

## Installation

Rebuild the existing `codex/member-extras-19.0.4` branch and upgrade **Jenny's Rewards** to **19.0.4.5.0**. Refresh the Apps list and ensure **Jenny's Rewards - Native POS Checkout** is installed (technical name `spx_loyalty_mobile_pos_payment`). It is auto-installable when both dependencies are present, but some existing deployments need one activation after refreshing the Apps list. Install Android **0.9.0+16** over the previous test build.

The gateway stays in Test mode. No changes to Odoo core, gateway secrets, production settings, existing payment methods, taxes, cards or accounting are required by this adapter.

## Next acceptance stages

- Test an Android-originated bill through staff readiness, Scotia checkout/3DS, POS completion, a single payment and one loyalty award.
- Test payment at POS while the app is open, cancellation/decline, stale offers, interruptions, partial payments and retries.
- **Takeaway requirement:** customer may pay immediately, or use configured POS methods. This release deliberately exposes only staff-prepared dine-in payment. Implement immediate takeaway through native order presets/self-order processing and verify kitchen dispatch and loyalty before enabling it. Do not bypass cashier readiness on dine-in bills or claim takeaway acceptance from these tests.
- Physical scanning, settlement/reconciliation, POS closing and iOS remain separate acceptance steps.
