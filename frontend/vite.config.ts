import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// In dev, /api is proxied to the FastAPI backend (uvicorn on :8080).
export default defineConfig({
  plugins: [vue()],
  server: { proxy: { "/api": "http://localhost:8080" } },
});
