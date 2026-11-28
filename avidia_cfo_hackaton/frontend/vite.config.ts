import { fileURLToPath, URL } from "node:url";
import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";

// Dev: /api is proxied to the backend. Default = local uvicorn on :8080.
// To work against the live cluster backend, set VITE_API_TARGET in frontend/.env.local (see .env.example).
// Prod: FastAPI serves dist/ from the same origin, so no proxy and no CORS.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const target = env.VITE_API_TARGET || "http://localhost:8080";

  return {
    plugins: [vue()],
    resolve: {
      alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
    },
    server: {
      proxy: {
        "/api": { target, changeOrigin: true, secure: false },
      },
    },
  };
});
