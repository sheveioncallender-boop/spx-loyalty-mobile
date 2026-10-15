> This activity-screen behavior is retained in 0.4.0. The current companion version is 19.0.2.0.0; the version references below record when the activity screen was introduced.

# Recent activity — Android 0.3.3+6

Open You → Recent activity, or My card → Recent activity below the scan controls.
The screen uses Jenny’s existing navy/blue/gold colours, Manrope typography,
rounded surfaces and a smooth expansion animation with reduced-motion support.

## Customer display

- Current points balance comes directly from the selected native loyalty card.
- Card issued is the card record’s create date, not the customer’s birthday or
  membership anniversary. A cash spending value is not inferred from points.
- All / Earned / Used filters apply to the selected card’s recent history.
- Dates group entries by month, newest first. Timestamps are displayed in the
  device’s local timezone; Odoo’s unzoned create_date values are interpreted as UTC.
- Tap an entry for its native description/reference and net points movement.
  Both issued and used amounts are shown if a record contains both. Negative
  amounts are shown as adjustments, preserving their actual signs.
- Expansion and filter state survive the normal 15-second foreground refresh.
  The page reads the app’s existing refreshed snapshot, without a second timer.
- Multiple eligible cards have a selector. Records are filtered to the selected
  native card ID. Missing or removed cards display a clear empty state.

## Data scope and limits

The existing authenticated bootstrap already returns native loyalty.history
id, card_id, description, issued, used and create_date. No connector upgrade is
needed specifically for this screen; the packaged companion remains 19.0.1.3.1.

Bootstrap supplies at most 40 recent history records across the eligible cards.
This screen shows recent activity, not a full lifetime statement. The native
card balance is authoritative and is never reconstructed from these 40 records.

The available schema has no separate expiry/refund event-type field. The UI
shows recorded amounts and descriptions; it does not invent expired-points
entries, expiry dates, a monetary value, or a running transaction balance.
Existing native POS/eCommerce rules determine what history gets recorded.

## Device check

1. Sign in with the linked test customer. Open Recent activity.
2. Complete an eligible native POS purchase, then compare the exact native card
   history with the app after its next refresh.
3. Test a redemption and, if enabled, a native adjustment/refund. Compare both
   the displayed movements and current balance with Odoo.
4. Expand an entry, leave the page open and confirm new history arrives.
5. Check the earned/used filters, local time and a second card if available.

The APK updates 0.3.2 in place using the retained test key. Devices still on
0.3.1 require removal of that older Android app and a new sign-in; server-side
records remain intact. See TEST_SIGNING.md.

Preview PNGs use sample data rendered by the actual Flutter widgets. They are
not screenshots of the customer’s live loyalty account. Reproduce them with
JENNYS_CAPTURE_DIR=/absolute/output flutter test --no-pub tool/capture_recent_activity.dart.
