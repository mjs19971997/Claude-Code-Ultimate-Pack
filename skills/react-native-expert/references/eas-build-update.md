# EAS Build, Submit and Update

Build profiles in `eas.json`, app versioning, store submission, over-the-air updates with channels and runtime versions, rollouts and rollbacks, environment variables, and CI. Verified against eas-cli 27.2.x, expo-updates 58.0.x and Expo SDK 58 (2026-10).

## Contents

1. [eas.json profiles](#1-easjson-profiles)
2. [App versions](#2-app-versions)
3. [EAS Submit](#3-eas-submit)
4. [EAS Update basics](#4-eas-update-basics)
5. [Runtime version policies](#5-runtime-version-policies)
6. [Rollouts and rollbacks](#6-rollouts-and-rollbacks)
7. [Environment variables](#7-environment-variables)
8. [CI example](#8-ci-example)
9. [Release checklist](#9-release-checklist)

## 1. eas.json profiles

```json
{
  "cli": { "appVersionSource": "remote" },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal",
      "environment": "development",
      "channel": "development",
      "ios": { "simulator": true }
    },
    "preview": {
      "distribution": "internal",
      "environment": "preview",
      "channel": "preview"
    },
    "production": {
      "environment": "production",
      "channel": "production",
      "autoIncrement": true
    }
  },
  "submit": {
    "production": {
      "ios": { "ascAppId": "1234567890" },
      "android": { "track": "internal" }
    }
  }
}
```

- `developmentClient: true` produces a development build; `distribution: "internal"` creates installable builds for testers (ad hoc on iOS, APK or AAB on Android) without a store.
- `environment` selects which EAS environment (`development`, `preview` or `production`) supplies variables to the build. Without it, EAS applies defaults based on the profile; set it explicitly.
- `channel` ties the build to an EAS Update channel. `eas update:configure` sets it for `preview` and `production` profiles if you use those names.
- A profile can `extends` another to share settings; `env` holds non-secret plain values for the build.
- Build commands: `eas build --profile preview --platform all`, `eas build --profile production --platform ios --auto-submit`.
- Resource classes (`ios.resourceClass`, `android.resourceClass`) and the build `image` control the worker; check the EAS Build docs for the current options and plan limits.
- Keep `eas.json` free of secrets. Use EAS environment variables for build-time values.

## 2. App versions

- `version` in app config is the user-facing version. `ios.buildNumber` and `android.versionCode` must increase on every store upload.
- With `cli.appVersionSource: "remote"`, EAS stores the build number and version code and `autoIncrement: true` on a profile bumps them for each build. `autoIncrement` does not manage `version`.
- With `appVersionSource: "local"`, EAS reads the values from the project and does not write to it; local `autoIncrement` is also supported.
- Inspect or change the stored remote values with `eas build:version:get`, `eas build:version:set` and `eas build:version:sync`; answer yes when `eas build` offers to set the version source to remote.

## 3. EAS Submit

```bash
eas submit --platform ios --profile production --latest
eas submit --platform android --profile production
eas build --platform all --profile production --auto-submit
```

- iOS needs an App Store Connect app (`ascAppId` in the submit profile for non-interactive runs) and an API key; EAS can manage the key. It runs on Linux and Windows too.
- Android needs a Google service account key with Play Console access and an app that already exists in Play Console. The first submission goes to the internal testing track by default; `releaseStatus: "draft"` uploads without rolling out.
- Non-interactive submission (`--non-interactive`) cannot prompt for credentials; configure them first, and give CI an `EXPO_TOKEN`.
- Submit a build that was made from the same commit you tested; do not rebuild between preview approval and submission.

## 4. EAS Update basics

Setup:

```bash
npx expo install expo-updates
eas update:configure
```

This adds `runtimeVersion` and `updates.url` to app config and the `extra.eas.projectId` field, and sets the `channel` on `preview` and `production` build profiles. Rebuild the binary afterwards; the update client is native code.

Publish:

```bash
eas update --channel preview --environment preview --message "Fix cart total rounding"
```

- On SDK 55 and later `--environment` is required for `eas update`; the CLI prompts for it in interactive mode.
- Non-interactive runs need `--message` with `--channel` or `--branch`, or `--auto` (uses the git branch and commit message).
- The bundle is built on the machine that runs the command, so `EXPO_PUBLIC_` values come from the local `.env` files plus the chosen EAS environment. Anything inlined is public.
- Channels point builds at branches: a build with `channel: "production"` receives updates published to the branch linked to that channel. `eas update --channel X` publishes to the branch with the same name by default.
- Promote the exact bundle you tested: `eas update:republish --destination-channel production`. This works well when staging and production use identical environment variables and code signing.
- Inspect with `eas update:list`, `eas update:view`, `eas channel:view`; delete with `eas update:delete`.
- Hermes bytecode produced by `eas update` and `npx expo export` is specific to the Hermes version in the binary; a React Native upgrade needs a new runtime version.
- Error recovery: if an update crashes at launch, `expo-updates` can fall back to the previous working update or the embedded bundle; do not rely on it as a substitute for staged rollout.
- Code signing for updates exists; check the current EAS Update docs before enabling and keep private keys out of the repository.

## 5. Runtime version policies

A build only loads updates whose `runtimeVersion` equals its own. Set it in app config as a string or a policy; platform-specific values under `ios` or `android` override the top-level one.

```json
{
  "expo": {
    "runtimeVersion": { "policy": "fingerprint" }
  }
}
```

| Policy | Runtime version is | Use when |
|---|---|---|
| `"appVersion"` | the `version` field (for example `1.4.0`) | Each store release has a unique version and the team bumps it reliably; the default from `eas update:configure` |
| `"nativeVersion"` | `version` plus `buildNumber` / `versionCode` | Every uploaded build must be its own runtime; native numbers are managed carefully |
| `"fingerprint"` | a hash from `@expo/fingerprint` over everything that affects native code, including SDK upgrades and native dependencies | The team wants incompatible updates to be unlikely without manual bumps; costs more builds |
| manual string | exactly what you write | Full control; you must bump it whenever native code changes |

- Any native change (new native library, config plugin change, SDK or React Native upgrade, permissions) requires a new binary and a new runtime version.
- With `appVersion`, forgetting to bump `version` after native changes sends incompatible JavaScript to old binaries.
- Run `npx expo-doctor` and, with the fingerprint policy, compare fingerprints in CI (`npx fingerprint` / `@expo/fingerprint`) to detect native drift in a pull request.

## 6. Rollouts and rollbacks

Per-update rollout:

```bash
eas update --channel production --environment production --message "Speed up search" --rollout-percentage 10
eas update:edit                      # change the percentage, or finish at 100
eas update:revert-update-rollout     # discard the rollout, restore the control update
```

- Only one rollout can be in progress per branch, platform and runtime version, and a new rollout cannot replace an active one. Publishing a non-rollout fix while one is active needs `--force-end-active-rollout` (EAS CLI 24.9.0 or later).
- Branch-based rollout: `eas channel:rollout` moves a percentage of channel traffic to another branch; only one branch can be rolled out per channel, and `eas update --channel` cannot be used during it (publish with `--branch`).
- Rollbacks:

```bash
eas update:rollback                         # republish a previous update to the same channel
eas update:roll-back-to-embedded            # send clients back to the bundle inside the binary
```

- Watch crash and error rates for the update on the EAS dashboard before raising the percentage.
- A rollback restores JavaScript only. If the bad change was native, ship a fixed binary.
- Users receive updates according to the app's update behavior (default: checked on launch, applied on the next launch); design UI for "update ready" states if immediate application matters.

## 7. Environment variables

- EAS environments: `development`, `preview`, `production` (custom names depend on the plan). Variables are project-wide or account-wide and have visibility `plaintext`, `sensitive` or `secret`.
- Create and pull: `eas env:set --name EXPO_PUBLIC_API_URL --value https://api.example.com --environment production --visibility plaintext`, and `eas env:pull --environment production` (writes `.env.local`; secret variables cannot be pulled).
- Use secret visibility for values consumed by the build process itself (for example a private npm registry token). It gives no protection to anything the app code reads, because that value ends up in the bundle.
- `EXPO_PUBLIC_*` variables are inlined into JavaScript by Metro. Never put credentials there. A backend holds the real secrets and the app calls it with the user's session token.
- In SDK 58 and later, Expo commands load only the standard `.env` files for their mode (`.env`, `.env.local`, `.env.development`, `.env.production` and the `.local` variants) and set `NODE_ENV` themselves; non-standard names like `.env.staging` are no longer loaded. Use `eas env:pull` to switch environments.
- Never commit `.env.local`; commit a `.env.example` with names only.

## 8. CI example

A workflow that type-checks, then publishes a preview update on pushes to `main`. The token comes from a repository secret and no untrusted event data is interpolated into shell commands.

```yaml
name: preview-update
on:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v7
        with:
          node-version: 22
          cache: npm
      - uses: expo/expo-github-action@v8
        with:
          eas-version: latest
          token: ${{ secrets.EXPO_TOKEN }}
      - run: npm ci
      - run: npx tsc --noEmit
      - run: npx expo-doctor
      - run: eas update --channel preview --environment preview --auto --non-interactive
```

- Pin third-party actions to a full commit SHA in production workflows and keep `permissions` minimal.
- Pin the EAS CLI version (`eas-version: 27.2.0`) when builds must be reproducible, and set `cli.version` in `eas.json`.
- Run store submissions from a protected branch or environment with required reviewers.

## 9. Release checklist

- [ ] Build profile has the right `channel` and `environment`.
- [ ] `runtimeVersion` policy matches the team's version discipline; native changes produce a new runtime.
- [ ] Preview build installed and the update verified on it before promoting.
- [ ] Rollout percentage and a named person watching error rates, or a justified full release.
- [ ] Rollback command known (`eas update:rollback`) and a fixed binary plan for native regressions.
- [ ] No secret in any `EXPO_PUBLIC_*` variable, `extra`, or plugin prop.
- [ ] Store metadata, privacy declarations and usage strings reviewed.
