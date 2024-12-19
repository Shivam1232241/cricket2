import importlib
import time
import random
import re
import asyncio
import sqlite3
from html import escape
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters

from shivu import shivuu, application, SUPPORT_CHAT, UPDATE_CHAT, LOGGER
from shivu.modules import ALL_MODULES

# Local SQLite Database Setup
conn = sqlite3.connect('local_database.db')
cursor = conn.cursor()

locks = {}
message_counters = {}
spam_counters = {}
last_characters = {}
sent_characters = {}
first_correct_guesses = {}
message_counts = {}

for module_name in ALL_MODULES:
    imported_module = importlib.import_module("shivu.modules." + module_name)

last_user = {}
warned_users = {}

def escape_markdown(text):
    escape_chars = r'\*_`\\~>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)

async def message_counter(update: Update, context: CallbackContext) -> None:
    chat_id = str(update.effective_chat.id)
    user_id = update.effective_user.id

    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()
    lock = locks[chat_id]

    async with lock:
        cursor.execute("SELECT message_frequency FROM user_totals_lmaoooo WHERE chat_id = ?", (chat_id,))
        chat_frequency = cursor.fetchone()
        if chat_frequency:
            message_frequency = chat_frequency[0] if chat_frequency[0] else 100
        else:
            message_frequency = 100

        if chat_id in last_user and last_user[chat_id]['user_id'] == user_id:
            last_user[chat_id]['count'] += 1
            if last_user[chat_id]['count'] >= 10:
                if user_id in warned_users and time.time() - warned_users[user_id] < 600:
                    return
                else:
                    await update.message.reply_text(f"⚠️ Don't Spam {update.effective_user.first_name}...\nYour Messages Will be ignored for 10 Minutes...")
                    warned_users[user_id] = time.time()
                    return
        else:
            last_user[chat_id] = {'user_id': user_id, 'count': 1}

        if chat_id in message_counts:
            message_counts[chat_id] += 1
        else:
            message_counts[chat_id] = 1

        if message_counts[chat_id] % message_frequency == 0:
            await send_image(update, context)
            message_counts[chat_id] = 0

async def send_image(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    cursor.execute("SELECT * FROM anime_characters_lol")
    all_characters = cursor.fetchall()

    if chat_id not in sent_characters:
        sent_characters[chat_id] = []

    if len(sent_characters[chat_id]) == len(all_characters):
        sent_characters[chat_id] = []

    character = random.choice([c for c in all_characters if c[0] not in sent_characters[chat_id]])

    sent_characters[chat_id].append(character[0])
    last_characters[chat_id] = {'id': character[0], 'name': character[1], 'anime': character[2], 'rarity': character[3], 'img_url': character[4]}

    if chat_id in first_correct_guesses:
        del first_correct_guesses[chat_id]

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character[4],
        caption=f"""A New {character[3]} Character Appeared...\n/guess Character Name and add in Your Harem""",
        parse_mode='Markdown')

async def guess(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in last_characters:
        return

    if chat_id in first_correct_guesses:
        await update.message.reply_text(f'❌️ Already Guessed By Someone.. Try Next Time Bruhh ')
        return

    guess = ' '.join(context.args).lower() if context.args else ''

    if "()" in guess or "&" in guess.lower():
        await update.message.reply_text("Nahh You Can't use This Types of words in your guess..❌️")
        return

    name_parts = last_characters[chat_id]['name'].lower().split()

    if sorted(name_parts) == sorted(guess.split()) or any(part == guess for part in name_parts):

        first_correct_guesses[chat_id] = user_id
        
        cursor.execute("SELECT * FROM user_collection_lmaoooo WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        if user:
            update_fields = {}
            if hasattr(update.effective_user, 'username') and update.effective_user.username != user[2]:
                update_fields['username'] = update.effective_user.username
            if update.effective_user.first_name != user[1]:
                update_fields['first_name'] = update.effective_user.first_name
            if update_fields:
                cursor.execute("UPDATE user_collection_lmaoooo SET username = ?, first_name = ? WHERE user_id = ?", 
                               (update_fields['username'], update_fields['first_name'], user_id))
            cursor.execute("INSERT INTO user_collection_lmaoooo (user_id, collection_data) VALUES (?, ?)", (user_id, str(last_characters[chat_id])))
            conn.commit()
        elif hasattr(update.effective_user, 'username'):
            cursor.execute("INSERT INTO user_collection_lmaoooo (user_id, username, first_name, collection_data) VALUES (?, ?, ?, ?)", 
                           (user_id, update.effective_user.username, update.effective_user.first_name, str(last_characters[chat_id])))
            conn.commit()

        cursor.execute("SELECT * FROM group_user_totalsssssss WHERE user_id = ? AND group_id = ?", (user_id, chat_id))
        group_user_total = cursor.fetchone()
        if group_user_total:
            update_fields = {}
            if hasattr(update.effective_user, 'username') and update.effective_user.username != group_user_total[3]:
                update_fields['username'] = update.effective_user.username
            if update.effective_user.first_name != group_user_total[2]:
                update_fields['first_name'] = update.effective_user.first_name
            if update_fields:
                cursor.execute("UPDATE group_user_totalsssssss SET username = ?, first_name = ? WHERE user_id = ? AND group_id = ?", 
                               (update_fields['username'], update_fields['first_name'], user_id, chat_id))
            cursor.execute("UPDATE group_user_totalsssssss SET total_count = total_count + 1 WHERE user_id = ? AND group_id = ?", (user_id, chat_id))
            conn.commit()
        else:
            cursor.execute("INSERT INTO group_user_totalsssssss (user_id, group_id, username, first_name, total_count) VALUES (?, ?, ?, ?, ?)", 
                           (user_id, chat_id, update.effective_user.username, update.effective_user.first_name, 1))
            conn.commit()

        cursor.execute("SELECT * FROM top_global_groups WHERE group_id = ?", (chat_id,))
        group_info = cursor.fetchone()
        if group_info:
            update_fields = {}
            if update.effective_chat.title != group_info[2]:
                update_fields['group_name'] = update.effective_chat.title
            if update_fields:
                cursor.execute("UPDATE top_global_groups SET group_name = ? WHERE group_id = ?", (update_fields['group_name'], chat_id))
            cursor.execute("UPDATE top_global_groups SET total_score = total_score + 1 WHERE group_id = ?", (chat_id,))
            conn.commit()
        else:
            cursor.execute("INSERT INTO top_global_groups (group_id, group_name, total_score) VALUES (?, ?, ?)", 
                           (chat_id, update.effective_chat.title, 1))
            conn.commit()

        keyboard = [[InlineKeyboardButton(f"See Harem", switch_inline_query_current_chat=f"collection.{user_id}")]]
        
        await update.message.reply_text(
            f'<b><a href="tg://user?id={user_id}">{escape(update.effective_user.first_name)}</a></b> You Guessed a New Character ✅️ \n\n𝗡𝗔𝗠𝗘: <b>{last_characters[chat_id]["name"]}</b> \n𝗔𝗡𝗜𝗠𝗘: <b>{last_characters[chat_id]["anime"]}</b> \n𝗥𝗔𝗜𝗥𝗧𝗬: <b>{last_characters[chat_id]["rarity"]}</b>\n\nThis Character added in Your harem.. use /harem To see your harem', 
            parse_mode='HTML', 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text('Please Write Correct Character Name... ❌️')

async def fav(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text('Please provide Character id...')
        return

    character_id = context.args[0]

    cursor.execute("SELECT * FROM user_collection_lmaoooo WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        await update.message.reply_text('You have not Guessed any characters yet....')
        return

    characters = eval(user[4])
    character = next((c for c in characters if c['id'] == character_id), None)
    if not character:
        await update.message.reply_text('This Character is Not In your collection')
        return

    cursor.execute("UPDATE user_collection_lmaoooo SET favorites = ? WHERE user_id = ?", (character_id, user_id))
    conn.commit()

    await update.message.reply_text(f'Character {character["name"]} has been added to your favorite...')

def main() -> None:
    """Run bot."""
    application.add_handler(CommandHandler(["guess", "protecc", "collect", "grab", "hunt"], guess, block=False))
    application.add_handler(CommandHandler("fav", fav, block=False))
    application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))

    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    shivuu.start()
    LOGGER.info("Bot started")
    main()
