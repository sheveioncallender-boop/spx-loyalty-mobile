# Jenny’s member extras — test update 0.7.0+13

Connector: **19.0.4.0.0**. Android: **0.7.0+13**.

This update adds member features to the existing integration. Native POS screens, order processing, table assignment, kitchen routing, payment, accounting and loyalty calculations are unchanged. Do not install on the live database until the checks below pass on the test instance.

## Install in this order

1. Back up the test database. Deploy the replacement `spx_loyalty_mobile` folder and **upgrade that module** against `jennys.spxcorp.site`; a restart or Apps-list refresh alone does not add database fields. Use Cloudpepper’s module upgrade task if the backend is unavailable.
2. Restart the instance after the upgrade succeeds, then refresh the browser. The new backend menus are Birthday Credits, Event Announcements, Gift Cards and Sent Gifts.
3. Install the new test APK over 0.6.0. It retains the existing test certificate and application ID. Your existing login should be preserved.
4. Keep Firebase deferred. This version publishes messages to the app inbox; it does not send background device push notifications.

## Birthday credit

In native **Gift cards & eWallet**, create a dedicated **Gift Card** program named **Jenny’s Birthday Credit**. Use the normal native reward: 1 currency unit per point, applied to the whole order. Enable the sales channels where it should work, including the POS. Remove all trigger products from this promotional program so buying products never issues birthday credit.

In **Jenny’s Rewards → Settings → Customer App**:

- Choose that program under Birthday credit.
- Enter the amount and greeting. Leave validity at **21 days**.
- Keep timezone **America/Port_of_Spain**.
- Enable birthday credit and save.

The hourly job issues a native card and an inbox greeting to eligible members on their local birthday. Eligibility requires an active individual portal account with verified or preserved legacy access and a native loyalty card in a visible program. A birthday must be recorded on the contact.

The date of issue is day one. A September 23 award is valid through October 13. February 29 birthdays use February 28 in non-leap years. Once-per-year protection is per customer and company, including retries and another website in that company. Changing the amount affects future awards only. The job does not backdate missed birthdays.

For a test, use a test member whose birthday is today and run **Jenny’s: birthday credit** from Scheduled Actions. Open **Rewards → Gifts & birthday treats**. Run the job again: the card and credit must not duplicate. Do not run this on a live birthday audience while testing.

## Gift cards across purchases

Keep your existing native gift-card program, native products and existing payment provider. Enable it for POS, Sales and Website as appropriate, and keep the reward applicable to the **whole order**, not selected products. Standard native rules still determine eligibility; this connector adds no app-only redemption restriction.

Choose the purchased gift-card programs and existing gift-card products in Customer App settings. Do not select the birthday program as a purchased program. Publish the products on the same website. The app’s buy action opens their native product page and secure checkout; no separate payment processing or price calculation has been added.

A dine-in order does not fund a gift card before native payment. Draft/unpaid online purchase codes are not exposed by the new app endpoints. Online orders require native payment confirmation; fully invoiced and paid native sales are also supported. POS-issued cards require a paid, done or invoiced source order. Cards issued directly by staff remain supported.

In the app, **You → Gifts & birthday treats** provides:

- Birthday credit and purchased gift-card balances, shown separately from points.
- Add an existing physical or digital card using its full code. An unassigned card is a bearer card; knowing its valid full code allows it to be linked. A card assigned to another customer cannot be claimed.
- Buy a card through native checkout. Once paid, return to the wallet; it refreshes automatically.
- Send an eligible purchased card with a recipient name, email and optional message. Review before confirming. The entire remaining native card is assigned to the recipient contact and removed from the sender’s available cards. Its balance and expiry are not copied or reset. In this first release a card can be sent once through the app.
- Sent-gift email status: queued, sent or needs attention. Sent means handed off to the mail server, not confirmed inbox delivery. Staff can retry failed mail using the existing Emails screen.

An existing recipient contact is reused by normalized email. Ambiguous, archived or internal-user matches require staff help. A new recipient becomes a contact only, never an automatically created user. They can use the emailed code without an app account; verified signup using the same email links them to that contact and card.

Digital gift cards remain bearer codes: sending a gift does not rotate or invalidate a physical printed code. Treat the code like the physical card. POS still confirms the current remaining balance when it is used.

## Event announcements

Use **Event Announcements → New**. Write the title and body, select the website and all members or selected members. Publish to the app inbox, or choose a future time and Schedule. The scheduler runs every five minutes. Times follow the administrator’s Odoo timezone.

Only eligible members with **Events at Jenny’s** enabled receive announcements. This preference is separate from promotional email consent. Publishing twice does not duplicate the message; scheduled/published content is locked. Cancelling a scheduled announcement prevents publication. Existing direct customer messages work as before.

Firebase project creation, Android permission handling, device registration and actual background push delivery remain a later stage. No Firebase credentials are required for this test update.

## Test before live use

- Existing sign-in, password recovery, card scanning and dine-in → POS → kitchen → pay flow.
- Birthday amount/expiry, second cron run, changed birthday, next year, leap day, disabled program and separate balances.
- Own/unassigned/wrong-owner/expired/empty gift-card claims; account isolation and repeated submissions.
- Native successful, pending, cancelled and failed gift-card payments; no usable card before confirmation. Repeat the provider callback using its normal testing tools; native issuance must remain single.
- Native POS redemption and online checkout redemption against the same card, including partial balances and refunds handled by Odoo’s existing workflow.
- Sending to existing and new recipients, duplicate retry, email failure/retry, and signup afterward without duplicate users.
- Event selection, opt-out, schedule/cancel and repeated publish.

Automated Odoo integration tests are included in `tests/test_engagement.py`; run them on a disposable Odoo 19 test database with the connector and its normal dependencies installed. They must not send real customer mail.
