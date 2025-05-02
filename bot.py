import json
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters, ConversationHandler

# Состояния
CATEGORY, SELECT_PRODUCT, GET_NAME, GET_ADDRESS, CONFIRM = range(5)

# Загрузка каталога
with open("data/catalog.json", "r", encoding="utf-8") as f:
    catalog = json.load(f)

# Память сессий пользователей
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(cat, callback_data=cat)] for cat in catalog.keys()]
    await update.message.reply_text("Выберите категорию:", reply_markup=InlineKeyboardMarkup(keyboard))
    return CATEGORY

async def category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data
    context.user_data["category"] = category
    keyboard = []
    media = []

    for item in catalog[category]:
        caption = f"№{item['id']} — {item['name']}\nЦена: {item['price']}₽"
        with open(item['image'], "rb") as img_file:
            await query.message.reply_photo(photo=img_file, caption=caption)

    await query.message.reply_text("Введите номер товара, который вас заинтересовал (например, 1):")
    return SELECT_PRODUCT

async def select_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    product_id = int(update.message.text.strip())
    category = context.user_data["category"]

    product = next((p for p in catalog[category] if p["id"] == product_id), None)
    if not product:
        await update.message.reply_text("Товар с таким номером не найден. Введите ещё раз:")
        return SELECT_PRODUCT

    context.user_data["product"] = product
    await update.message.reply_text("Введите ваше имя:")
    return GET_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Введите ваш адрес:")
    return GET_ADDRESS

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["address"] = update.message.text

    product = context.user_data["product"]
    name = context.user_data["name"]
    address = context.user_data["address"]
    category = context.user_data["category"]

    summary = (
        f"Вы выбрали:\n\n"
        f"🔒 Товар: {product['name']} (№{product['id']})\n"
        f"📂 Категория: {category}\n"
        f"💵 Цена: {product['price']}₽\n\n"
        f"🧑 Имя: {name}\n"
        f"🏠 Адрес: {address}\n\n"
        f"Подтвердите заказ (да/нет):"
    )
    await update.message.reply_text(summary)
    return CONFIRM

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if update.message.text.lower() in ["да", "yes", "ок", "подтверждаю"]:
    product = context.user_data["product"]
    name = context.user_data["name"]
    address = context.user_data["address"]
    category = context.user_data["category"]

    send_whatsapp_order(product, name, address, category)
    await update.message.reply_text("✅ Спасибо! Ваш заказ принят. Мы скоро с вами свяжемся.")


# Настройки Twilio (замени на свои реальные данные)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = "whatsapp:+19787337969"  # Это номер Twilio
MANAGER_NUMBER = "whatsapp:+992005997884"  # Твой WhatsApp номер

def send_whatsapp_order(product, name, address, category):
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    message = (
        f"🔔 НОВЫЙ ЗАКАЗ\n\n"
        f"Категория: {category}\n"
        f"Товар: {product['name']} (№{product['id']})\n"
        f"Цена: {product['price']}₽\n\n"
        f"Имя: {name}\n"
        f"Адрес: {address}"
    )

    client.messages.create(
        body=message,
        from_=TWILIO_WHATSAPP_NUMBER,
        to=MANAGER_NUMBER
    )

    else:
        await update.message.reply_text("❌ Заказ отменён. Вы можете начать сначала: /start")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Выход из процесса. Чтобы начать заново — /start")
    return ConversationHandler.END

# Запуск бота
def main():
    TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CATEGORY: [CallbackQueryHandler(category_selected)],
            SELECT_PRODUCT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_product)],
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GET_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
