# Illustrated manual and acceptance requirements

This document defines the acceptance and documentation scope. It is not the final customer manual.

## Release acceptance

Test the same customer order from the installed Android app through native Odoo POS, table confirmation, kitchen preparation, payment and the customer's updated loyalty balance. Test takeaway and app payment separately when implemented. A controller test, widget test or POS-entered order must not be reported as a complete app-originated device test.

Physical scanner acceptance is separate from typing a card code or testing a barcode lookup method. Scan the phone-displayed native loyalty card with the intended POS scanner and verify that the correct customer and native card are selected.

For loyalty eligibility, distinguish the stored balance from the POS preview of points that this unpaid order may earn. After changing program rules, refresh native POS data before testing. Preserve saved orders; do not discard unrelated unsaved work during synchronization.

Required outcomes include:
- No spendable new points before full payment.
- Correct redemption, cancellation and refund behavior.
- Gift-card purchase, issuance, partial redemption and remaining balance.
- Birthday rewards from the configured existing customer date, annual duplicate prevention and expiry.
- No duplicate order or payment after retries or interrupted connections.
- Gateway success, decline, cancellation, abandoned checkout and repeated callbacks.
- Correct native payment records, journal entries, POS closing, invoice reconciliation where applicable, and bank settlement/fees.
- Clean Odoo 19 install, upgrade, uninstall/reinstall retention and explicit app-data removal.
- Android completion before equivalent iOS device acceptance.

Keep the payment gateway disabled until the integration and callback review is complete. Start with sandbox/Test mode; source review alone does not establish payment or accounting acceptance.

## Final illustrated manual

Deliver a printable PDF and editable source after the relevant workflows pass.

For each procedure include the responsible role, prerequisites, numbered actions, labelled screenshots, expected results, and common errors with recovery steps. Use demo records and approved configuration examples; exclude credentials and real customer information.

1. Administrator: install on Odoo 19, connect the instance and complete guided setup.
2. Customer: signup, email verification, login, recovery and profile.
3. Cashier and customer: display/enlarge the app loyalty card, scan at POS, verify customer and balance, and use manual entry if the scanner cannot read it.
4. Loyalty: earn after payment, redeem, distinguish automatic promotions, and verify the same native balance in the app.
5. Gift cards: purchase, issuance, app display, scanning, redemption and remaining balance.
6. Birthdays: existing date source, eligibility, issuance, expiry and redemption.
7. Dine-in: app basket, order submission, staff table assignment, kitchen, bill additions, app or in-person payment.
8. Takeaway: service selection, preparation, payment and collection.
9. Payments and accounting: administrator sandbox configuration, outcome checks, native postings and reconciliation.
10. Exceptions: failed connections, duplicate submissions, unavailable items, cancellations and refunds.
11. Daily operations: open/close POS, cash checks and kitchen completion.
12. Maintenance: upgrade, reinstall, retention choices and reconnect existing records.
13. Devices: Android/iOS installation plus a concise staff quick-reference checklist.

Untested steps remain clearly marked pending in working drafts. Do not illustrate an unimplemented screen as if it were available.
