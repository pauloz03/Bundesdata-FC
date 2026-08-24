import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiTarget = env.VITE_DEV_API_PROXY || "http://localhost:8000";
  const analyticsTarget = env.VITE_DEV_ANALYTICS_PROXY || "http://localhost:8000";

  return {
    plugins: [react()],
    server: {
      proxy: {
        "/auth": { target: apiTarget, changeOrigin: true },
        "/matches": { target: analyticsTarget, changeOrigin: true },
        "/users": { target: analyticsTarget, changeOrigin: true },
        "/health": { target: analyticsTarget, changeOrigin: true },
        "/explore": { target: analyticsTarget, changeOrigin: true },
      },
    },
  };
});
