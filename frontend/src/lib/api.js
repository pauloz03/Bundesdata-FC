/**
 * FastAPI base URL (port 8000). In dev, Vite proxies /auth and /users to this target.
 */
export const apiBaseUrl = (() => {
  const fromEnv = import.meta.env.VITE_API_URL?.replace(/\/$/, "");
  if (fromEnv) return fromEnv;
  if (import.meta.env.DEV) return "";
  return "http://localhost:8000";
})();
