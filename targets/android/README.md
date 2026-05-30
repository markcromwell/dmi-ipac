# DMI WCAC — Android App

Native Android client (Kotlin + Jetpack Compose) for the WCAC heat exchanger
calculator. The proprietary calculation engine runs **server-side** via the
REST API (`targets/api`); this app only collects inputs and renders results,
so the IP is never shipped in the APK.

## Structure

```
app/src/main/
├── AndroidManifest.xml          INTERNET permission, launcher activity
├── java/com/dmimfg/wcac/
│   ├── MainActivity.kt          Compose UI (form + results)
│   └── WcacApi.kt               REST client (calculate, models)
└── res/values/                  strings, theme
app/build.gradle.kts             dependencies (Compose, serialization, coroutines)
```

## Build

1. Open `targets/android` in Android Studio (Hedgehog or newer), or build from CLI:
   ```
   ./gradlew :app:assembleDebug
   ```
2. Set the API endpoint in `WcacApi.kt`:
   ```kotlin
   var BASE_URL = "https://your-wcac-api.example.com"
   ```
   - Emulator → local server: `http://10.0.2.2:8000`
   - Physical device on LAN: `http://<host-ip>:8000`
   (For plain-HTTP testing, set `android:usesCleartextTraffic="true"` in the
   manifest; use HTTPS in production.)
3. Install: `./gradlew :app:installDebug`

## How it works

- `WcacApi.calculate(inputs)` POSTs to `/calculate`; the API validates,
  computes server-side with the `wcac` library, and returns `{result, warnings}`.
- Validation errors return HTTP 422 with field-level messages, shown to the user.
- Warnings (out-of-range correlations) are surfaced but do not block.

## Why server-side

The Bell-Delaware / Wcool 2.03 correlations and the iterative solver are 50
years of DMI engineering IP. Keeping them behind the API means the same engine
serves web, desktop, CLI, and mobile, and the math never leaves the server.
