import sqlite3
from telegram import Update
from itertools import groupby
import math
from html import escape
import random

from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from shivu import application  # Assuming 'application' is already initialized

# SQLite database connection
def get_db_connection():
    conn = sqlite3.connect('local_database.db')
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

# Create tables (ensure this is run only once during setup)
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            first_name TEXT,
            characters TEXT,
            favorites TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Ensure the tables are created
create_tables()

# Fetch user data from the SQLite database
def get_user_data(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

# Update user characters in the SQLite database
def update_user_characters(user_id, characters):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET characters = ? WHERE id = ?', (characters, user_id))
    conn.commit()
    conn.close()

# Get user favorites from the SQLite database
def get_user_favorites(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT favorites FROM users WHERE id = ?', (user_id,))
    favorites = cursor.fetchone()
    conn.close()
    return favorites['favorites'] if favorites else None

# The main harem function
async def harem(update: Update, context: CallbackContext, page=0) -> None:
    user_id = update.effective_user.id

    user = get_user_data(user_id)
    if not user:
        if update.message:
            await update.message.reply_text('You Have Not Guessed any Characters Yet..')
        else:
            await update.callback_query.edit_message_text('You Have Not Guessed any Characters Yet..')
        return

    characters = sorted(eval(user['characters']), key=lambda x: (x['anime'], x['id']))  # Convert string back to list

    character_counts = {k: len(list(v)) for k, v in groupby(characters, key=lambda x: x['id'])}

    unique_characters = list({character['id']: character for character in characters}.values())

    total_pages = math.ceil(len(unique_characters) / 15)

    if page < 0 or page >= total_pages:
        page = 0

    harem_message = f"<b>{escape(update.effective_user.first_name)}'s Harem - Page {page+1}/{total_pages}</b>\n"

    current_characters = unique_characters[page*15:(page+1)*15]

    current_grouped_characters = {k: list(v) for k, v in groupby(current_characters, key=lambda x: x['anime'])}

    for anime, characters in current_grouped_characters.items():
        harem_message += f'\n<b>{anime} {len(characters)}/{len([c for c in characters if c["anime"] == anime])}</b>\n'

        for character in characters:
            count = character_counts[character['id']]
            harem_message += f'{character["id"]} {character["name"]} ×{count}\n'

    total_count = len(user['characters'])

    keyboard = [[InlineKeyboardButton(f"See Collection ({total_count})", switch_inline_query_current_chat=f"collection.{user_id}")]]

    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"harem:{page-1}:{user_id}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"harem:{page+1}:{user_id}"))
        keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)

    if 'favorites' in user and user['favorites']:
        fav_character_id = user['favorites'][0]
        fav_character = next((c for c in user['characters'] if c['id'] == fav_character_id), None)

        if fav_character and 'img_url' in fav_character:
            if update.message:
                await update.message.reply_photo(photo=fav_character['img_url'], parse_mode='HTML', caption=harem_message, reply_markup=reply_markup)
            else:
                if update.callback_query.message.caption != harem_message:
                    await update.callback_query.edit_message_caption(caption=harem_message, reply_markup=reply_markup, parse_mode='HTML')
        else:
            if update.message:
                await update.message.reply_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)
            else:
                if update.callback_query.message.text != harem_message:
                    await update.callback_query.edit_message_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)
    else:
        if user['characters']:
            random_character = random.choice(user['characters'])

            if 'img_url' in random_character:
                if update.message:
                    await update.message.reply_photo(photo=random_character['img_url'], parse_mode='HTML', caption=harem_message, reply_markup=reply_markup)
                else:
                    if update.callback_query.message.caption != harem_message:
                        await update.callback_query.edit_message_caption(caption=harem_message, reply_markup=reply_markup, parse_mode='HTML')
            else:
                if update.message:
                    await update.message.reply_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)
                else:
                    if update.callback_query.message.text != harem_message:
                        await update.callback_query.edit_message_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)
        else:
            if update.message:
                await update.message.reply_text("Your List is Empty :)")

# Callback for harem navigation
async def harem_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    data = query.data
    _, page, user_id = data.split(':')

    page = int(page)
    user_id = int(user_id)

    if query.from_user.id != user_id:
        await query.answer("It's not your harem", show_alert=True)
        return

    await harem(update, context, page)

# Handlers for commands and callbacks
application.add_handler(CommandHandler(["harem", "collection"], harem, block=False))
application.add_handler(CallbackQueryHandler(harem_callback, pattern='^harem', block=False))
