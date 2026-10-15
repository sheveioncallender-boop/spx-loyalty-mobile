> Current ordering uses the dine-in API in 0.4.0. The foreground-refresh behavior below remains; references to website cart/checkout describe the earlier 0.3.2 implementation. See DINE_IN_UPDATE.md for current basket and submission behavior.

# Automatic refresh — Android 0.3.2+5

Odoo remains the system of record. This update reads the existing customer,
loyalty, product and order records through the same authenticated connector.
It does not import a catalogue, create replacement customers, maintain a
separate points ledger or override Odoo's pricing/loyalty calculations.

## Customer experience

- While the app is active, it checks for updates every 15 seconds. The next
  successful response updates the screen without a full-page loading transition.
- Returning to the app or selecting a navigation tab also requests fresh data.
- Pull-to-refresh remains available as an optional immediate check.
- The app updates products, displayed prices, categories, card balances,
  available program rewards, customer details and inbox messages. An open
  order-history page also refreshes its native online-order records.
- Open product, inbox and cart sheets listen for refreshed data. A product
  removed from the available catalogue is marked unavailable in its open sheet.
- Search text, valid category selection, tab scroll positions, selected card
  identity and the number of catalogue pages already loaded are retained.
- If a selected category no longer exists, the menu returns to All.
- Polling stops while the app is in the background, after logout or when the
  session expires. Brief connection failures retain the last successful data;
  later checks retry reads. Customer actions are never automatically retried.
- Refreshes are paused while native website checkout/account pages are open;
  returning from those pages requests the latest app data.

This is automatic foreground polling, not an instantaneous server-push feed or
background device notification service. The normal delay is up to 15 seconds
plus the response time of the test server and network.

## Native data and existing live records

Menu records must be available to the customer's Odoo website and published for
online sale. Products enabled only for POS are not automatically published.
The same eligibility rules apply to existing products and newly created ones.

The customer's portal login and loyalty card must reference the same native
contact. Existing points are displayed as stored in the selected eligible
program; they are not reset when installing or upgrading this connector.

Cart amounts are the amounts returned by the native draft order. Polling does
not force a custom repricing policy or change an order. Native cart/checkout
actions continue to control pricing, taxes, availability and reward redemption.
Online order history still represents website sale orders, not POS receipts.

## Connector 19.0.1.3.1

Product image URLs now include a stable revision based on the product's native
write date. Unchanged images remain cacheable; edited products receive a new
image URL. Variant images also account for changes to their product template.
There are no added access privileges, model overrides or business-data writes.

Deploy the updated `spx_loyalty_mobile` folder through the existing Cloudpepper
Git repository, restart as required and upgrade the installed addon. Do not
uninstall it. Install the matching updated Android build for automatic refresh.

## Test before moving to the live instance

1. Leave Order open. Publish a test product in Odoo and allow one refresh cycle.
2. Change its name, price and photo. Confirm each update appears without pulling
   down. Unpublish it and confirm it disappears from the menu.
3. Open an item, then unpublish it. Confirm the open sheet disables ordering it.
4. Search the menu and load another catalogue page. Confirm polling preserves
   the search and loaded pages.
5. Complete an eligible POS purchase with the linked test customer. Compare the
   native card balance with the app after its next refresh.
6. Leave the inbox/order-history page open while adding an appropriate test
   message or processing the customer's website order in Odoo.
7. Background and resume the app, then briefly disconnect/reconnect the device.
8. Add or change a cart item during refresh and check the final order in Odoo.

Only connect the approved live origin/database after this joint acceptance
test. Connection identifiers remain developer build settings, never fields in
the customer app.
