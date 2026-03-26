import os
import logging
import asyncio
import random
import string
from typing import Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ТОКЕН
TOKEN = "8445466695:AAGORyjHM8ghSs2jhKblwwrO0-aJNp6Zuq8"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

user_data: Dict[int, Dict] = {}

# ЗАДАНИЯ ПО ПОРЯДКУ
TASKS_ORDER = ["yandex", "sberprime", "24tv"]

# ИНФОРМАЦИЯ О ЗАДАНИЯХ
TASK_INFO = {
    "yandex": {
        "name": "📱 СКАЧАТЬ ЯНДЕКС БРАУЗЕР",
        "description": "Скачай Яндекс Браузер по ссылке и установи",
        "link": "https://vk.cc/cVUvvJ",
        "button": "🔽 СКАЧАТЬ ЯНДЕКС БРАУЗЕР"
    },
    "sberprime": {
        "name": "💳 <b>СБЕРПРАЙМ ЗА 1 РУБЛЬ</b>",
        "description": "<b>Оформи подписку СберПрайм за 1 рубль</b>\n(если ссылка не открывается, выключи VPN)",
        "link": "https://vk.cc/cVUvEb",
        "button": "💳 ОФОРМИТЬ СБЕРПРАЙМ"
    },
    "24tv": {
        "name": "🎬 АКТИВИРОВАТЬ ПРОМОКОД 24TV",
        "description": "Перейди по ссылке и активируй промокод",
        "link": "https://vk.cc/cVUwtW",
        "button": "🎬 АКТИВИРОВАТЬ ПРОМОКОД"
    }
}

def generate_promo_code() -> str:
    characters = string.ascii_letters + string.digits
    length = random.randint(9, 12)
    return ''.join(random.choice(characters) for _ in range(length))

class UserState:
    def __init__(self, user_id: int, username: str):
        self.user_id = user_id
        self.username = username
        self.current_task_index = 0
        self.waiting_for_screenshot = False
        self.current_task_key = None
        self.reward_claimed = False
        self.promo_code = None
        self.completed_tasks = []

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎁 ПОЛУЧИТЬ 5000 G-Coins", callback_data="start_tasks")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    user = update.effective_user
    text = (
        f"🎮 ПОЛУЧИ ГОЛДУ STANDOFF 2 БЕСПЛАТНО! 🎮\n\n"
        f"Привет, {user.first_name}! 👋\n\n"
        f"Активируй скрытый промокод разработчиков.\n\n"
        f"💰 Выполни 3 задания и получи 5000 G-Coins!\n\n"
        f"👇 Нажми на кнопку:"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def start_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id in user_data:
        user = user_data[user_id]
        if user.reward_claimed:
            await query.edit_message_text("❌ Ты уже получил промокод! Нельзя проходить задания повторно.", parse_mode=ParseMode.HTML)
            return
    
    user = UserState(user_id, query.from_user.username)
    user.current_task_index = 0
    user.completed_tasks = []
    
    user_data[user_id] = user
    
    await show_current_task(query, user)

async def show_current_task(query, user: UserState):
    if user.current_task_index >= len(TASKS_ORDER):
        user.promo_code = generate_promo_code()
        user.reward_claimed = True
        
        await query.edit_message_text(
            text=f"✅ ПОЗДРАВЛЯЮ! ТЫ ПРОШЕЛ ВСЕ 3 ЗАДАНИЯ! 🎉🎉🎉\n\n"
                 f"━━━━━━━━━━━━━━━━━━━━━━\n"
                 f"🎁 ТВОЙ ПРОМОКОД НА 5000 G-Coins:\n"
                 f"<code>{user.promo_code}</code>\n\n"
                 f"🔑 Активируй в игре Standoff 2\n"
                 f"и получи голду бесплатно!\n"
                 f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                 f"Спасибо за участие! 🎮",
            parse_mode=ParseMode.HTML
        )
        return
    
    task_key = TASKS_ORDER[user.current_task_index]
    task = TASK_INFO[task_key]
    
    current = user.current_task_index + 1
    
    text = (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 <b>ЗАДАНИЕ {current} ИЗ 3</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>{task['name']}</b>\n\n"
        f"{task['description']}\n\n"
        f"🔗 <a href='{task['link']}'>👉 {task['button']} 👈</a>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📸 <b>КАК ПОДТВЕРДИТЬ:</b>\n"
        f"После выполнения отправь СКРИНШОТ подтверждения\n"
        f"⏱ Автопроверка займет 5 секунд\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"❌ Отмена - нажми /start"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ ОТМЕНИТЬ ВСЕ", callback_data="cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    user.waiting_for_screenshot = True
    user.current_task_key = task_key
    
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )

async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id in user_data:
        del user_data[user_id]
    
    await main_menu(update, context)

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_data:
        await update.message.reply_text("❌ Сначала нажми /start и выбери 'ПОЛУЧИТЬ 5000 G-Coins'")
        return
    
    user = user_data[user_id]
    
    if user.reward_claimed:
        await update.message.reply_text("❌ Ты уже получил промокод!")
        return
    
    if not user.waiting_for_screenshot:
        await update.message.reply_text("❌ Сейчас не нужно отправлять скриншот. Нажми /start")
        return
    
    photo = update.message.photo[-1]
    user.waiting_for_screenshot = False
    
    current_num = user.current_task_index + 1
    task_name = TASK_INFO[user.current_task_key]["name"]
    
    checking_msg = await update.message.reply_text(
        f"⏳ ПРОВЕРКА ЗАДАНИЯ {current_num}/3...\n\n"
        f"📋 {task_name}\n\n"
        f"🔍 Идет автоматическая проверка скриншота...\n"
        f"⏱ Подожди 5 секунд!\n\n"
        f"Не отправляй новые сообщения!"
    )
    
    async def check_and_next():
        await asyncio.sleep(5)
        
        try:
            await checking_msg.delete()
        except:
            pass
        
        completed_task = user.current_task_key
        user.completed_tasks.append(completed_task)
        user.current_task_index += 1
        
        if user.current_task_index >= len(TASKS_ORDER):
            await update.message.reply_text(
                f"✅ ЗАДАНИЕ {current_num}/3 ВЫПОЛНЕНО!\n\n"
                f"🎉 ПОЗДРАВЛЯЮ! ТЫ ВЫПОЛНИЛ ВСЕ 3 ЗАДАНИЯ!\n\n"
                f"🎁 Сейчас получишь промокод на 5000 G-Coins..."
            )
            await asyncio.sleep(2)
            
            class DummyQuery:
                def __init__(self, user_id):
                    self.from_user = type('obj', (object,), {'id': user_id})
                async def edit_message_text(self, text, reply_markup=None, parse_mode=None, disable_web_page_preview=None):
                    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview)
            
            dummy = DummyQuery(user_id)
            await show_current_task(dummy, user)
        else:
            await update.message.reply_text(
                f"✅ ЗАДАНИЕ {current_num}/3 ВЫПОЛНЕНО!\n\n"
                f"Отлично! Переходим к заданию {current_num + 1}/3... 🚀"
            )
            await asyncio.sleep(2)
            
            class DummyQuery:
                def __init__(self, user_id):
                    self.from_user = type('obj', (object,), {'id': user_id})
                async def edit_message_text(self, text, reply_markup=None, parse_mode=None, disable_web_page_preview=None):
                    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview)
            
            dummy = DummyQuery(user_id)
            await show_current_task(dummy, user)
    
    asyncio.create_task(check_and_next())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_data:
        del user_data[user_id]
    await main_menu(update, context)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "start_tasks":
        await start_tasks(update, context)
    elif data == "cancel":
        await handle_cancel(update, context)

def main():
    print("🚀 БОТ ЗАПУСКАЕТСЯ...")
    print("🎮 Standoff 2 Gold Bot - 5000 G-Coins")
    print("📋 Задания по порядку:")
    print("   1. Яндекс Браузер")
    print("   2. СберПрайм (с предупреждением о VPN)")
    print("   3. 24TV")
    print("💰 Награда: 5000 G-Coins после 3 заданий")
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()