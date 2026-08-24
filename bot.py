import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = "8800294305:AAH9J_eXWr3aC9WrzDfiID0iWXwUV-nKgTw"
CHANNEL_USERNAME = "@q8wee"

QUESTIONS = [
    {"q": "هل يتكون الماء من أكسجين وهيدروجين؟", "a": "صح"},
    {"q": "هل كوكب المريخ هو أبعد كوكب عن الشمس؟", "a": "خطأ"},
    {"q": "هل كرة القدم تلعب بـ 11 لاعباً لكل فريق؟", "a": "صح"},
    {"q": "هل السرعة القصوى للضوء أكبر من الصوت؟", "a": "صح"},
    {"q": "هل عاصمة فرنسا هي مدريد؟", "a": "خطأ"},
]

games = {}
user_stats = {}

async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            return True
        return False
    except Exception:
        return True

async def prompt_subscription(update: Update):
    keyboard = [
        [InlineKeyboardButton("اشترك في القناة 📢", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("تم الاشتراك ✅", callback_data="check_sub")]
    ]
    msg_text = f"⚠️ **عذراً! يجب عليك الاشتراك في قناة البوت أولاً لاستخدام اللعبة:**\n\n👉 {CHANNEL_USERNAME}"
    
    if update.callback_query:
        await update.callback_query.answer("يرجى الاشتراك بالقناة أولاً!", show_alert=True)
        await update.callback_query.message.reply_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_subscription(user_id, context):
        await prompt_subscription(update)
        return

    main_menu = [
        ["🎮 ابدأ اللعب"],
        ["🏆 المتصدرون", "📊 إحصائياتي"],
        ["⚔️ تحدي لاعب", "🎁 المهام"],
        ["👤 حسابي"],
        ["ℹ️ طريقة اللعب", "⚙️ الإعدادات"]
    ]
    reply_markup = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
    
    await update.message.reply_text(
        "🔥 **أهلاً بك في لعبة Truth Battle!**\n\nاختر من القائمة أدناه للبدء:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_text_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user

    if not await check_subscription(user.id, context):
        await prompt_subscription(update)
        return

    if text == "🎮 ابدأ اللعب":
        await start_game(update, context)
    elif text == "🏆 المتصدرون":
        await show_leaderboard(update)
    elif text == "📊 إحصائياتي":
        stats = user_stats.get(user.id, {"games": 0, "score": 0})
        await update.message.reply_text(f"📊 **إحصائياتك يا {user.first_name}:**\n\n🎯 عدد الألعاب: {stats['games']}\n⭐ مجموع النقاط: {stats['score']}")
    elif text == "👤 حسابي":
        await update.message.reply_text(f"👤 **معلومات الحساب:**\n\nالاسم: {user.first_name}\nالمعرف: @{user.username if user.username else 'لا يوجد'}\nالآيدي: `{user.id}`", parse_mode="Markdown")
    elif text == "ℹ️ طريقة اللعب":
        await update.message.reply_text("ℹ️ **طريقة اللعب:**\n\n1. تنضم للعبة مع 15 لاعب كحد أقصى.\n2. تطرح أسئلة عامة (صح أم خطأ).\n3. كل إجابة صحيحة تمنحك نقطة لتتصدر القائمة!")
    elif text in ["⚔️ تحدي لاعب", "🎁 المهام", "⚙️ الإعدادات"]:
        await update.message.reply_text("🚧 **هذه الميزة قيد التطوير وستتوفّر قريباً!**")

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in games and games[chat_id]["active"]:
        await update.message.reply_text("اللعبة قائمة حالياً بالفعل!")
        return

    games[chat_id] = {
        "players": {},
        "current_q": 0,
        "scores": {},
        "active": False
    }

    keyboard = [[InlineKeyboardButton("انضمام للعبة 🎮", callback_data="join")]]
    await update.message.reply_text(
        "🔥 **بدأت لعبة Truth Battle!**\n\n"
        "الانضمام مفتوح لـ 15 لاعب كحد أقصى.\n"
        "اضغط على الزر للإنضمام!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    chat_id = query.message.chat_id

    if not await check_subscription(user.id, context):
        await prompt_subscription(update)
        return

    game = games.get(chat_id)
    if not game:
        await query.answer("لا توجد لعبة قائمة حالياً!", show_alert=True)
        return

    if user.id in game["players"]:
        await query.answer("أنت منضم بالفعل!", show_alert=True)
        return

    if len(game["players"]) >= 15:
        await query.answer("اكتمل العدد الأقصى (15 لاعب)!", show_alert=True)
        return

    game["players"][user.id] = user.first_name
    game["scores"][user.id] = 0
    await query.answer("تم انضمامك بنجاح!")

    players_list = "\n".join([f"- {name}" for name in game["players"].values()])
    keyboard = [[InlineKeyboardButton("انضمام للعبة 🎮", callback_data="join")]]
    
    await query.edit_message_text(
        f"🔥 **بدأت لعبة Truth Battle!**\n\n"
        f"اللاعبون المنضمون ({len(game['players'])}/15):\n"
        f"{players_list}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def show_leaderboard(update: Update):
    if not user_stats:
        await update.message.reply_text("🏆 **قائمة المتصدرين فارغة حالياً!**")
        return
    
    sorted_users = sorted(user_stats.items(), key=lambda x: x[1]['score'], reverse=True)
    text = "🏆 **قائمة أبطال المتصدرين:**\n\n"
    for rank, (uid, data) in enumerate(sorted_users[:10], 1):
        text += f"{rank}. المستخدم `{uid}` — {data['score']} نقطة\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def check_sub_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await check_subscription(query.from_user.id, context):
        await query.answer("شكراً لاشتراكك! يمكنك الآن استخدام البوت 🎉", show_alert=True)
        await query.message.delete()
    else:
        await query.answer("لم تقم بالاشتراك بعد، يرجى الاشتراك أولاً.", show_alert=True)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_sub_button, pattern="^check_sub$"))
    app.add_handler(CallbackQueryHandler(handle_join, pattern="^join$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_menu))
    app.run_polling()
