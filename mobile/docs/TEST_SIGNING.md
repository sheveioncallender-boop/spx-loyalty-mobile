> Update 0.4.0+7 retains the same test certificate as 0.3.2+5 and 0.3.3+6. It can update either in place.

# Android test-signing continuity

The temporary signing key used for Android 0.3.1+4 was removed during workspace
maintenance and was not present in the saved source archive. It could not be
recovered. Android 0.3.2+5 therefore uses a new test certificate.

Android 0.3.3+6 retains the same certificate as 0.3.2+5 and can update it in
place, preserving local sign-in storage.

To install 0.3.2 or 0.3.3 over 0.3.1, remove the earlier Jenny's
test app, install the new APK and sign in again. Android cannot accept this as
an in-place update because the signing certificates differ. This removes local
app/session storage; it does not delete customers, products, cards or points
stored in Odoo.

New test certificate SHA-256:

`0ee55af36b3c0a84442078f7dc58a3e33b660b69a06a8a72e520548c1af33d8f`

The test key is retained separately in `Jennys-Android-Test-Signing.zip`. Restore
its `debug.keystore` to the standard Android user debug-keystore location before
future test builds, or configure an explicit developer test-signing location.
Keep this key out of source repositories, APK assets and customer-facing files.
The archive's README contains the standard development-keystore parameters.

Subsequent test APKs should retain this certificate and increase the Android
version code so they can update 0.3.2 in place. Store releases require a separate
publisher-owned production/upload signing configuration. This is a development
certificate and must not be described as production signing.
