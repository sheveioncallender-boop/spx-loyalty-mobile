# Jenny’s iPhone test setup — 0.6.0+12

The iPhone version shares Jenny’s approved Android design and app flow. It uses the same test instance, accounts, cards, products and native POS workflow. An existing customer signs in with the same email and password; installing on another phone does not require another customer or card.

This delivery is a prepared source project. **No signed IPA, TestFlight upload or physical iPhone test has been completed.** The workspace used for preparation runs Linux; an iOS build requires macOS and Xcode. See [Flutter’s official iOS deployment guide](https://docs.flutter.dev/deployment/ios).

## Supported phones

The project targets **iOS 15.0 and later** and is intended for supported iPhones, including iPhone X and newer models. Its layout adapts to screen size and safe areas. Newer hardware is part of the target audience; the iPhone X is the first planned test device.

Check **Settings → General → About → iOS Version** on the test phone. The current [TestFlight app](https://apps.apple.com/us/app/testflight/id899247664) requires **iOS 16.0 or later**, independently of Jenny’s deployment target. Apple lists iPhone X among [iOS 16 compatible devices](https://support.apple.com/en-in/103267). Compatibility must still be confirmed by compiling the project with Xcode and running the app on the phone.

## Choose the installation route

| Available setup | Route |
| --- | --- |
| A Mac with Xcode and an Apple Account | Connect the iPhone and install a development build using an Xcode Personal Team. Apple’s free provisioning profiles expire after seven days, so the app needs periodic reprovisioning. |
| An Apple Developer Program membership and access to a Mac or a configured Mac build service | Sign and upload a beta for TestFlight. This is the preferred route for ongoing testing and sharing with additional testers. |
| A Windows/Linux computer only, with no Mac build service | The source is ready for handoff, but compiling and signing the iPhone build remains blocked until a Mac build environment is available. |

Apple explains the difference between a Personal Team and program membership in [developer account documentation](https://developer.apple.com/help/account/basics/about-your-developer-account). A downloadable source ZIP cannot be installed on an iPhone. Signing details stay in Xcode or the chosen build service.

## Build on a Mac

1. Extract the full source ZIP. Install Xcode and finish its first-run setup, then install Flutter **3.47.4**. Keep the supplied `app/pubspec.lock`; this preparation did not upgrade dependencies. Follow [Flutter’s iOS setup instructions](https://docs.flutter.dev/platform-integration/ios/setup) for required Xcode components and dependency tooling.
2. From the extracted `Jennys-Native` directory, prepare the connected test configuration:

   ```bash
   bash tools/build_ios_test.sh prepare
   open app/ios/Runner.xcworkspace
   ```

3. In Xcode, select **Runner → Signing & Capabilities**, choose your signing **Team**, and keep automatic signing enabled. The current bundle identifier is `net.spxcorp.jennysRewards`. It must be available to the selected team; establish the final publisher-owned identifier before the first distributed build. The supplied entitlements configure the app’s Keychain group.
4. Connect the iPhone, trust the computer, select it as the run destination and follow Xcode’s device setup prompts, including Developer Mode if requested. List the device ID:

   ```bash
   flutter devices
   ```

5. Install and run a release-mode development build, substituting the connected device ID:

   ```bash
   bash tools/build_ios_test.sh device YOUR_DEVICE_ID
   ```

The helper supplies the approved test origin `https://jennys.spxcorp.site` and database `jennys.spxcorp.site`. These are build configuration, with no customer-facing server selector. No passwords, tokens or administrative keys are embedded. The helper does not deploy the connector or submit test orders.

For an iOS simulator build, use `bash tools/build_ios_test.sh simulator`. A simulator `.app` cannot be installed on the physical iPhone. Run the supplied `RunnerTests` through Xcode’s **Product → Test** using an available iOS simulator to compile and exercise the native cookie validation tests.

## TestFlight

Once signing is configured with the appropriate Apple Developer Program team:

```bash
bash tools/build_ios_test.sh ipa
```

The command builds an archive and attempts a signed IPA export. Review the archive and validation results in Xcode before uploading it to the matching App Store Connect app. Complete Apple’s requested app information and beta testing setup, then invite the test Apple Account through TestFlight. External beta distribution may require Apple’s beta review. This script does not upload or send invitations.

The project version is **0.6.0**, build **12**. Increase the build number for subsequent uploads to the same app version as required. Installation and beta distribution follow [Apple’s TestFlight process](https://developer.apple.com/testflight/).

## What was prepared

- Jenny’s native iOS app icon in all 19 configured asset slots, plus the matching navy launch branding.
- Existing first-use introduction and replay option, shared with Android.
- Keychain entitlement for the existing secure saved-login implementation.
- A native WebKit session-cookie bridge for authenticated account pages, with cookie clearing on sign-out.
- Temporary full brightness and disabled screen sleep while showing the scan card. Previous settings are restored when the app loses focus or the card closes.
- Existing `jennys` URL scheme retained. Verification can also finish when the customer returns to the app through its existing account-status flow; automatic launching from every email client is not assumed.
- No new Odoo module version, POS customization, replacement customer records or changes to the existing Android package.

## Validation and first device test

**Completed locally:** static analysis; 37 focused Flutter checks for accounts, refresh, ordering, activity, card animation and onboarding; and three additional Flutter layout checks at 375×812, 393×852 and 430×932 with iPhone safe areas. Plists and opaque icon dimensions were checked. All 39 packaged Odoo files and 25 Android project files match the Android 0.6.0 source baseline.

**Still to run on macOS/iPhone:** Swift compilation, the three native cookie tests, code signing, installation and the following integration checks. Flutter layout checks are not iOS simulator tests.

1. Open a fresh installation: confirm Jenny’s icon, launch screen, introduction, Skip and account entry. Repeat on a newer iPhone or simulator to check the safe areas and keyboard.
2. Sign in with an existing account, close and reopen the app, and confirm the same customer/card and saved session. Use a distinct test email to check signup, verification and automatic continuation after returning to the app. Check the existing duplicate-email prompt.
3. Request password recovery, set a new password and confirm the old password fails on a fresh sign-in. Confirm expired/used links show the intended recovery message.
4. Open **My card**, flip to the barcode, enlarge it and scan it at the test POS. Check brightness restoration when leaving the card, switching apps or locking the phone.
5. Open account pages, then sign out and verify that saved sessions and authenticated web pages are cleared. Confirm the introduction replay still works under **You → Discover the app**.
6. When resuming ordering tests, submit an app order, find the customer/order in the test POS, use the staff-controlled table/kitchen/payment flow and confirm order status and loyalty updates in the app.

Record device model, iOS version and any error screen for the first run. The initial goal is an installed, tested iPhone build of the existing experience; public App Store submission follows after that testing.
