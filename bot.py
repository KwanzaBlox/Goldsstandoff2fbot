import os
import logging
import asyncio
import random
import string
from typing import Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ТОКЕН ПРЯМО В КОДЕ
TOKEN = "8445466695:AAGORyjHM8ghSs2jhKblwwrO0-aJNp6Zuq8"

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Словарь для хранения состояний пользователей
user_data: Dict[int, Dict] = {}

# Задания
TASKS = {
    1: {
        "200": {
            "tasks": ["yandex"],
            "rewards": 200,
            "task_count": 1
        },
        "1000": {
            "tasks": ["yandex", "sberprime"],
            "rewards": 1000,
            "task_count": 2
        },
        "5000": {
            "tasks": ["yandex", "sberprime", "24tv"],
            "rewards": 5000,
            "task_count": 3
        }
    }
}

# Ссылки на задания
TASK_LINKS = {
    "yandex": "https://vk.cc/cVUvvJ",
    "sberprime": "https://vk.cc/cVUvEb",
    "24tv": "https://vk.cc/cVUwtW"
}

TASK_NAMES = {
    "yandex": "Скачать Яндекс Браузер",
    "sberprime": "Оформить подписку СберПрайм за 1 рубль",
    "24tv": "Активировать промокод в сервисе 24TV"
}

# Функция для генерации промокода
def generate_promo_code() -> str:
    characters = string.ascii_letters + string.digits
    length = random.randint(9, 12)
    return ''.join(random.choice(characters) for _ in range(length))

# Класс для управления состоянием пользователя
class UserState:
    def __init__(self, user_id: int, username: str):
        self.user_id = user_id
        self.username = username
        self.selected_reward = None
        self.completed_tasks = []
        self.waiting_for_screenshot = False
        self.current_task_index = 0
        self.screenshot_task = None
        self.promo_code = None
        self.reward_claimed = False
        self.completed = False
        self.screenshot_check_task = None

    def reset(self):
        self.selected_reward = None
        self.completed_tasks = []
        self.waiting_for_screenshot = False
        self.current_task_index = 0
        self.screenshot_task = None
        self.promo_code = None
        self.reward_claimed = False
        self.completed = False
        if self.screenshot_check_task:
            self.screenshot_check_task.cancel()

# Главное меню
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int = None):
    if user_id is None:
        user_id = update.effective_user.id
    
    keyboard = [
        [InlineKeyboardButton("200 G-Coins", callback_data="reward_200")],
        [InlineKeyboardButton("1000 G-Coins", callback_data="reward_1000")],
        [InlineKeyboardButton("5000 G-Coins", callback_data="reward_5000")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    user = update.effective_user
    welcome_text = (
        f"🎮 ПОЛУЧИ ГОЛДУ STANDOFF 2 БЕСПЛАТНО! 🎮\n\n"
        f"Привет, {user.first_name}! 👋\n\n"
        f"Активируй скрытый промокод разработчиков.\n\n"
        f"💰 Выбери сколько хочешь получить:\n"
        f"   1️⃣ 200 G-Coins\n"
        f"   2️⃣ 1000 G-Coins\n"
        f"   3️⃣ 5000 G-Coins\n"
        f"👇 Нажми на кнопку:"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=welcome_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            text=welcome_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

# Обработчик выбора награды
async def handle_reward_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    reward_key = query.data.split("_")[1]
    
    if user_id not in user_data:
        user_data[user_id] = UserState(user_id, query.from_user.username)
    
    user = user_data[user_id]
    
    if user.reward_claimed:
        await query.edit_message_text(
            text="❌ Вы уже получили награду! Нельзя пройти задания повторно.",
            parse_mode=ParseMode.HTML
        )
        return
    
    if user.selected_reward is not None and not user.completed:
        await query.edit_message_text(
            text="⚠️ У вас уже есть активное задание. Пожалуйста, завершите его или начните заново командой /start",
            parse_mode=ParseMode.HTML
        )
        return
    
    user.selected_reward = reward_key
    user.completed_tasks = []
    user.current_task_index = 0
    user.completed = False
    
    await start_next_task(query, user, reward_key)

async def start_next_task(query, user: UserState, reward_key: str):
    tasks_list = TASKS[1][reward_key]["tasks"]
    
    if user.current_task_index >= len(tasks_list):
        user.promo_code = generate_promo_code()
        user.reward_claimed = True
        user.completed = True
        
        reward_amount = TASKS[1][reward_key]["rewards"]
        
        await query.edit_message_text(
            text=f"✅ Поздравляем! Вы выполнили все задания!\n\n"
                 f"🎁 Ваш промокод на {reward_amount} G-Coins:\n"
                 f"<code>{user.promo_code}</code>\n\n"
                 f"🔑 Активируйте его в игре Standoff 2 и получите голду!\n\n"
                 f"Спасибо за участие! 🎮",
            parse_mode=ParseMode.HTML
        )
        return
    
    task_key = tasks_list[user.current_task_index]
    task_name = TASK_NAMES[task_key]
    task_link = TASK_LINKS[task_key]
    
    task_number = user.current_task_index + 1
    
    text = (
        f"📋 <b>Задание {task_number}</b>\n\n"
        f"{task_name}\n\n"
        f"🔗 <a href='{task_link}'>Выполнить задание</a>\n\n"
        f"📸 После выполнения отправьте скриншот подтверждения.\n"
        f"⏱ Проверка займет 5 секунд."
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Отмена", callback_data="cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    user.waiting_for_screenshot = True
    user.screenshot_task = task_key
    
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
        user_data[user_id].reset()
        del user_data[user_id]
    
    await main_menu(update, context, user_id)

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_data:
        await update.message.reply_text("❌ Сначала выберите награду в меню /start")
        return
    
    user = user_data[user_id]
    
    if not user.waiting_for_screenshot:
        await update.message.reply_text("❌ Сейчас вы не должны отправлять скриншот. Используйте /start для начала.")
        return
    
    photo = update.message.photo[-1]
    user.waiting_for_screenshot = False
    
    checking_msg = await update.message.reply_text(
        "⏳ Проверка скриншота... Подождите 5 секунд.\n"
        "Пожалуйста, не отправляйте новые сообщения."
    )
    
    async def check_screenshot():
        await asyncio.sleep(5)
        
        try:
            await checking_msg.delete()
        except:
            pass
        
        user.completed_tasks.append(user.screenshot_task)
        user.current_task_index += 1
        
        success_msg = await update.message.reply_text(
            "✅ Скриншот принят! Задание выполнено.\n"
            "Переходим к следующему заданию..."
        )
        
        await asyncio.sleep(2)
        await success_msg.delete()
        
        class DummyQuery:
            def __init__(self, user_id):
                self.from_user = type('obj', (object,), {'id': user_id})
            
            async def edit_message_text(self, text, parse_mode=None, reply_markup=None):
                await update.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup, disable_web_page_preview=True)
        
        dummy_query = DummyQuery(user_id)
        await start_next_task(dummy_query, user, user.selected_reward)
    
    asyncio.create_task(check_screenshot())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in user_data:
        user_data[user_id].reset()
        del user_data[user_id]
    
    await main_menu(update, context)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data.startswith("reward_"):
        await handle_reward_selection(update, context)
    elif data == "cancel":
        await handle_cancel(update, context)

def main():
    print("🚀 Бот запускается...")
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()