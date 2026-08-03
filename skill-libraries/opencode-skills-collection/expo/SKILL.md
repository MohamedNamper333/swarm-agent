---
name: expo
description: Use when building cross-platform React Native applications with Expo, including managed workflow, EAS Build, EAS Update, and app store deployment. Invoke for project setup, native module configuration, EAS builds, OTA updates, app config, push notifications, and app store submission.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: mobile
  triggers: Expo, React Native, EAS, expo-cli, managed workflow, development build, OTA update, app.json, app.config, push notification, EAS Build, EAS Submit, Expo Go, expo-router, Expo SDK
  role: specialist
  scope: implementation
  output-format: code
  related-skills: react-native-expert, react-expert, developer, ci-cd-and-automation
---

# Expo

Expo is a framework and platform for building cross-platform React Native applications. It provides a managed runtime, over-the-air updates, cloud build services (EAS), and a unified SDK that abstracts native configuration. Expo supports both managed and bare workflows with automatic native module resolution.

## When to Use This Skill

- Scaffolding a new Expo app with `npx create-expo-app` and configuring `app.json`/`app.config.ts`
- Building and submitting iOS and Android apps to app stores via EAS Build and EAS Submit
- Implementing push notifications with Expo Notifications API and FCM/APNs configuration
- Publishing OTA updates with EAS Update for instant bug fixes without app store review

## Key Capabilities

- Configure `app.config.ts` with plugins, environment variables, icons, splash screen, and deep linking schemes
- Build native binaries with EAS Build for iOS (IPA) and Android (APK/AAB) with code signing and credentials management
- Publish over-the-air updates with `eas update` using EAS Update service and channel-based release management
- Configure Expo plugins for native module customization — camera, biometrics, payments, and other native APIs

## Best Practices

- Use `expo-dev-client` (development builds) instead of Expo Go for projects with custom native modules or plugins
- Store environment-specific config in `app.config.ts` using the `extra` field accessed via `Constants.expoConfig.extra`
- Use EAS Update channels (e.g., `production`, `staging`, `pr-123`) to control which builds receive which updates
- Configure automatic versioning with `version` and `buildNumber` in app config, and CI-driven `EAS_BUILD_VERSION` env vars

## Core Workflow

1. **Create** — Run `npx create-expo-app@latest MyApp --template blank-typescript`
2. **Configure** — Edit `app.config.ts` with app name, icon, splash, plugins, and environment variables
3. **Develop** — Run `npx expo start` for local development with Expo Go or a development build
4. **Build** — Run `eas build --platform all` for production binaries
5. **Submit** — Run `eas submit --platform all` to upload to App Store Connect and Google Play Console

## Key Patterns

```typescript
// app.config.ts — Full Expo configuration
import { ExpoConfig, ConfigContext } from 'expo/config';

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: 'MyApp',
  slug: 'my-app',
  version: '1.0.0',
  orientation: 'portrait',
  icon: './assets/icon.png',
  scheme: 'myapp',
  splash: {
    image: './assets/splash.png',
    resizeMode: 'contain',
    backgroundColor: '#ffffff',
  },
  plugins: [
    'expo-router',
    'expo-secure-store',
    ['expo-camera', { cameraPermission: 'Allow access to your camera.' }],
  ],
  extra: {
    apiUrl: process.env.API_URL ?? 'https://api.dev.example.com',
    eas: { projectId: process.env.EAS_PROJECT_ID },
  },
});
```

```typescript
// Push notifications
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import Constants from 'expo-constants';

async function registerForPushNotifications() {
  if (!Device.isDevice) return;

  const { status } = await Notifications.requestPermissionsAsync();
  if (status !== 'granted') return;

  const token = await Notifications.getExpoPushTokenAsync({
    projectId: Constants.expoConfig?.extra?.eas?.projectId,
  });

  // Send token to your backend
  await api.post('/push-token', { token: token.data });
}
```

## Constraints

### MUST DO
- Use `expo-dev-client` for any project with custom native plugins (not Expo Go)
- Set `app.config.ts` with `runtimeVersion` policy for EAS Update to work correctly
- Run `eas build` on CI for reproducible builds — avoid building locally for production

### MUST NOT DO
- Commit `google-services.json` or `GoogleService-Info.plist` to public repositories
- Use Expo Go for production testing — always use development builds or production builds
- Mix EAS Update channels between development and production without careful testing
