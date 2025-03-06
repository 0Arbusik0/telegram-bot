import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

TOKEN = "7362733217:AAEF4Ua3t_Nwvf5x6ETERR-S8vlCzKY9c6k"
GROUP_CHAT_ID = -1002499181532

bot = Bot(token=TOKEN)
dp = Dispatcher()

cooldowns = {}
COOLDOWN_TIME = 1800

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Привет! Отправь мне свою идею")

async def is_admin(chat_id: int, user_id: int) -> bool:
    chat_member = await bot.get_chat_member(chat_id, user_id)
    return chat_member.status in ["administrator", "creator"]

@dp.message()
async def handle_idea(message: types.Message):
    if message.text.startswith("/"):
        return

    user_id = message.from_user.id
    username = f"(@{message.from_user.username})" if message.from_user.username else ""
    user_full_name = f"{message.from_user.full_name} {username}".strip()

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

    await bot.send_message(GROUP_CHAT_ID, f"Новая идея от {user_full_name}:\n\n{message.text}", reply_markup=keyboard)
    await message.answer("Твоя идея отправлена в группу на рассмотрение!")

@dp.chat_member()
async def on_user_join(chat_member: types.ChatMemberUpdated):
    if chat_member.new_chat_member.user.is_bot:
        await bot.send_message(chat_member.chat.id, "Привет! Я предложка, готов принимать ваши идеи.")

@dp.callback_query()
async def process_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    action, idea_sender_id = callback.data.split("_")
    idea_sender_id = int(idea_sender_id)

    if not await is_admin(GROUP_CHAT_ID, user_id):
        await callback.answer("У вас нет прав для этого действия!", show_alert=True)
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
