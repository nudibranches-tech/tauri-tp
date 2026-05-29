import { defineConfig } from "vite";

// @tauri-apps/cli sets TAURI_DEV_HOST when running `tauri dev` on a device.
const host = process.env.TAURI_DEV_HOST;

// https://vite.dev/config/
export default defineConfig({
  // Prevent Vite from clearing Rust compiler output.
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    host: host || false,
    hmr: host
      ? { protocol: "ws", host, port: 1421 }
      : undefined,
    watch: {
      // Tauri's Rust sources are watched by cargo, not Vite.
      ignored: ["**/src-tauri/**"],
    },
  },
});
