import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

TOKEN = os.getenv("TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

cooldowns = {}
COOLDOWN_TIME = 1800
blocked_users = {}

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Привет! Отправь мне свою идею.")

async def is_admin(chat_id: int, user_id: int) -> bool:
    chat_member = await bot.get_chat_member(chat_id, user_id)
    return chat_member.status in ["administrator", "creator"]

@dp.message(Command("block"))
async def block_user(message: types.Message):
    if not await is_admin(GROUP_CHAT_ID, message.from_user.id):
        await message.answer("У тебя нет прав на это!")
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Использование: /block <user_id> <причина>")
        return

    user_id, reason = args[1], args[2]
    blocked_users[int(user_id)] = reason
    await message.answer(f"Пользователь {user_id} заблокирован. Причина: {reason}")

@dp.message(Command("unblock"))
async def unblock_user(message: types.Message):
    if not await is_admin(GROUP_CHAT_ID, message.from_user.id):
        await message.answer("У тебя нет прав на это!")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /unblock <user_id>")
        return

    user_id = int(args[1])
    if user_id in blocked_users:
        del blocked_users[user_id]
        await message.answer(f"Пользователь {user_id} разблокирован.")
    else:
        await message.answer("Этот пользователь не был заблокирован.")

@dp.message()
async def handle_idea(message: types.Message):
    if message.text and message.text.startswith("/"):
        return

    user_id = message.from_user.id
    if user_id in blocked_users:
        await message.answer(f"Ты заблокирован. Причина: {blocked_users[user_id]}")
        return

    username = f"(@{message.from_user.username})" if message.from_user.username else ""
    user_info = f"{message.from_user.full_name} {username} [ID: {user_id}]".strip()

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
        caption = f"Новая идея от {user_info}:\n\n{message.caption or ''}"
        await bot.send_photo(GROUP_CHAT_ID, photo=photo_id, caption=caption, reply_markup=keyboard)
    else:
        await bot.send_message(GROUP_CHAT_ID, f"Новая идея от {user_info}:\n\n{message.text}", reply_markup=keyboard)

    await message.answer("Твоя идея отправлена в группу на рассмотрение!")

@dp.callback_query()
async def process_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    action, idea_sender_id = callback.data.split("_")
    idea_sender_id = int(idea_sender_id)

    if not await is_admin(GROUP_CHAT_ID, user_id):
        await callback.answer("У тебя нет прав на это!", show_alert=True)
        return

    if action == "approve":
        await bot.send_message(idea_sender_id, "Твоя идея одобрена!")
    elif action == "deny":
        await bot.send_message(idea_sender_id, "К сожалению, твоя идея отклонена.")

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
