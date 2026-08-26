// Minimal JavaScript Vite configuration for the vidts React frontend.
import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { vitePluginManusRuntime } from "vite-plugin-manus-runtime";

const projectRoot = import.meta.dirname;

function manusStorageProxy() {
  return {
    name: "manus-storage-proxy",
    configureServer(server) {
      server.middlewares.use("/manus-storage", async (request, response) => {
        const key = request.url?.replace(/^\//, "");
        const baseUrl = (process.env.BUILT_IN_FORGE_API_URL || "").replace(/\/+$/, "");
        const accessKey = process.env.BUILT_IN_FORGE_API_KEY;

        if (!key || !baseUrl || !accessKey) {
          response.writeHead(404, { "Content-Type": "text/plain" });
          response.end("Asset is unavailable");
          return;
        }

        try {
          const url = new URL("v1/storage/presign/get", `${baseUrl}/`);
          url.searchParams.set("path", key);
          const assetResponse = await fetch(url, { headers: { Authorization: `Bearer ${accessKey}` } });
          const { url: assetUrl } = await assetResponse.json();
          response.writeHead(assetResponse.ok && assetUrl ? 307 : 502, assetUrl ? { Location: assetUrl } : { "Content-Type": "text/plain" });
          response.end(assetUrl ? undefined : "Asset is unavailable");
        } catch {
          response.writeHead(502, { "Content-Type": "text/plain" });
          response.end("Asset is unavailable");
        }
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), vitePluginManusRuntime(), manusStorageProxy()],
  root: path.resolve(projectRoot, "client"),
  build: {
    outDir: path.resolve(projectRoot, "dist/public"),
    emptyOutDir: true,
  },
  server: {
    host: true,
    port: 3000,
    strictPort: false,
    allowedHosts: [".manuspre.computer", ".manus.computer", ".manus-asia.computer", ".manuscomputer.ai", "localhost", "127.0.0.1"],
  },
});
