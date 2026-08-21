import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  transpilePackages: ["maplibre-gl", "@vis.gl/react-maplibre"],
  // NOTE: This project must use the webpack bundler for `next build`.
  // Turbopack's build cannot bundle maplibre-gl v6 because the package's
  // worker-spawning fallback uses `new URL(e, import.meta.url)` which
  // Turbopack cannot resolve at build time. The `webpackIgnore: true`
  // magic comment in PitHeatmap's dynamic import handles this in dev mode
  // (where the package loads from esm.sh at runtime), but Turbopack build
  // also walks the static dep tree via @vis.gl/react-maplibre and fails
  // before it can defer to the runtime import. Keep the build script on
  // `next build --webpack` (see package.json).
};

export default nextConfig;


