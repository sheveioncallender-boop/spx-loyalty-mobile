# Jenny’s — Signup and login test build

Android **0.5.0+9** · Odoo connector **19.0.3.0.1** · 13 September 2026

This update implements the approved account screens in the app and adds verified registration and password recovery to the connector. It is for the existing test instance, **https://jennys.spxcorp.site**, database **jennys.spxcorp.site**. The HTML restaurant website remains the next stage.

## Recovery when Apps is blocked by a missing signup column

The reported error is `column res_users.spx_mobile_verified_email does not exist`. The loaded code expects a column that is absent in the database used by that request. A successful file deployment does not, by itself, establish that this module's database upgrade completed. The supplied traceback is timestamped **13 September 2026, 21:01:26 GMT**; use a newly triggered error when checking recovery.

Connector **19.0.3.0.1** loads signup-only user, contact and website fields on explicit request, excluding them from ordinary native record prefetch. This addresses the reported failure path when opening native actions before the database upgrade. It does not create columns on application requests or bypass email verification. Signup still requires a successful native Odoo module upgrade.

1. Take a Cloudpepper backup of this test instance.
2. Replace the connector in its **existing Addons entry** with the new `spx_loyalty_mobile.zip` contents. Use the existing repository/upload update method; avoid deploying a second copy of the same module.
3. For a Git repository, enable Cloudpepper **Auto-upgrade** for that connector repository and run its update. Cloudpepper documents this as upgrading installed modules when their manifest versions increase: https://cloudpepper.io/updates/2025/01/auto-upgrade-odoo-modules/.
4. Restart the Jenny's instance after deployment so its workers load the corrected field definitions. Reopen `/odoo/` and go to **Apps**. If Cloudpepper has not performed the actual module upgrade, upgrade **Jenny's Rewards** (`spx_loyalty_mobile`) here. Complete this before opening signup settings or testing the app's account features.
5. Confirm that Apps and Jenny's Rewards settings open without an error. Then continue the signup configuration below. The existing Android **0.5.0+9** APK works with this connector; no APK replacement is needed for this recovery.

If Apps remains blocked, obtain the **new traceback** and the **first error from the module-upgrade job**. The server-side alternative is an Odoo invocation with these arguments:

```text
-d jennys.spxcorp.site -u spx_loyalty_mobile --stop-after-init
```

These are arguments, not a complete shell command. They must be used with this instance's actual Odoo executable, Python environment, configuration and addons paths, while its normal workers are stopped. Those server details have not been supplied; do not substitute guessed paths. Restart the instance after a successful upgrade. Keep the installed module and its records; do not repair this by manually adding individual columns.

Recovery validation: six database-free regression tests use the actual Odoo 19 ORM field-selection methods with a simulated old schema. The native user/contact/website reads failed before the patch and pass after it. Explicit signup reads still require migrated columns. A running PostgreSQL upgrade and Cloudpepper recovery have **not** been executed from this workspace.

## Install in this order

1. Deploy the updated `spx_loyalty_mobile` folder from the module ZIP through the same Cloudpepper Git/addons process used previously.
2. In Odoo, go to **Apps**, find **Jenny’s Rewards**, and **Upgrade** the module. A code deployment or service restart alone does not create the new database columns. Upgrade before opening the new settings or testing signup.
3. Open **Jenny’s Rewards → Settings**, select the website used by the app, and open its **Customer App** tab.
4. Complete the settings below and save.
5. Install `Jennys-Android-0.5.0-arm64.apk` over the current test app. It has the same test signing certificate as 0.4.1, so an uninstall should not be needed.
6. If you are already signed in, sign out to see **Create an account** and **Sign in**.

Do not uninstall the Odoo module. Preserve existing website/POS settings, products, customers, cards and points.

## Signup settings

| Setting | Value for this test instance |
| --- | --- |
| Enable customer app | Keep enabled. |
| Visible loyalty programs | Keep your current Jenny’s loyalty program selected. |
| New member loyalty program | Choose that same native loyalty program. This determines which card new members receive. |
| Account email sender | `no-reply@spxcorp.site` — matches the outgoing server shown in your screenshot. |
| Account link origin | `https://jennys.spxcorp.site` — do not add `/odoo/` or another path. |
| Policy version | For example, `test-1` during testing; change when the accepted policy changes. |
| Account and rewards terms | Enter the policy text displayed to the customer. |
| Privacy policy | Enter the privacy text displayed to the customer. |
| Enable verified signup | Enable after completing the above. |

For a private test with your own test accounts, clearly labelled test policy text can be used. Use Jenny’s approved terms and privacy copy before inviting customers. Policies are shown as text in the app. Nothing is copied from KFC.

The sender uses your existing outgoing mail server. Your screenshot confirms the connection test; actual message delivery still needs to be tested. Account emails are transactional and do not require marketing opt-in.

## Test the complete journey

1. Choose **Create an account**. Use a fresh email address you control and can receive mail at. Enter first/last name, a seven-digit local phone number after +1 (868), email, a password of at least 12 characters and birthday. City is optional. Email and SMS marketing are separate optional choices, unchecked by default.
2. Open the policy links, accept the terms/privacy acknowledgement, and submit.
3. The app shows **Check your inbox**. In Odoo, **Jenny’s Rewards → Registrations** shows the pending signup. A pending signup is not yet a user and cannot sign in.
4. Open the Jenny’s verification email. The email link opens a branded confirmation page; enter the password you chose during signup and press **Verify my email** there. This binds verification to your signup and prevents ordinary email-link scanners from activating an account just by opening the URL.
5. Return to the app and sign in using the email/password you entered. The normal app loads with the native loyalty card and zero points for a new card.
6. In Odoo, inspect the completed registration, linked customer, portal user and loyalty card. The contact’s **Jenny’s Membership** tab shows verification, birthday and signup preferences.
7. Test **Forgot password**. Open the email, enter and confirm a new password on the Jenny’s page, and sign in with it. Confirm that the old password no longer works.
8. Under **You → Communication preferences**, check that email and text preferences can be changed. SMS consent is stored; this update does not send SMS.

Verification links expire after 24 hours. Password-reset links expire after one hour. Used links cannot be reused. Verification resend is available after a one-minute cooldown; it rotates the link, so use the newest email. If signup expires or the app was closed before you verified, submit signup again to request a fresh link. Repeated completed signups do not overwrite an existing account.

Existing members should sign in with their current account. This upgrade preserves access for portal accounts that existed before the upgrade. That is a compatibility allowance, not a claim that those historical email addresses were verified by the new process. New accounts created outside the verified app flow cannot bypass verification to access app data.

If exactly one suitable existing customer contact matches the verified email, registration can link to that contact and preserve its existing card and balance. Ambiguous contact matches, internal users, inactive contacts/cards and unsuitable company records require staff help; the module does not merge them automatically.

## If the email does not arrive

- Check junk/spam, then **Settings → Technical → Email → Emails** in developer mode.
- A message still in **Outgoing** is waiting for the mail queue. For the email addressed to your own test account, use Odoo’s normal **Send Now** action to test delivery or allow the scheduled mail queue to process it.
- A failed message’s error explains the SMTP problem. The configured From address must be accepted by the server.
- Confirm the account-link origin matches this test domain. Registration, verification and recovery must use the same website.
- The account service has rate limits: up to eight signup/recovery attempts per email per hour and forty account requests per IP per hour. A shared store network may reach the IP limit during repeated testing. Allow an hour before further attempts when the limit is reached.

The app does not store customer passwords. Pending registration contains an Odoo-compatible password hash; it is removed when completed or cleaned up after expiry. Verification activates a portal user, with no staff/backend permissions. Staff keep the normal POS, table, preparation, payment and loyalty workflow.

## Validation and remaining checks

Completed locally:

- Flutter static analysis and Android release compilation.
- 21 focused Flutter tests covering signup, recovery, required fields, optional marketing choices, card animation, recent activity, order submission/status and automatic refresh.
- Signup screen rendering with the actual app theme.
- Connector import against the pinned Odoo 19 source and account input validation.
- Python syntax and Odoo XML data-schema checks.
- Six Odoo ORM field-selection regression tests for the 19.0.3.0.1 recovery patch (`tools/test_onboarding_prefetch.py` in the source ZIP); the database fetch is simulated.
- APK signature verification and version/package checks. Package: `net.spxcorp.jennys_rewards`; version code 9; ARM64; Android 7 or newer.

**Not yet completed:** installation/migration and transactional signup tests in a running Odoo database, actual verification/reset email delivery, and end-to-end checks on your Android device. The local environment could not start PostgreSQL. Do not treat this package as production validated.

The connector includes database tests in `tests/test_onboarding.py` for pending access, native user/card creation, duplicate/replayed/expired links, matching existing cards, password reset, policy validation and access control. A developer can run them on an isolated Odoo test database with the required native modules installed:

```bash
odoo-bin -d YOUR_ISOLATED_TEST_DATABASE -u spx_loyalty_mobile \
  --test-enable --test-tags /spx_loyalty_mobile:TestMobileOnboarding --stop-after-init
```

Use a database copy for automated tests. The regular manual test steps above are for the existing Jenny’s test instance. This package does not deploy to or change that instance by itself.
