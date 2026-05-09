/**
 * API base URL. In Vite dev, default is same-origin + `vite.config.js` proxy → no CORS.
 * Set VITE_API_URL to your Express URL for `vite preview` or production builds.
 */
export const apiBaseUrl = (() => {
  const fromEnv = import.meta.env.VITE_API_URL?.replace(/\/$/, "");
  if (fromEnv) return fromEnv;
  if (import.meta.env.DEV) return "";
  return "http://localhost:5050";
})();
