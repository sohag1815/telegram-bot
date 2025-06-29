import os
import datetime
from telegram import Update, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ChatMemberHandler
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
allowed_users_env = os.getenv("ALLOWED_USERS", "")
ALLOWED_USERS = set(int(uid.strip()) for uid in allowed_users_env.split(",") if uid.strip().isdigit())

# Group-wise setting container
group_data = {}

# ========== BASIC COMMANDS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 বট সক্রিয় আছে।\n"
        "/set <keyword> ➡️ মিডিয়া/মেসেজ সেট করুন\n"
        "/unset <keyword> অথবা /unset all\n"
        "/nightmod on/off, /nighttime <start> <end>, /nightstatus\n"
        "/welcome_set, /resetall\n"
        "/filter ➡️ কিওয়ার্ড লিস্ট দেখুন"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# ========== CONFIGURATION COMMANDS ==========
async def set_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ অনুমতি নেই")
        return

    if len(context.args) < 1:
        await update.message.reply_text("ব্যবহার: /set <keyword>")
        return

    keyword = context.args[0].lower()
    context.user_data['setting_keyword'] = keyword
    await update.message.reply_text(f"📝 '{keyword}' এর জন্য মেসেজ, ছবি, অথবা লিংক পাঠান")

async def unset_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ অনুমতি নেই")
        return

    if len(context.args) < 1:
        await update.message.reply_text("/unset <keyword> অথবা /unset all")
        return

    if context.args[0].lower() == "all":
        group_data.setdefault(chat_id, {})["keywords"] = {}
        await update.message.reply_text("✅ সব কিওয়ার্ড মুছে ফেলা হলো।")
        return

    keyword = context.args[0].lower()
    if keyword in group_data.get(chat_id, {}).get("keywords", {}):
        del group_data[chat_id]["keywords"][keyword]
        await update.message.reply_text(f"❌ '{keyword}' কিওয়ার্ড মুছে ফেলা হয়েছে।")
    else:
        await update.message.reply_text("⚠️ কিওয়ার্ড খুঁজে পাওয়া যায়নি।")

async def show_all_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    keywords = group_data.get(chat_id, {}).get("keywords", {})
    if not keywords:
        await update.message.reply_text("⚠️ কোনো কিওয়ার্ড নেই।")
    else:
        keys = '\n'.join(f"• {k}" for k in keywords)
        await update.message.reply_text(f"📚 কিওয়ার্ডসমূহ:\n{keys}")

# ========== RECEIVE MESSAGE ==========
async def receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    message = update.message

    if 'setting_keyword' in context.user_data:
        keyword = context.user_data['setting_keyword']
        group = group_data.setdefault(chat_id, {})
        group.setdefault("keywords", {})[keyword] = {
            "text": message.text or "",
            "photo": message.photo[-1].file_id if message.photo else None,
            "button": None
        }
        if message.reply_markup and message.reply_markup.inline_keyboard:
            group["keywords"][keyword]["button"] = message.reply_markup.inline_keyboard
        await update.message.reply_text(f"✅ '{keyword}' এর কনটেন্ট সংরক্ষণ করা হলো।")
        del context.user_data['setting_keyword']
        return

    if context.user_data.get("setting_welcome"):
        group_data.setdefault(chat_id, {})["welcome"] = message.text
        await update.message.reply_text("✅ ওয়েলকাম মেসেজ আপডেট হয়েছে।")
        context.user_data["setting_welcome"] = False
        return

    now = datetime.datetime.now().time()
    gdata = group_data.get(chat_id, {})
    if gdata.get("night_mode"):
        start = gdata.get("night_start", 23)
        end = gdata.get("night_end", 5)
        in_range = start <= now.hour < end if start < end else now.hour >= start or now.hour < end
        if in_range:
            await update.message.reply_text("🌙 এই সময় মেসেজ পাঠানো নিষেধ।")
            return

    text = message.text.lower()
    for k, v in gdata.get("keywords", {}).items():
        if k in text:
            if v.get("photo"):
                await update.message.reply_photo(photo=v["photo"], caption=v.get("text", ""))
            elif v.get("text"):
                await update.message.reply_text(v["text"])
            return

# ========== NIGHT MODE ==========
async def nightmod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ অনুমতি নেই")
        return

    if len(context.args) != 1 or context.args[0].lower() not in ["on", "off"]:
        await update.message.reply_text("ব্যবহার: /nightmod on/off")
        return

    group = group_data.setdefault(chat_id, {})
    group["night_mode"] = context.args[0].lower() == "on"
    await update.message.reply_text(f"🌙 নাইট মোড {'চালু' if group['night_mode'] else 'বন্ধ'} হয়েছে।")

async def set_nighttime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ অনুমতি নেই")
        return

    if len(context.args) != 2:
        await update.message.reply_text("ব্যবহার: /nighttime <start_hour> <end_hour>")
        return

    group = group_data.setdefault(chat_id, {})
    group["night_start"] = int(context.args[0])
    group["night_end"] = int(context.args[1])
    await update.message.reply_text("🕰️ নাইট টাইম আপডেট হয়েছে।")

async def night_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    g = group_data.get(chat_id, {})
    await update.message.reply_text(
        f"🌙 নাইট মোড: {'চালু' if g.get('night_mode') else 'বন্ধ'}\n⏰ সময়: {g.get('night_start', 23)} - {g.get('night_end', 5)}"
    )

# ========== OTHER ==========
async def reset_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("❌ অনুমতি নেই")
        return
    group_data[update.effective_chat.id] = {}
    await update.message.reply_text("🔄 গ্রুপ সেটিংস রিসেট করা হয়েছে।")

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("❌ অনুমতি নেই")
        return
    await update.message.reply_text("নতুন ওয়েলকাম মেসেজ পাঠান:")
    context.user_data['setting_welcome'] = True

async def member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    status = update.chat_member.new_chat_member.status
    if status == "member":
        welcome_msg = group_data.get(chat_id, {}).get("welcome", "স্বাগতম!")
        await context.bot.send_message(chat_id, welcome_msg)

async def delete_service_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.delete_message(update.effective_chat.id, update.message.message_id)
    except:
        pass

# ========== RUN ==========
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("set", set_keyword))
    app.add_handler(CommandHandler("unset", unset_keyword))
    app.add_handler(CommandHandler("showall", show_all_keywords))
    app.add_handler(CommandHandler("filter", show_all_keywords))
    app.add_handler(CommandHandler("nightmod", nightmod))
    app.add_handler(CommandHandler("nighttime", set_nighttime))
    app.add_handler(CommandHandler("nightstatus", night_status))
    app.add_handler(CommandHandler("resetall", reset_all))
    app.add_handler(CommandHandler("welcome_set", set_welcome))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), receive_message))
    app.add_handler(ChatMemberHandler(member_update))
    app.add_handler(MessageHandler(filters.StatusUpdate.ALL, delete_service_messages))

    print("✅ Bot running...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
