# Jenny’s — Email verification and app return

Android **0.5.2+11** · Odoo connector **19.0.3.0.4** · 14 September 2026

Test instance: **https://jennys.spxcorp.site**. Database: **jennys.spxcorp.site**.

## Latest correction — duplicate signup and password reset

- An existing user email now stops signup in the app and opens **You already have an account**, with **Sign in**, **Forgot password?**, and **Use a different email**. The email stays filled in when moving to sign-in/recovery. No registration or account email is created for that duplicate request.
- **New password-reset links last 24 hours**, replacing the previous one-hour lifetime. Request a fresh reset after upgrading; old expired/used links are not reactivated or extended.
- Requesting another reset still invalidates earlier pending resets. The error now says whether a link was replaced, expired, unavailable or already used and directs the customer specifically to **Forgot password**.
- Successful reset links show **Password already updated** on repetition without changing the password again. A double-click on the form is blocked while saving. A completed reset remains single-use.
- Password mismatch or a short password keeps the customer on the form with a correction message and the same valid token. Password inputs are cleared, never echoed back.
- Reset continues to write the native Odoo user password. The new password replaces the previous hash; native authentication rejects the old password after successful completion. Requesting a reset email alone does not change a password. The customer, card and points remain the same.

The reported expiry screen alone does not identify whether the previous link exceeded one hour, was superseded by another request or had already been submitted. This release separates those cases and tests the full token/form/service boundary locally. Cloudpepper acceptance testing is still required.

## Existing verification and app return

- Opening the verification email completes verification without asking for the signup password again. The page automatically submits an Odoo CSRF-protected form. Its fallback button is **Verify my email**.
- The success page offers **Open Jenny’s** and attempts to open the app on mobile. Email browsers can require a tap on that button.
- If the app is still waiting on verification, switching back to it checks the result and signs in using the signup password held temporarily in memory. **I’ve verified my email** performs the same check manually.
- If Android closed the app in the background, the email’s app link can complete sign-in using a short-lived handoff plus the original device’s securely stored signup receipt. Another device, an expired handoff or a cleared app installation falls back to normal sign-in.
- Forgot password sends a recovery email, accepts a new password and confirmation on Jenny’s page, and returns to the app’s sign-in screen with a success message. Use the new password there.
- Existing native POS ordering, pricing, products, loyalty balances, card animation and the main app design are retained.

## Install in this order

1. Back up the test instance in Cloudpepper.
2. Replace the connector in its **existing Addons entry** using `spx_loyalty_mobile.zip`. Avoid deploying a second copy of the same module.
3. Upgrade **Jenny’s Rewards** (`spx_loyalty_mobile`) in Odoo, or use the existing Cloudpepper module auto-upgrade process. Confirm installed version **19.0.3.0.4**. Restart workers if the deployment process has not reloaded them. This release changes recovery and signup behavior. It adds no new database fields beyond the prior handoff release; still upgrade the module so all workers use the new code.
4. Install **Jennys-Android-0.5.2-arm64.apk** over the current app. It uses the existing test certificate; an uninstall should not be necessary. This is an ARM64 Android test build, minimum Android 7.0.
5. Keep the current outgoing mail server, Jenny’s settings, products, customers, cards and points. Email delivery was confirmed by your test with the previous correction.

Both the new connector and APK are needed for automatic app return. An old APK can still sign in normally but does not handle the new app links.

## Existing signup settings

Under **Jenny’s Rewards → Settings → Customer App**, retain these values:

| Setting | Value |
| --- | --- |
| Enable customer app | Enabled |
| Visible loyalty programs | Your Jenny’s native loyalty program |
| New member loyalty program | The same program intended for new members |
| Account email sender | `no-reply@spxcorp.site` |
| Account link origin | `https://jennys.spxcorp.site` — origin only, without `/odoo/` |
| Policy version | The currently accepted version |
| Account and rewards terms | Your configured policy text |
| Privacy policy | Your configured policy text |
| Enable verified signup | Enabled after completing the settings |

## Test signup and automatic return

1. Sign out of the test app. Choose **Create an account** and use an email you control that does not already have a user in Odoo.
2. Enter first/last name, local phone number after +1 (868), email, a password of at least 12 characters and birthday. City is optional. Marketing choices remain optional and unchecked. Accept the displayed terms/privacy acknowledgement.
3. The app shows **Check your inbox**. Odoo’s **Registrations** menu shows a pending registration. At this stage there is no new user or loyalty card.
4. Open the newest verification email. There is **no password field**. Wait for **Email verified**; tap **Verify my email** only if automatic verification does not continue.
5. Tap **Open Jenny’s** if the browser does not open it automatically. Alternatively, switch back to the app while it is still waiting. It should complete sign-in and show the new native card at zero points, or the preserved balance of a safely matched existing card.
6. In Odoo, confirm the registration is completed and linked to one customer, one portal user and the native loyalty card.
7. Open the verification link again. A completed signup can show success/open the app again; it does not create another user or card. Each sign-in handoff is single-use and expires after ten minutes.
8. Test signup with the same email using different capitalization. There must be no additional user. The app must display the account-exists screen immediately after submission. No new email should be sent for that signup attempt.

If the app was closed entirely, test the **Open Jenny’s** link as well as a normal sign-in. Automatic sign-in after a cold start requires the secure pending receipt saved by this APK. Registrations started on an older APK or another device may need normal sign-in.

## Email is the customer account identifier

The connector normalizes submitted email addresses and checks both native login and customer email, including Odoo’s normalized email field. Checks include inactive users and accounts with a different login name. Account creation repeats the check while holding a lock for that email, preventing competing app signups from creating duplicate users.

A matching existing user is kept and the app offers sign-in/recovery without sending an account email. Email sign-in resolves that existing user’s actual Odoo login and uses native password authentication, so an alternate login name does not require a duplicate account. A single suitable existing customer contact can be reused with its existing loyalty card and points. Multiple matching contacts or users require staff review. This signup protection applies to the connector; existing native Odoo duplicates are not automatically merged or deleted.

## Test forgot password

1. Sign out and choose **Forgot password?**.
2. Enter the email of the verified customer and press **Send reset link**. The inbox message does not reveal whether an arbitrary email has an account.
3. Open the latest recovery email. Enter and confirm a new password of at least 12 characters. Press **Save new password**.
4. Check **Password updated**, then use **Open Jenny’s**. The app should show confirmation above its sign-in form.
5. Sign in using the new password. Confirm the same customer, card and points remain.
6. Sign out and check that the old password fails. A used reset link must show Password already updated and must not change the password again. Requesting another reset invalidates the earlier pending reset link; opening the old email should explain that a newer reset was requested. Resetting a password also invalidates outstanding signup sign-in handoffs for that user.

Verification links expire after 24 hours; new recovery links also expire after 24 hours. Resend has a one-minute cooldown and replaces the previous verification token. Use the newest email. Repeated account requests are limited; allow an hour if testing reaches the limit.

## Email and form troubleshooting

The earlier **Message write / User 2** correction remains included. Account emails are created under Odoo’s system user, linked to their registration and sent with native post-commit delivery. Administrators can maintain linked messages while registration records stay read-only.

The reported **This request is unavailable** came from the connector’s origin check. A page using `Referrer-Policy: no-referrer` can submit a browser form with `Origin: null`. The correction accepts that specific case only on the HTTP account forms, where Odoo has already checked the session-bound CSRF token. JSON routes still reject a null or unrelated browser origin. See [MDN’s description of this browser behavior](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Referrer-Policy#effect_on_the_origin_header).

For another delivery failure, inspect **Settings → Technical → Email → Emails → Failure Reason**. It may describe an SMTP rejection or an Odoo error. Successful outgoing account mail is automatically deleted from the queue; a disappearing row alone is not proof of inbox delivery.

The earlier recovery for missing signup columns remains included. If an upgrade is blocked, collect the latest traceback and first module-upgrade error. Do not uninstall the module or add individual database columns manually. The native upgrade arguments are `-d jennys.spxcorp.site -u spx_loyalty_mobile --stop-after-init`, used with the instance’s real Odoo executable/configuration by its operator.

## Authentication implementation and validation

- The app link contains only a random ten-minute sign-in code. It contains no password, email address or session cookie. The exchange also needs the secret receipt from the app installation that started signup. Server-side values are stored as hashes and consumed under a row lock.
- The exchange uses Odoo’s credential extension and native session authentication/rotation. It accepts only an active, verified portal account and retains native MFA handling. It cannot grant staff permissions.
- For switching back to an app still on its signup screen, the original signup password is held only in memory and passed through normal native password authentication after verification. It is cleared on completion or leaving the account flow. Passwords are not saved to device storage.
- The device receipt and authenticated session use secure storage and are bound to the configured origin/database. The pending server password hash is cleared after account creation.
- The app persists a session only after the connector accepts its authenticated bootstrap request.

Completed locally: **31 focused Flutter tests**, static analysis, **29 Python controller/service/ORM checks**, and **7 JavaScript form-flow checks**. The Python checks simulate database records; the password-recovery regression runs Odoo’s actual password setter, hashing context and credential checker against simulated password rows. The JavaScript checks simulate browser events. They cover origin handling, native CSRF dispatch, missing/expired links, receipt binding, wrong-device/wrong-user rejection, single-use grants, signup data, resume sign-in, reset return, 24-hour expiry, duplicate signup without email, new-password acceptance, old-password rejection, session storage and existing order/card behavior.

Native database tests are included in `odoo/spx_loyalty_mobile/tests/test_onboarding.py` for actual account/card creation, email uniqueness, password preservation/reset and handoff consumption. They have **not been executed against a running Odoo database here**. The Cloudpepper upgrade, mobile email-browser launch and full device-to-instance flow still need your acceptance test. iOS link configuration is included in source, but an iOS build/device test requires macOS/Xcode and signing.

The current APK is for sideload testing using the existing test certificate. Production store signing/publishing remains a later stage. The full HTML restaurant website also remains a later stage.
