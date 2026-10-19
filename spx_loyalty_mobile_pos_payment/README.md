# Native POS checkout from the app

## Checkout bridge 19.0.1.0.3 — full-refund loyalty reversal

After Odoo completes a full refund of a plain app-originated bill, reverse the
exact loyalty award recorded on that original bill. The original sale's history
is retained. Odoo's `confirm_coupon_programs` records negative issued points
against the refund; native history and row locks prevent a second deduction.
This does not recalculate earning rules or directly write card balances/history.
An intervening redemption may leave the card negative after the full reversal.

The native refund selection, quantities, cashier validation, cash/bank payments,
stock, accounting and session close are unchanged. The hook runs after native
saved-order processing. A loyalty failure preserves the completed monetary
refund and shows a staff-review warning in POS. Retrying reconciles points only.
The POS refreshes the affected card after its ordinary loyalty processing.

Scope: one fully paid refund returning every line of one fully paid, customer-
linked app bill, without reward lines, exchanges or previous return lines.
Partial refunds, mixed exchanges and reward-bearing bills require separate
loyalty review; their monetary refunds still use Odoo normally. Gift-card and
eWallet credit and spent reward points are not restored by this correction.
Unrelated POS orders retain Odoo's existing behavior.

Deploy this branch, restart Odoo, then upgrade **Jenny's Rewards - Native POS
Checkout** (`spx_loyalty_mobile_pos_payment`) to **19.0.1.0.3** and reload POS.
No Android rebuild or payment-provider update is needed. Upgrading does not
automatically change historical balances.

For an already completed eligible refund, a POS manager opens that refund in
POS Orders and clicks **Reconcile Refund Points**. The action is repeatable and
does not create or modify a payment, refund, invoice or stock movement. Verify
one negative earned-points history entry and the expected balance afterward.
Never initiate another monetary refund to repair loyalty.

## Checkout bridge 19.0.1.0.2 — durable native loyalty

A delayed successful online payment could leave points missing if the cashier's
POS browser had closed: Odoo's POS loyalty compiler runs in the browser, while
the bank can finish the payment independently.

For app-originated bills, the bridge now captures Odoo's native loyalty payload
when the cashier prepares online payment, before exposing the payment amount.
It stores the payload with a fingerprint of the customer and saved bill. Native
payment completion confirms it through `pos.order.confirm_coupon_programs`
only after the bill is fully paid and still matches. Odoo remains responsible
for the earning calculation, existing card selection, reward links and history.
No direct points increments or history creation are added.

The order row serializes callback/browser confirmation; native history suppresses
duplicate awards. A late browser receives the current card balance. Cancelling
checkout or clearing the QR request keeps the prepared payload, so a successful
retry uses the same restaurant order. A loyalty failure is isolated from payment
processing and leaves the handoff available for retry.

When POS reconnects, older fully paid app bills with online payments and no loyalty
history can recover through the same native compiler. Automatic recovery is
limited to unchanged automatic loyalty programs and bills without reward lines.
Changed historical rules or reward spending require review. Gift cards and other
promotion types retain their native POS confirmation flow.

Deployment: pull this branch, restart Odoo and upgrade **Jenny's Rewards - Native
POS Checkout** (`spx_loyalty_mobile_pos_payment`) to **19.0.1.0.2**. Reload the POS.
The Android app and Scotia modules do not need a new build for this correction.
Verify the affected order has one native loyalty history entry and the expected
balance; do not manually add points while recovery is pending.

### Customer identification and seating

Loyalty scanning is not required for entry or seating. Staff assigns the table
using Odoo's restaurant flow. A signed-in app order is already linked to its
customer. For an order entered by staff, scan the loyalty card or select the
customer on that same order before applying rewards and taking payment.
Finalize rewards before preparing the bill. Customers then pay through configured
POS methods or the prepared Scotia checkout. Points become available after full
payment. Immediate takeaway checkout remains a separate acceptance stage below.

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
It uses existing POS orders and adds a stored loyalty handoff and completion flag to app-originated bills. It creates no alternative payment or accounting workflow.

## Dine-in flow in Android 0.9.0

1. The customer orders from the app. Odoo receives its existing unpaid POS order.
2. Staff confirms the table, sends preparation and manages the meal as usual.
3. When the final bill is ready, the customer can pay with **any configured POS payment method**, or choose online payment through Scotia.
4. For app payment, staff selects the existing **Scotiabank Online** method and presses native **Validate** once. The current bridge persists the loyalty handoff before opening checkout.
5. The customer opens **You → Your orders**, refreshes if needed, and taps **Pay**. The same native `/pos/pay` checkout opens; the customer does not need to scan their own phone.
6. After checkout, **Back to my orders** refreshes the native bill and loyalty balance. Closing checkout alone never marks anything paid.

The Pay action is offered only for an owned draft bill in the configured website/company/POS, with an open session, a positive valid cashier-prepared next payment amount and an eligible published online provider. Order history never carries payment tokens. The authenticated handoff rechecks ownership and readiness before issuing Odoo's native token. No customer-supplied amount, currency, provider or partner is accepted.

For Jenny's, the native online POS method should allow the configured Scotia provider. Its sandbox USD simulation remains test-only. Other in-person methods are untouched. The PayBridge POS Completion companion refreshes the cashier's payment screen. The current bridge also completes prepared loyalty when that browser has closed.

## Installation

Rebuild the existing `codex/member-extras-19.0.4` branch and upgrade **Jenny's Rewards** to **19.0.4.5.0**. Refresh the Apps list and ensure **Jenny's Rewards - Native POS Checkout** is installed (technical name `spx_loyalty_mobile_pos_payment`). It is auto-installable when both dependencies are present, but some existing deployments need one activation after refreshing the Apps list. Install Android **0.9.0+16** over the previous test build.

The gateway stays in Test mode. No changes to Odoo core, gateway secrets, production settings, existing payment methods, taxes, cards or accounting are required by this adapter.

## Next acceptance stages

- Test an Android-originated bill through staff readiness, Scotia checkout/3DS, POS completion, a single payment and one loyalty award.
- Test payment at POS while the app is open, cancellation/decline, stale offers, interruptions, partial payments and retries.
- **Takeaway requirement:** customer may pay immediately, or use configured POS methods. This release deliberately exposes only staff-prepared dine-in payment. Implement immediate takeaway through native order presets/self-order processing and verify kitchen dispatch and loyalty before enabling it. Do not bypass cashier readiness on dine-in bills or claim takeaway acceptance from these tests.
- Physical scanning, settlement/reconciliation, POS closing and iOS remain separate acceptance steps.

