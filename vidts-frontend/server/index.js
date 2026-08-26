// Minimal static host required by the managed deployment; application code remains client-side React.
import express from "express";
import { createServer } from "http";
import path from "path";
import { fileURLToPath } from "url";

const filename = fileURLToPath(import.meta.url);
const dirname = path.dirname(filename);
const app = express();
const server = createServer(app);
const staticPath = path.resolve(dirname, "..", "dist", "public");

app.use(express.static(staticPath));
app.get("*", (_request, response) => response.sendFile(path.join(staticPath, "index.html")));

server.listen(process.env.PORT || 3000, () => {
  console.log("vidts static frontend is running");
});
