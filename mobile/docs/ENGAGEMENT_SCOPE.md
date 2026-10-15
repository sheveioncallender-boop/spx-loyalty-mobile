# Jenny’s next app update — agreed scope

Confirmed 23 September 2026.

## Birthday reward

Admins select the native birthday credit programme, enter the credit amount and choose the greeting in Jenny’s settings. The amount is not hard-coded. Validity defaults to the requested 21 days. The award is issued once per customer and company per year. Administrators choose verified app members or all customer contacts with birthdays. Existing contact Date fields can be selected; empty values fall back to the signup birthday. Its balance and expiry stay in Odoo; the app displays them. Birthday promotional credit stays separate from purchased gift cards and ordinary loyalty points.

The birthday notification opens the reward in the app. The reward must still exist if the customer has notifications disabled. Admins can inspect the issued award and native card. Changing settings affects future awards, not already issued balances.

## Event announcements

Admins compose and preview an event title and message in Jenny’s Odoo backend, choose the audience, and send immediately or schedule. Karaoke, Latin Nights and other events use the same composer. Messages remain in the existing app inbox. Mobile push requires notification permission, device registration and a configured Firebase project. Do not send any real customer notifications while testing.

## Digital and physical gift cards

Cards assigned to the customer in Odoo appear automatically. Customers can buy a native card and send it as a gift; there is no code-claim step. All views refer to native Odoo card records, never copied balances. Validate card ownership and eligibility before linking or displaying a code. Prevent duplicate purchase fulfilment and cross-customer access.

Purchase uses Odoo’s existing gift-card product and payment-provider flow. A submitted dine-in order is not a paid gift-card purchase. Only native confirmed payment/fulfilment can produce spendable purchased value. Staff continue selling and redeeming physical cards in the native POS. The app must not override native prices, taxation, gift-card issuance, payment confirmation, POS redemption or accounting.

The recipient flow must support an existing member and a recipient who has not registered yet, without creating duplicate users by email. Gift delivery must not expose a customer’s ordinary loyalty card or birthday credit.

## Preserve

- Existing Jenny’s design, onboarding, verified signup and password recovery.
- Existing native dine-in order → POS → kitchen → payment workflow.
- Odoo controls products, prices, programme rules, balances and redemption.
- Website remains informational; these functions belong in the app.

## Required acceptance checks

- Configurable birthday amount, 21-day boundary, local birthday date, one award per year, retries and changed birthday.
- Push permission denied, token refresh, logout/account switch and duplicate delivery handling.
- Admin event draft/preview/audience/scheduling and opt-out handling.
- Automatic digital/physical card assignment, wrong owner, expired/empty card and rate limiting.
- Successful, cancelled, failed and repeated gift-card payment notifications; no prepaid value before payment.
- Recipient email matches, new-member registration, delivery retry and unchanged native POS redemption.

## Implementation status

Android 0.7.1+14 and connector 19.0.4.1.0 include customer birthday management, native birthday credit issuance/adjustment links, inbox announcements, automatic gift-card display, native checkout handoff and recipient delivery. See MEMBER_EXTRAS_TEST.md. Background device push and Firebase remain deferred. No live instance has been modified by this work.
