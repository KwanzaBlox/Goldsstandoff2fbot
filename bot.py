import os
import logging
import asyncio
import random
import string
from typing import Dict
from datetime import datetime

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
TASKS_ORDER = ["yandex", "sberprime", "tv24"]

# ИНФОРМАЦИЯ О ЗАДАНИЯХ
TASK_INFO = {
    "yandex": {
        "name": "📱 СКАЧАТЬ ЯНДЕКС БРАУЗЕР",
        "description": "Скачай Яндекс Браузер по ссылке и установи",
        "link": "https://vk.cc/cVUvvJ",
        "button": "🔽 СКАЧАТЬ ЯНДЕКС БРАУЗЕР"
    },
    "sberprime": {
        "name": "💳 СБЕРПРАЙМ ЗА 1 РУБЛЬ",
        "description": "Оформи подписку СберПрайм за 1 рубль\n(если ссылка не открывается, выключи VPN)",
        "link": "https://vk.cc/cVUvEb",
        "button": "💳 ОФОРМИТЬ СБЕРПРАЙМ"
    },
    "tv24": {
        "name": "🎬 АКТИВИРОВАТЬ ПРОМОКОД 24TV",
        "description": "Перейди по ссылке и активируй промокод",
        "link": "https://vk.cc/cVUwtW",
        "button": "🎬 АКТИВИРОВАТЬ ПРОМОКОД"
    }
}

def generate_code() -> str:
    """Генерирует код формата XXXX-XXXX-XXXX"""
    chars = string.ascii_uppercase + string.digits
    part1 = ''.join(random.choice(chars) for _ in range(4))
    part2 = ''.join(random.choice(chars) for _ in range(4))
    part3 = ''.join(random.choice(chars) for _ in range(4))
    return f"{part1}-{part2}-{part3}"

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
        self.last_activity = datetime.now()
        self.reminder_sent = False

async def send_reminder(context: ContextTypes.DEFAULT_TYPE, user_id: int, task_name: str, task_num: int):
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"⏰ НАПОМИНАНИЕ!\n\n"
                 f"Ты начал выполнять задания для Standoff 2, но так и не завершил!\n\n"
                 f"📋 Ты остановился на {task_name} (Задание {task_num}/3)\n\n"
                 f"🎁 Не забывай, что за выполнение 3 заданий ты получишь 5000 G-Coins!\n\n"
                 f"👉 Продолжить - просто отправь скриншот для этого задания\n"
                 f"❌ Отменить - нажми /start",
            parse_mode=ParseMode.HTML
        )
        logger.info(f"Напоминание отправлено пользователю {user_id}")
    except Exception as e:
        logger.error(f"Ошибка отправки напоминания {user_id}: {e}")

async def check_reminders(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    to_remove = []
    
    for user_id, user in user_data.items():
        if user.reward_claimed:
            to_remove.append(user_id)
            continue
        
        if user.current_task_index >= len(TASKS_ORDER):
            to_remove.append(user_id)
            continue
        
        time_diff = now - user.last_activity
        hours_passed = time_diff.total_seconds() / 3600
        
        if hours_passed >= 1 and not user.reminder_sent:
            task_key = TASKS_ORDER[user.current_task_index]
            task_name = TASK_INFO[task_key]["name"]
            task_num = user.current_task_index + 1
            
            await send_reminder(context, user_id, task_name, task_num)
            user.reminder_sent = True
        
        elif hours_passed >= 2 and user.reminder_sent:
            task_key = TASKS_ORDER[user.current_task_index]
            task_name = TASK_INFO[task_key]["name"]
            task_num = user.current_task_index + 1
            
            await send_reminder(context, user_id, task_name, task_num)
            user.last_activity = now
    
    for user_id in to_remove:
        if user_id in user_data:
            del user_data[user_id]

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
    user.last_activity = datetime.now()
    user.reminder_sent = False
    
    user_data[user_id] = user
    
    await show_current_task(query, user)

async def show_current_task(query, user: UserState):
    user.last_activity = datetime.now()
    user.reminder_sent = False
    
    if user.current_task_index >= len(TASKS_ORDER):
        user.promo_code = generate_code()
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
    total = len(TASKS_ORDER)
    
    text = (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 ЗАДАНИЕ {current} ИЗ {total}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{task['name']}\n\n"
        f"{task['description']}\n\n"
        f"🔗 <a href='{task['link']}'>👉 {task['button']} 👈</a>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📸 КАК ПОДТВЕРДИТЬ:\n"
        f"После выполнения отправь СКРИНШОТ подтверждения\n"
        f"⏱ Автопроверка займет 5 секунд\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"❌ Отмена - нажми /start\n"
        f"⏰ Если забудешь - я напомню через 1-2 часа!"
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
    
    user.last_activity = datetime.now()
    user.reminder_sent = False
    
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

async def reminder_callback(context: ContextTypes.DEFAULT_TYPE):
    await check_reminders(context)

def main():
    print("🚀 БОТ ЗАПУСКАЕТСЯ...")
    print("🎮 Standoff 2 Bot - 5000 G-Coins")
    print("📋 Задания по порядку:")
    print("   1. Яндекс Браузер")
    print("   2. СберПрайм")
    print("   3. 24TV")
    print("💰 Награда: 5000 G-Coins после 3 заданий")
    print("🎁 Формат промокода: XXXX-XXXX-XXXX")
    print("⏰ Напоминания: через 1 и 2 часа бездействия")
    
    application = Application.builder().token(TOKEN).build()
    
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(reminder_callback, interval=1800, first=60)
        print("✅ Система напоминаний запущена (проверка каждые 30 минут)")
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()