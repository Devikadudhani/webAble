import { defineConfig } from "vite";
export default defineConfig({
  root: "frontend",
  base: "/static/",
  server: {
    proxy: {
      "/accessibility": "http://127.0.0.1:8000",
      "/captures": "http://127.0.0.1:8000",
    },
  },
  build: { outDir: "../app/static", emptyOutDir: true },
});
