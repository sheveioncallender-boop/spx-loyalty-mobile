# Full-refund correction — Native POS Checkout 19.0.1.0.3

## Acceptance evidence, 19 October 2026 (Trinidad time)

- Takeaway `260-1-000013`: TT$15 cash, customer retained, one 15-point award.
- Dine-in `260-1-000015`: customer retained on the same order after native table
  transfer. Two cancelled checkout attempts were recorded as errors, with no
  accounting payment. The third attempt was confirmed with one TT$15 POS online
  payment, one accounting payment and one 15-point award (201.5 → 216.5).
  This was the configured gateway's test environment, not a live-card settlement.
- Takeaway `260-1-000016`: native TT$15 gift-card redemption, card balance zero,
  no cash/card payment, and one 15-point award (216.5 → 231.5).
- Native cash refund `2610-1-000002` (POS order 26) links to original order
  `260-1-000013` (POS order 21). Paid, one Cash payment of -TT$15. The native
  refund did not reverse the original 15 earned points; balance stayed 231.5.

## Correction and deployment gate

The new bridge reverses the original recorded award after a native full refund
of an eligible plain app bill. It does not replace any native refund/payment,
kitchen, stock, table, preset or accounting operation. See the bridge README for
scope and review requirements for partial refunds and reward-bearing bills.

After deploying and upgrading the bridge to **19.0.1.0.3**, open existing refund
`2610-1-000002` and use **Reconcile Refund Points** once. Verify:

1. The existing refund still has exactly one Cash payment of -TT$15.
2. Original order `260-1-000013` retains its original 15-point award.
3. Refund `2610-1-000002` has exactly one native history entry with issued -15
   and used 0 for the same loyalty card.
4. Balance becomes **216.5** from **231.5**.
5. Repeating reconciliation leaves the balance and financial records unchanged.

This reconciliation and its live balance check are **pending deployment**.
Do not describe the historical balance as corrected until independently read.
Do not refund the cash again or manually edit the card's balance.

Partial-refund loyalty, session/accounting close, physical scanning and iOS
acceptance remain outstanding. Original native Takeout remains configured;
the app uses App Takeaway. Native POS Checkout remains installed.
