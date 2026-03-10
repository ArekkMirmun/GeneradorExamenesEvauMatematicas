import { defineConfig } from "astro/config";
import tailwind from "@astrojs/tailwind";

export default defineConfig({
  site: "https://arekkmirmun.github.io",
  base: "/GeneradorExamenesEvau",
  integrations: [tailwind()],
});
