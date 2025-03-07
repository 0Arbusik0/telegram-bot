import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

TOKEN = os.getenv("TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")

if not TOKEN or not GROUP_CHAT_ID:
    raise ValueError("Переменные окружения TOKEN не установлены!")

if not GROUP_CHAT_ID:
    raise ValueError("Переменные окружения GROUP_CHAT_ID не установлены!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

cooldowns = {}
COOLDOWN_TIME = 1800
blocked_users = {}

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Привет! Отправь мне свою идею!")

async def is_admin(chat_id: int, user_id: int) -> bool:
    chat_member = await bot.get_chat_member(chat_id, user_id)
    return chat_member.status in ["administrator", "creator"]

@dp.message(Command("block"))
async def block_user(message: types.Message):
    if not await is_admin(GROUP_CHAT_ID, message.from_user.id):
        await message.answer("У вас нет прав для этого!")
        return

    command_parts = message.text.split(maxsplit=2)
    if len(command_parts) < 3:
        await message.answer("Использование: /block <user_id> <причина>")
        return

    user_id, reason = command_parts[1], command_parts[2]
    
    try:
        user_id = int(user_id)
    except ValueError:
        await message.answer("ID пользователя должен быть числом!")
        return

    blocked_users[user_id] = reason
    await message.answer(f"Пользователь {user_id} заблокирован по причине: {reason}")

@dp.message(Command("unblock"))
async def unblock_user(message: types.Message):
    if not await is_admin(GROUP_CHAT_ID, message.from_user.id):
        await message.answer("У вас нет прав для этого!")
        return

    command_parts = message.text.split(maxsplit=1)
    if len(command_parts) < 2:
        await message.answer("Использование: /unblock <user_id>")
        return

    try:
        user_id = int(command_parts[1])
    except ValueError:
        await message.answer("ID пользователя должен быть числом!")
        return

    if user_id in blocked_users:
        del blocked_users[user_id]
        await message.answer(f"Пользователь {user_id} разблокирован!")
    else:
        await message.answer("Этот пользователь не в блокировке.")

@dp.message()
async def handle_idea(message: types.Message):
    if message.text and message.text.startswith("/"):
        return

    user_id = message.from_user.id

    if user_id in blocked_users:
        await message.answer(f"Вы заблокированы! Причина: {blocked_users[user_id]}")
        return

    username = f"(@{message.from_user.username})" if message.from_user.username else ""
    user_full_name = f"{message.from_user.full_name} {username} [ID: {user_id}]".strip()

    current_time = asyncio.get_event_loop().time()
    
    if user_id in cooldowns and cooldowns[user_id] > current_time:
        remaining_time = int(cooldowns[user_id] - current_time)
        minutes, seconds = divmod(remaining_time, 60)
        await message.answer(f"Подожди {minutes:02}:{seconds:02} перед отправкой новой идеи!")
        return

    cooldowns[user_id] = current_time + COOLDOWN_TIME

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{user_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"deny_{user_id}")]
    ])

    if message.photo:
        photo_id = message.photo[-1].file_id
        await bot.send_photo(GROUP_CHAT_ID, photo=photo_id, caption=f"Новая идея от {user_full_name}:\n\n{message.caption or '(Без текста)'}", reply_markup=keyboard)
    else:
        await bot.send_message(GROUP_CHAT_ID, f"Новая идея от {user_full_name}:\n\n{message.text}", reply_markup=keyboard)

    await message.answer("Твоя идея отправлена в группу на рассмотрение!")

@dp.callback_query()
async def process_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    action, idea_sender_id = callback.data.split("_")
    idea_sender_id = int(idea_sender_id)

    if not await is_admin(GROUP_CHAT_ID, user_id):
        await callback.answer("У вас нет прав для этого действия!", show_alert=True)
        return

    try:
        if action == "approve":
            await bot.send_message(idea_sender_id, "Твоя идея одобрена!")
        elif action == "deny":
            await bot.send_message(idea_sender_id, "К сожалению, твоя идея отклонена.")

        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer()
    except TelegramBadRequest:
        await callback.answer("Ошибка: пользователь, возможно, заблокировал бота.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
