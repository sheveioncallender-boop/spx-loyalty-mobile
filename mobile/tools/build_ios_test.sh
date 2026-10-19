#!/usr/bin/env bash
set -euo pipefail

# The test origin is public configuration; signing credentials stay in Xcode.
if [[ "$(uname -s)" != "Darwin" ]]; then
  printf '%s\n' 'This step requires macOS with Xcode. No iOS binary has been built.' >&2
  exit 2
fi
command -v flutter >/dev/null || { printf '%s\n' 'Install Flutter 3.47.4 and add it to PATH.' >&2; exit 2; }
command -v xcodebuild >/dev/null || { printf '%s\n' 'Install and select Xcode first.' >&2; exit 2; }

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir/../app"
mode="${1:-prepare}"
case "$mode" in
  prepare|simulator|device|ipa) ;;
  *) printf '%s\n' 'Usage: build_ios_test.sh prepare|simulator|device <device-id>|ipa' >&2; exit 2 ;;
esac
flutter pub get
defines=(
  --dart-define=JENNYS_API_URL=https://jennysontheboulevard.spxcorp.site
  --dart-define=JENNYS_DATABASE=jennysontheboulevard.spxcorp.site
)

case "$mode" in
  prepare)
    flutter build ios --debug --config-only --no-codesign "${defines[@]}"
    printf '%s\n' 'Open app/ios/Runner.xcworkspace in Xcode and choose your signing Team for Runner.'
    ;;
  simulator)
    flutter build ios --simulator --debug "${defines[@]}"
    printf '%s\n' 'Simulator app: app/build/ios/iphonesimulator/Runner.app. This is not an iPhone install file.'
    ;;
  device)
    device_id="${2:?Pass the connected iPhone ID shown by flutter devices.}"
    flutter run --release -d "$device_id" "${defines[@]}"
    ;;
  ipa)
    # Uses the Team selected in Xcode. No upload, distribution or invitation is performed.
    flutter build ipa --release "${defines[@]}"
    printf '%s\n' 'Review the signed archive in Xcode and distribute to TestFlight when ready.'
    ;;
esac
