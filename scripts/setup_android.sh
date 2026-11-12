#!/usr/bin/env bash
# Jalankan dari folder mobile/ : membuat folder android/ dan mengizinkan INTERNET
# serta HTTP lokal (khusus pengembangan; produksi wajib HTTPS).
set -euo pipefail
flutter create . --platforms=android --project-name triaseku
M=android/app/src/main/AndroidManifest.xml
if ! grep -q "usesCleartextTraffic" "$M"; then
  sed -i 's#<application#<uses-permission android:name="android.permission.INTERNET"/>\n    <application android:usesCleartextTraffic="true"#' "$M"
fi
flutter pub get
