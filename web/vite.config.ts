import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

export default defineConfig({
  base: "/ui/",
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  build: {
    outDir: path.resolve(__dirname, "../review-api/static"),
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/runs": "http://127.0.0.1:8001",
      "/health": "http://127.0.0.1:8001",
      "/dashboard": "http://127.0.0.1:8001",
      "/reviews": "http://127.0.0.1:8001",
      "/knowledge": "http://127.0.0.1:8001",
      "/integrations": "http://127.0.0.1:8001",
      "/skills": "http://127.0.0.1:8001",
      "/test-cases": "http://127.0.0.1:8001",
      "/scripts": "http://127.0.0.1:8001",
      "/executions": "http://127.0.0.1:8001",
    },
  },
});
