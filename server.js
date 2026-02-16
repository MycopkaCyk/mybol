/**
 * Запуск на Railway в режиме webhook (без polling → нет 409).
 * В Variables задать: BOT_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, WEBHOOK_URL
 * WEBHOOK_URL = публичный URL сервиса, например https://your-app.up.railway.app
 */
import path from "path";
import { fileURLToPath } from "url";
import dotenv from "dotenv";
import http from "http";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, ".env") });

const PORT = Number(process.env.PORT) || 8000;
const WEBHOOK_URL = process.env.WEBHOOK_URL?.replace(/\/$/, "");

if (!process.env.BOT_TOKEN || !process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_ROLE_KEY) {
  console.error("Задайте BOT_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY в Variables");
  process.exit(1);
}
if (!WEBHOOK_URL) {
  console.error("Задайте WEBHOOK_URL в Variables (публичный URL сервиса, например https://xxx.up.railway.app)");
  process.exit(1);
}

const { bot } = await import("./api/webhook.js");

await bot.telegram.setWebhook(WEBHOOK_URL);
console.log("Webhook установлен:", WEBHOOK_URL);

const server = http.createServer((req, res) => {
  if (req.method !== "POST" || (req.url !== "/" && req.url !== "/webhook")) {
    res.writeHead(404);
    res.end();
    return;
  }
  let body = "";
  req.on("data", (chunk) => { body += chunk; });
  req.on("end", () => {
    bot.handleUpdate(JSON.parse(body || "{}")).catch((e) => console.error("handleUpdate error:", e));
    res.writeHead(200);
    res.end();
  });
});

server.listen(PORT, "0.0.0.0", () => {
  console.log("Сервер слушает порт", PORT);
});
