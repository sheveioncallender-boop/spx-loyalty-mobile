# Jenny’s 0.6.0 — photographs and first-use introduction

Android version 0.6.0, build 12. ARM64 test APK, configured for the existing Jenny’s test instance. Connector 19.0.3.0.4 remains unchanged; no Odoo installation or upgrade is needed for this release.

## What customers see

The brief native launch screen uses Jenny’s logo and navy background. While the saved account is being restored, Flutter continues that branding without an artificial delay. New customers then see four welcome pages:

1. **A little Jenny’s. Always with you.** — the digital loyalty card.
2. **Every visit. A little more.** — collecting points and discovering rewards.
3. **Order here. Enjoy it there.** — dine-in ordering, with payment handled by the restaurant team.
4. **Your visits. All together.** — order status, points activity and messages.

Customers can swipe, use Next, skip to the account welcome page, sign in immediately, or choose Create my account on the last page. Completion and skipping are remembered on that installation. Existing signed-in members continue directly into their account. **You → Discover the app** replays all four pages without signing out. In replay, Close and Back to Jenny’s return to the existing account.

This tour presents features only. It does not show a fabricated balance, reward threshold, customer card number or order. Odoo continues to supply actual account data and business rules.

The first-use preference is separate from account/session storage: Android SharedPreferences and iOS UserDefaults. Updating the app retains the preference; logging out does not reset it. Android backup is disabled in the existing manifest. Clean-install behaviour on iOS still needs device testing alongside that platform’s session/keychain behaviour.

## Photographs

| Supplied image | App placement |
| --- | --- |
| Jennys App Image 1.jpeg — front elevation | Card introduction, account welcome, restaurant section under You |
| Jennys App Image 2.jpeg — angled evening view | Rewards and activity introductions, Home feature |

The actual supplied image bytes are bundled in the app. Layouts crop them to fit their presentation; the restaurant section shows the full front photograph. Existing food photography remains on the ordering introduction. The main navigation and business flows retain their established design.

## Test on your phone

1. Install `Jennys-Android-0.6.0-arm64.apk` over 0.5.2. The package name and test certificate are the same. You do not need to uninstall or clear your account.
2. If already signed in, confirm Home opens normally and the new evening photograph appears further down the page.
3. Open **You → Discover the app**. Swipe through all four pages, try Next and the page indicators, then return with Close or Back to Jenny’s.
4. Reopen the app and confirm the tour does not interrupt your account. Check the full front photograph under You.
5. For a true first-install test, use a spare Android device or separate test profile with no previous installation. Confirm the tour appears, Skip leads to account entry, and closing/reopening remembers that choice. There is no need to erase data on your main test device.
6. From a new installation, test Sign in and Create my account. Continue the existing email-verification and password-recovery checks, including returning to the app from email.
7. Increase the phone’s text size and enable reduced animations. The tour content can scroll vertically where needed, while the main action remains accessible. Confirm status/navigation-bar contrast when entering or leaving the tour.

## Validation for this release

- Flutter analyzer passed.
- 37 focused Flutter tests passed across account entry/API, automatic refresh, dine-in ordering, activity, card animation and the introduction.
- Introduction tests cover first-use/Skip persistence, restored-account entry, replay without losing the account, swipe/Next/signup, immediate sign-in, native preference calls, and a 320×640 layout with 200% text and reduced motion.
- Four preview PNGs were rendered from the actual Flutter introduction with bundled fonts and images and visually inspected.
- Android release APK built for ARM64 using the existing test configuration. Package metadata, signature continuity and bundled photo bytes were checked.
- No live orders, account changes or backend deployments were performed for this visual update. Physical-device checks are still required. iOS source is included, but no iOS binary was built or tested on Xcode.

Reproduce the focused tests from `app/`:

```bash
flutter analyze --no-pub
flutter test --no-pub test/account_access_test.dart test/account_api_test.dart test/automatic_refresh_test.dart test/dine_in_test.dart test/recent_activity_test.dart test/card_flip_test.dart test/app_intro_test.dart
```

Generate the actual welcome previews:

```bash
JENNYS_CAPTURE_DIR=/absolute/output flutter test --no-pub tool/capture_app_intro.dart
```

The native splash and the optional feature tour are separate. The tour is not a store-publication requirement, and this sideload test build is not a store-ready release. See the [Android splash-screen guidance](https://developer.android.com/develop/ui/views/launch/splash-screen) for the native launch behaviour, and `BUILD.md` for toolchain and release-signing notes.
