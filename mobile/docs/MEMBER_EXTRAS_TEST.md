# Jenny’s member extras — test update 0.7.1+14

Connector: **19.0.4.1.0**. Android: **0.7.1+14**.

This update adds birthday management and removes customer gift-card code entry. Native POS screens, orders, table assignment, kitchen, payments, accounting and redemption are unchanged. Odoo generates all card codes and holds all balances and expiry dates.

## Update the test instance

1. In Cloudpepper pull **codex/member-extras-19.0.4**, not main, from the existing spx-loyalty-mobile repository.
2. Upgrade the installed **spx_loyalty_mobile** module to **19.0.4.1.0**. Do not uninstall it. Restart after a successful upgrade and refresh the browser. Pulling files or restarting alone does not add the new database fields.
3. Install Android **0.7.1+14** over the existing test app. Its application ID and test signing certificate are unchanged.
4. Firebase remains deferred. Announcements and birthday greetings appear in the app inbox; background device push is not enabled yet.

## Birthday Settings

Open **Jenny’s Rewards → Member Extras → Birthday Settings**, then your website.

- **Birthday credit program:** select a dedicated native Gift Card program, such as Jenny’s Birthday Credit. Keep it separate from purchased gift cards. Use the native whole-order reward of one currency unit per point, in the website currency. Enable the native POS/Sales/Website channels where it should work. Remove sale trigger products so purchases do not issue promotional birthday credit.
- **Birthday credit amount:** your default amount; it is not hard-coded.
- **Birthday validity (days):** defaults to 21. It can be changed.
- **Birthday greeting:** the inbox message customers receive.
- **Existing customer birthday field:** if birthdays already exist in another stored Date field on Contacts, select that field. It is read directly; no dates or contacts are copied. A blank value falls back to the birthday collected at app signup.
- **Audience:** Verified app members (existing default), or All customer contacts with a birthday. The second option includes customers who have not joined the app. Choose it explicitly to enable automatic awards for them.
- **Timezone:** America/Port_of_Spain.
- Enable birthday credit and save once the program and amount are configured.

Default amount and validity changes affect future awards, not existing cards.

## Customer Birthdays

Open **Member Extras → Customer Birthdays**. If more than one website is enabled, select the website in Birthday Settings and click Customer birthdays.

The list reads active individual top-level customer contacts, including nonmembers. Companies, child contacts and contacts with internal staff users are excluded. It shows:

- Customer, email, existing birthday and next birthday.
- Days until birthday, with Today and Next 30 days filters.
- Available birthday credit, read from native gift cards in the website currency.
- Next credit expiry and days left to use credit.
- Whether credit has already been issued this calendar year.

The available balance excludes expired, empty or inactive cards/programs. Where several cards exist, the expiry column shows the earliest expiry among usable credits. Records without a birthday are not listed; edit the contact’s birthday in its existing field first.

## Issue or adjust birthday credit

Use **Issue credit** beside a customer. Enter the amount, validity and reason, then confirm. The defaults come from Birthday Settings. Staff may issue before the birthday; it uses the current calendar year’s allowance. Issuing again opens the existing annual credit instead of adding another one.

Open **Member Extras → Birthday Credits** for the issue history. The screen now has **Issue credit**, **Update Balance**, and **Open native card** actions:

- **Update Balance** opens Odoo’s own balance adjustment wizard. Enter the new balance and reason there.
- **Open card / edit expiry** opens the native card for expiry changes and its native history.
- The original issue amount stays in the award history; the current balance and expiry are read from the card.

For cards created directly in Odoo’s native birthday program, use **Open native cards** beside the customer. They appear in the app without requiring an award-history record or a claim code. A card already issued in the birthday program this year blocks a second automatic/manual award; adjust that native card instead.

Administrators manage these controls. Customer accounts cannot browse other customers’ birthdays or issue credits.

## Automatic birthdays

The hourly **Jenny’s: birthday credit** scheduled action issues one native card and inbox greeting on the customer’s local birthday. The selected audience determines eligibility. Member-only eligibility uses the existing verified/legacy portal membership and visible loyalty program rules.

The issue date is day one: September 23 plus 21 days is valid through October 13. February 29 birthdays use February 28 in non-leap years. Once-per-year protection is per customer and company, including retries and multiple websites in the same company. Missed birthdays are not backdated automatically; staff can issue manually.

## Gift cards — automatic, no claiming step

1. Staff assign a native gift card to the customer’s contact in Odoo. Its program must be selected under Customer App → Purchased gift card programs.
2. The card appears automatically in **You → Gifts & birthday treats** on refresh/resume. Digital and physical cards use the same native record. There is no Add code step.
3. **Buy a gift card** opens the configured, published native product and checkout. Odoo handles price, payment and code generation. After native payment confirmation, return to the app to see the card. Unpaid purchase codes are not exposed.
4. To give a purchased card, choose **Send as a gift**, enter the recipient’s name/email and review. The entire remaining card is reassigned to that recipient contact and emailed. Balance, code and expiry are not regenerated or reset.
5. An existing customer sees the card in their account. A new recipient can register with that same email; signup reuses the contact. Receiving a gift alone does not create a login. The recipient may also present the gift email at Jenny’s.

A card can be sent once through this app flow. Purchased cards and birthday credit stay separate. Gift-card email status is queued, sent or needs attention; sent means handed to the mail server, not confirmed inbox delivery. Staff can retry mail in the existing Emails screen.

Keep native gift-card rewards applicable to the whole order and enable the sales channels where they should work. Normal Odoo rules still apply. This connector adds no app-only purchase restriction and no custom POS redemption screen. Existing older APKs cannot claim unassigned codes after this connector update either; staff link physical cards to customers in Odoo.

## Focused test on your test instance

1. Configure the birthday program, amount and source date field. Check a customer who has not signed up appears in Customer Birthdays with the expected date/countdown.
2. Issue 100 with 21 days. Confirm one native card and one award record, correct expiry and an app balance of 100. Repeat Issue credit; no second award should appear.
3. Use native Update Balance to change to 75. Confirm the app shows 75 after refresh. Use the native card form to change expiry and check the countdown.
4. Select a test customer with today’s birthday. Run the birthday job twice with each audience setting. Confirm member-only excludes nonmembers and all-customer mode includes them without duplicates.
5. Assign a purchased gift card directly in Odoo. Confirm it appears without code entry. Check another account cannot see it.
6. Buy through native checkout, return after payment, then send to an existing and a new test recipient. Confirm ownership, unchanged balance, mail status and later signup reuse. Also check pending/cancelled payments reveal no usable code.
7. Redeem part of the balance in native POS and refresh the app. Continue existing order → POS → kitchen → pay testing, including native refunds and point awards.

Use test contacts and mailboxes only. Automated Odoo tests are supplied in tests/test_engagement.py, but still require a disposable Odoo 19 database. Flutter tests and static checks cannot replace the Cloudpepper module-upgrade and native POS/payment checks.
