// Локальный запуск: .env в корне (BOT_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY), затем npm run dev
import path from "path";
import { fileURLToPath } from "url";
import dotenv from "dotenv";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, ".env") });

if (!process.env.BOT_TOKEN) {
  console.error("Не задан BOT_TOKEN. Локально: .env. На Railway: Variables в настройках проекта.");
  process.exit(1);
}
if (!process.env.SUPABASE_URL) {
  console.error("Не задан SUPABASE_URL. Локально: .env. На Railway: Variables в настройках проекта.");
  process.exit(1);
}
if (!process.env.SUPABASE_SERVICE_ROLE_KEY) {
  console.error("Не задан SUPABASE_SERVICE_ROLE_KEY. Локально: .env. На Railway: Variables в настройках проекта.");
  process.exit(1);
}

const { bot } = await import("./api/webhook.js");
bot.launch().then(() => console.log("Бот запущен (polling). /start в Telegram"));
process.once("SIGINT", () => bot.stop("SIGINT"));
process.once("SIGTERM", () => bot.stop("SIGTERM"));
