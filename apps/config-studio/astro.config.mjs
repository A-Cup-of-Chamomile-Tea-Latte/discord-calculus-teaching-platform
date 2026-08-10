import { defineConfig } from "astro/config";

export default defineConfig({
  output: "static",
  server: {
    host: "127.0.0.1",
  },
  vite: {
    server: {
      strictPort: true,
    },
  },
});
