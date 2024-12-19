import re
import time
from html import escape
from cachetools import TTLCache
import sqlite3

from telegram import Update, InlineQueryResultPhoto
from telegram.ext import InlineQueryHandler, CallbackContext, CommandHandler
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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY,
            name TEXT,
            anime TEXT,
            rarity TEXT,
            img_url TEXT
        )
    ''')

    conn.commit()
    conn.close()

# Ensure the tables are created
create_tables()

# Caching
all_characters_cache = TTLCache(maxsize=10000, ttl=36000)
user_collection_cache = TTLCache(maxsize=10000, ttl=60)

# Fetch user data from the SQLite database
def get_user_data(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

# Fetch characters from the SQLite database
def get_characters(query=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    if query:
        regex = f'%{query}%'
        cursor.execute('SELECT * FROM characters WHERE name LIKE ? OR anime LIKE ?', (regex, regex))
    else:
        cursor.execute('SELECT * FROM characters')

    characters = cursor.fetchall()
    conn.close()
    return characters

# Inline query handler
async def inlinequery(update: Update, context: CallbackContext) -> None:
    query = update.inline_query.query
    offset = int(update.inline_query.offset) if update.inline_query.offset else 0

    if query.startswith('collection.'):
        user_id, *search_terms = query.split(' ')[0].split('.')[1], ' '.join(query.split(' ')[1:])
        if user_id.isdigit():
            if user_id in user_collection_cache:
                user = user_collection_cache[user_id]
            else:
                user = get_user_data(int(user_id))
                user_collection_cache[user_id] = user

            if user:
                # Assuming characters are stored as a string in the 'characters' field
                all_characters = eval(user['characters'])  # Converting string back to list
                if search_terms:
                    regex = re.compile(' '.join(search_terms), re.IGNORECASE)
                    all_characters = [character for character in all_characters if regex.search(character['name']) or regex.search(character['anime'])]
            else:
                all_characters = []
        else:
            all_characters = []
    else:
        if query:
            all_characters = get_characters(query)
        else:
            if 'all_characters' in all_characters_cache:
                all_characters = all_characters_cache['all_characters']
            else:
                all_characters = get_characters()
                all_characters_cache['all_characters'] = all_characters

    characters = all_characters[offset:offset+50]
    if len(characters) > 50:
        characters = characters[:50]
        next_offset = str(offset + 50)
    else:
        next_offset = str(offset + len(characters))

    results = []
    for character in characters:
        global_count = 0  # Replace this with actual counting logic for user characters (if needed)
        anime_characters = len([c for c in all_characters if c['anime'] == character['anime']])

        if query.startswith('collection.'):
            user_character_count = sum(c['id'] == character['id'] for c in user['characters'])
            user_anime_characters = sum(c['anime'] == character['anime'] for c in user['characters'])
            caption = f"<b> Look At <a href='tg://user?id={user['id']}'>{(escape(user.get('first_name', user['id'])))}</a>'s Character</b>\n\n🌸: <b>{character['name']} (x{user_character_count})</b>\n🏖️: <b>{character['anime']} ({user_anime_characters}/{anime_characters})</b>\n<b>{character['rarity']}</b>\n\n<b>🆔️:</b> {character['id']}"
        else:
            caption = f"<b>Look At This Character !!</b>\n\n🌸:<b> {character['name']}</b>\n🏖️: <b>{character['anime']}</b>\n<b>{character['rarity']}</b>\n🆔️: <b>{character['id']}</b>\n\n<b>Globally Guessed {global_count} Times...</b>"

        results.append(
            InlineQueryResultPhoto(
                thumbnail_url=character['img_url'],
                id=f"{character['id']}_{time.time()}",
                photo_url=character['img_url'],
                caption=caption,
                parse_mode='HTML'
            )
        )

    await update.inline_query.answer(results, next_offset=next_offset, cache_time=5)

# Add handler for inline query
application.add_handler(InlineQueryHandler(inlinequery, block=False))
