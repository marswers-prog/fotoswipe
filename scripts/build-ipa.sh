#!/bin/bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

if [[ "$(uname -s)" != "Darwin" ]] || ! command -v xcodebuild >/dev/null 2>&1; then
  echo "Dieser Build benötigt macOS mit Xcode. Nutze den vorbereiteten GitHub-Actions-Workflow." >&2
  exit 1
fi

mkdir -p build dist
xcodebuild \
  -project FotoSwipe.xcodeproj \
  -scheme FotoSwipe \
  -configuration Release \
  -sdk iphoneos \
  -destination 'generic/platform=iOS' \
  -derivedDataPath build/DerivedData \
  CODE_SIGNING_ALLOWED=NO \
  CODE_SIGNING_REQUIRED=NO \
  CODE_SIGN_IDENTITY= \
  DEVELOPMENT_TEAM= \
  build 2>&1 | tee build/xcodebuild.log

python3 scripts/package_ipa.py \
  build/DerivedData/Build/Products/Release-iphoneos/FotoSwipe.app \
  dist/FotoSwipe.ipa

echo 'Erstellt: dist/FotoSwipe.ipa – zur persönlichen Signierung mit AltStore Classic.'
