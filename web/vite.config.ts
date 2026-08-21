import { fileURLToPath, URL } from "node:url"

import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

const API_TARGET = "http://127.0.0.1:8000"

const API_PREFIXES = [
  "/api",
  "/health",
  "/papers",
  "/ingest",
  "/extract",
  "/verify",
  "/jobs",
  "/benchmark",
  "/claims",
  "/report",
  "/demo",
  "/static",
]

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    proxy: Object.fromEntries(
      API_PREFIXES.map((prefix) => [
        prefix,
        {
          target: API_TARGET,
          changeOrigin: true,
          bypass(req) {
            if (req.headers.accept?.includes("text/html")) {
              return "/index.html"
            }
          },
        },
      ]),
    ),
  },
})
