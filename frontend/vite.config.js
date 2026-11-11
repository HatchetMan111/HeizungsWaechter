import { defineConfig } from "vite";
import { resolve } from "node:path";

// Baut die Lovelace-Card als einzelnes ES-Modul direkt in die
// Integration (custom_components/heizungswaechter/www/).
export default defineConfig({
  // Lib-Mode ersetzt process.env.NODE_ENV nicht automatisch – React
  // würde sonst im Browser mit "process is not defined" abstürzen.
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
  esbuild: {
    jsx: "automatic",
  },
  build: {
    target: "es2022",
    minify: "esbuild",
    outDir: resolve(__dirname, "../custom_components/heizungswaechter/www"),
    emptyOutDir: true,
    lib: {
      entry: resolve(__dirname, "src/main.jsx"),
      formats: ["es"],
      fileName: () => "heizungswaechter-card.js",
    },
  },
});
