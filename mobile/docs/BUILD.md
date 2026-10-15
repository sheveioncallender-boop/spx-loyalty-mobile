## Current member extras test build — 0.7.0+13

Upgrade connector **19.0.4.0.0** before using the new wallet. Retain the same test application ID and signing certificate. This release uses the existing Flutter/Dart dependencies and Android ARM64 target; Gradle now downloads its smaller binary distribution (same 9.3.1 version). See [MEMBER_EXTRAS_TEST.md](MEMBER_EXTRAS_TEST.md).

The older welcome and iOS preparation notes below describe 0.6.0 only.

## Current welcome test build

Android 0.6.0+12 uses the same toolchain and test certificate below. Configure the same origin/database as the 0.5.2 build. See `FIRST_LAUNCH.md` for the current update. The Odoo connector remains 19.0.3.0.4; this visual update requires no module upgrade.

The iOS project for the same version is prepared separately. See [IOS_TEST_SETUP.md](IOS_TEST_SETUP.md) for signing, direct iPhone installation and TestFlight. Its native account-page session bridge, Keychain configuration and scan-display support are included; they still require a macOS/Xcode build and device testing. No IPA has been built in the Linux workspace.

# Build from source

Toolchain for this update: Flutter 3.47.4 / Dart 3.13.3, Android SDK platforms 35 and 36 (app compile/target SDK 36), Android NDK 28.2.13676358 and Amazon Corretto Java 17.0.20.10.1. Dependency versions are retained in `app/pubspec.lock`. Secure storage remains pinned to 10.3.1.

```bash
cd app
flutter pub get
flutter analyze
flutter test
flutter build apk --release --target-platform android-arm64
```

Output: `app/build/app/outputs/flutter-apk/app-release.apk`. The current release build deliberately uses the standard **test/debug signing configuration** for sideload testing. Create a proper private Play signing/upload configuration before publishing; never commit signing keys or passwords.

Restore the separately preserved test key before subsequent development builds.
Version 0.4.0+7 retains the 0.3.2+5 certificate and supports an in-place update.
Version 0.3.2 uses a new test certificate because the previous temporary key was
removed during workspace maintenance. It requires one fresh installation over
0.3.1; see `TEST_SIGNING.md` for the exact certificate and continuity procedure.

The Android application ID currently is `net.spxcorp.jennys_rewards`. Confirm the permanent publisher-owned ID before registering it in Firebase or Play. The minimum Android SDK is 24 (Android 7.0). This packaged APK targets ARM64; adjust the build targets if a test device uses another architecture.

In a managed CI environment, set `CI=true` to prevent Flutter's optional cloud environment detection. `TAR_OPTIONS=--no-same-owner` is appropriate where archives cannot restore their original Unix file ownership. Neither setting changes the app or accesses cloud instance metadata.

## Deployment configuration (developer only)

The customer never enters an Odoo address or database. Set them at build time:

```bash
flutter build apk --release --target-platform android-arm64 \
  --dart-define=JENNYS_API_URL=https://jennys-test.example \
  --dart-define=JENNYS_DATABASE=your_test_database
```

Replace the example origin/database with the approved deployment. These are connection identifiers, not credentials; never embed a password, session or admin API key. The URL must be a trusted HTTPS origin with no page path, credentials or query.

The **0.4.0+7** test APK uses the user-supplied instance:

```bash
flutter build apk --release --target-platform android-arm64 \
  --dart-define=JENNYS_API_URL=https://jennys.spxcorp.site \
  --dart-define=JENNYS_DATABASE=jennys.spxcorp.site
```

The `/odoo/` backend page path is not part of the configured origin. The default source constants remain empty; use these build arguments to reproduce this connected test build. **Sign in to Jenny’s** connects to the test instance. **Try the preview** continues to use sample data.

A configured build restores saved sessions only when their origin/database match that build. Changing environments requires signing in again. Customer error messages hide technical connection details. Backend class names and administrative installation documentation remain developer-only. Configure Jenny’s existing website branding separately for pages opened during account pages.

## Tests

```bash
cd app
flutter analyze
flutter test
cd ..
python odoo/test_validation.py -v
```

Widget tests cover navigation, a small-screen add/remove flow, loyalty-card rendering, exact barcode payloads, scan/enlarged layouts, manual-entry fallback, refresh on returning to the front or closing the enlarged card, 3D rotation and rapid reversal, reduced-motion behavior and screen snapshots. Code 128 rendering uses [barcode_widget](https://pub.dev/packages/barcode_widget) 2.0.4 with the locked barcode encoder dependency. API unit tests cover HTTPS origin validation, cross-origin/redirect protection and no automatic mutation retry. Native Odoo database tests are inside the addon; run those on the actual test instance separately.

Goldens are generated using the bundled Manrope fonts. Regenerate intentionally after visual changes with `flutter test --update-goldens`, then inspect the PNGs in `app/test/goldens/`. Small pixel differences may occur with a different Flutter engine or operating system.

## Production work still required

Configure Firebase and device push, production authentication/MFA, full account lifecycle/privacy support, native POS/payment/loyalty acceptance tests, release signing, and Play listing assets. iOS requires a macOS/Xcode build environment, signing and native integration/device testing. Do not describe the prepared source as a tested iOS release.

Existing image assets came from the previously approved Jenny’s project. Manrope is bundled with its `OFL.txt`. Confirm production rights and final imagery/content with Jenny’s before store submission.

## Capture the card animation

To render a sequence from the actual Flutter interface, set `JENNYS_CAPTURE_DIR` to a local output folder and run `flutter test --no-pub tool/capture_card_flip.dart` from `app/`. The script captures both turns and their resting faces. The delivered GIF is assembled from these frames; it is not a design mockup. Sample data is used throughout.
