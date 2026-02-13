// api/webhook.js
// Примитивный сценарий: нажатие → инфо → нажатие → инфо → нажатие → отзыв (текст) → оценка полезности → оценка удобства → завершение
//
// Таблица public."mYfeedbek": id, created_at, tg_user_id, tg_username, category, comment, rating_usefulness, rating_usability
//
// Переменные окружения: BOT_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, WEBHOOK_SECRET
import { Telegraf, Markup } from "telegraf";
import { createClient } from "@supabase/supabase-js";
import { TEXT } from "../texts.js";

const bot = new Telegraf(process.env.BOT_TOKEN);

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY,
  { auth: { persistSession: false } }
);

/**
 * Состояние: userId -> {
 *   step: "START" | "INFO1" | "INFO2" | "WAIT_FEEDBACK" | "WAIT_USEFULNESS" | "WAIT_USABILITY"
 *   comment?: string
 *   usefulness?: number
 * }
 */
const state = new Map();

function kbNext() {
  return Markup.inlineKeyboard([[Markup.button.callback("Далее", "next")]]);
}

function kbLeaveFeedback() {
  return Markup.inlineKeyboard([[Markup.button.callback("Оставить отзыв", "leave_feedback")]]);
}

function kbRating(prefix) {
  return Markup.inlineKeyboard([
    [1, 2, 3, 4, 5].map((n) => Markup.button.callback(`⭐ ${n}`, `${prefix}:${n}`)),
  ]);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Задержка "Печатает…": по длине текста + дополнительная секунда
const EXTRA_TYPING_MS = 1000;

function calcDelayMs(text) {
  const ms = Math.round(String(text ?? "").length * 12);
  return Math.max(500, Math.min(1300, ms)) + EXTRA_TYPING_MS;
}

// options.deletePreviousMessageId — id сообщения с кнопкой; удаляется после появления "Печатает…", создаётся эффект замены
async function sendTypingThen(ctx, finalText, extra = undefined, parseMode = "HTML", options = {}) {
  const { deletePreviousMessageId } = options;
  const safeTyping = TEXT?.typing ?? "Печатает…";
  const safeText = String(finalText ?? "");

  try {
    await ctx.telegram.sendChatAction(ctx.chat.id, "typing");
  } catch {}

  let tempMsgId = null;
  try {
    const temp = await ctx.reply(safeTyping);
    tempMsgId = temp.message_id;
  } catch {}

  // Сначала показали "Печатает…", теперь удаляем предыдущее — создаётся впечатление замены
  if (deletePreviousMessageId) {
    try {
      await ctx.telegram.deleteMessage(ctx.chat.id, deletePreviousMessageId);
    } catch {}
  }

  await sleep(calcDelayMs(safeText));

  if (tempMsgId) {
    try {
      await ctx.telegram.deleteMessage(ctx.chat.id, tempMsgId);
    } catch {}
  }

  return ctx.reply(safeText, { ...extra, parse_mode: parseMode });
}

function setState(userId, patch) {
  const prev = state.get(userId) || { step: "START" };
  state.set(userId, { ...prev, ...patch });
}

function resetState(userId) {
  state.set(userId, { step: "START" });
}

// ——— /start ———
bot.start(async (ctx) => {
  resetState(ctx.from.id);
  await sendTypingThen(ctx, TEXT.greeting, kbNext());
});

// ——— Кнопка "Далее" / "Оставить отзыв" ———
const deleteAfterTyping = (ctx) =>
  ctx.callbackQuery?.message?.message_id ? { deletePreviousMessageId: ctx.callbackQuery.message.message_id } : {};

bot.action("next", async (ctx) => {
  await ctx.answerCbQuery();
  const userId = ctx.from.id;
  const st = state.get(userId) || { step: "START" };

  if (st.step === "START") {
    setState(userId, { step: "INFO1" });
    await sendTypingThen(ctx, TEXT.info1, kbNext(), "HTML", deleteAfterTyping(ctx));
    return;
  }

  if (st.step === "INFO1") {
    setState(userId, { step: "INFO2" });
    await sendTypingThen(ctx, TEXT.info2, kbLeaveFeedback(), "HTML", deleteAfterTyping(ctx));
    return;
  }

  if (st.step === "INFO2") {
    await sendTypingThen(ctx, TEXT.info2, kbLeaveFeedback(), "HTML", deleteAfterTyping(ctx));
    return;
  }
});

bot.action("leave_feedback", async (ctx) => {
  await ctx.answerCbQuery();
  const userId = ctx.from.id;
  setState(userId, { step: "WAIT_FEEDBACK" });
  await sendTypingThen(ctx, TEXT.askFeedback, undefined, "HTML", deleteAfterTyping(ctx));
});

// ——— Текст от пользователя (WAIT_FEEDBACK) → запоминаем и просим оценку полезности ———
bot.on("text", async (ctx) => {
  const userId = ctx.from.id;
  const st = state.get(userId);
  if (!st || st.step !== "WAIT_FEEDBACK") return;

  const comment = ctx.message.text.trim();
  if (!comment) return;

  setState(userId, { step: "WAIT_USEFULNESS", comment });
  await sendTypingThen(ctx, TEXT.askUsefulness, kbRating("useful"));
});

// ——— Оценка полезности (1–5) → просим оценку удобства ———
bot.action(/^useful:(\d)$/, async (ctx) => {
  await ctx.answerCbQuery();
  const userId = ctx.from.id;
  const st = state.get(userId);
  if (!st || st.step !== "WAIT_USEFULNESS") return;

  const val = Number(ctx.match[1]);
  setState(userId, { step: "WAIT_USABILITY", usefulness: val });
  // После выбора оценки полезности убираем сообщение с рейтингом и переходим к следующему вопросу
  await sendTypingThen(ctx, TEXT.askUsability, kbRating("usable"), "HTML", deleteAfterTyping(ctx));
});

// ——— Оценка удобства (1–5) → сохранение в БД и завершающее сообщение ———
bot.action(/^usable:(\d)$/, async (ctx) => {
  await ctx.answerCbQuery();
  const userId = ctx.from.id;
  const st = state.get(userId);
  if (!st || st.step !== "WAIT_USABILITY" || !st.comment || st.usefulness == null) return;

  const usability = Number(ctx.match[1]);
  const avg = (st.usefulness + usability) / 2;

  const payload = {
    tg_user_id: userId,
    tg_username: ctx.from.username ?? null,
    category: "FEEDBACK",
    comment: st.comment,
    rating_usefulness: st.usefulness,
    rating_usability: usability,
  };

  const { error } = await supabase.from("mYfeedbek").insert(payload);

  if (error) {
    console.error("SUPABASE INSERT ERROR:", {
      message: error.message,
      code: error.code,
    });
    await sendTypingThen(ctx, TEXT.saveError(error.code));
    return;
  }

  resetState(userId);
  // Выбираем финальное сообщение в зависимости от средней оценки (1–2, 3, 4–5)
  const finalText =
    avg <= 2 ? TEXT.closeLow : avg <= 3 ? TEXT.closeMid : TEXT.closeHigh;

  await sendTypingThen(
    ctx,
    finalText,
    { reply_markup: { inline_keyboard: [] } },
    "HTML",
    deleteAfterTyping(ctx)
  );
});

// Для локального запуска через polling (см. local.js)
export { bot };

// ——— Vercel ———
export default async function handler(req, res) {
  const secret = req.headers["x-telegram-bot-api-secret-token"];
  if (secret !== process.env.WEBHOOK_SECRET) {
    res.status(401).send("unauthorized");
    return;
  }
  if (req.method !== "POST") {
    res.status(200).send("ok");
    return;
  }
  try {
    await bot.handleUpdate(req.body);
  } catch (e) {
    console.error("BOT HANDLE UPDATE ERROR:", e);
  }
  res.status(200).send("ok");
}
