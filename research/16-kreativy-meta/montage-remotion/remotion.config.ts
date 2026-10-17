// See all configuration options: https://remotion.dev/docs/config
// Each option also is available as a CLI flag: https://remotion.dev/docs/cli

// Note: When using the Node.JS APIs, the config file doesn't apply. Instead, pass options directly to the APIs

import { Config } from "@remotion/cli/config";

Config.setRspack(true);
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
// Свой chrome-headless-shell Remotion на этом Mac не грузит корень (delayRender timeout).
// Сборка Playwright 1234 работает — используем её.
Config.setBrowserExecutable(
  "/Users/Bel-a/Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell",
);
