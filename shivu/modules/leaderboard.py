import os
import random
import html
import sqlite3

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from shivu import application, PHOTO_URL, OWNER_ID, sudo_users as SUDO_USERS

# SQLite database connection function
def get_db_connection():
    conn = sqlite3.connect('local_database.db')
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

# Helper function to fetch global leaderboard data
async def global_leaderboard(update: Update, context: CallbackContext) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT group_name, count FROM top_global_groups ORDER BY count DESC LIMIT 10")
    leaderboard_data = cursor.fetchall()
    conn.close()

    leaderboard_message = "<b>TOP 10 GROUPS WHO GUESSED MOST CHARACTERS</b>\n\n"
    for i, group in enumerate(leaderboard_data, start=1):
        group_name = html.escape(group['group_name'])

        if len(group_name) > 10:
            group_name = group_name[:15] + '...'
        count = group['count']
        leaderboard_message += f'{i}. <b>{group_name}</b> ➾ <b>{count}</b>\n'

    photo_url = random.choice(PHOTO_URL)
    await update.message.reply_photo(photo=photo_url, caption=leaderboard_message, parse_mode='HTML')

# Helper function to fetch top users in a specific group
async def ctop(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT username, first_name, character_count FROM group_user_totals
        WHERE group_id = ? ORDER BY character_count DESC LIMIT 10
    """, (chat_id,))
    leaderboard_data = cursor.fetchall()
    conn.close()

    leaderboard_message = "<b>TOP 10 USERS WHO GUESSED CHARACTERS MOST TIME IN THIS GROUP..</b>\n\n"
    for i, user in enumerate(leaderboard_data, start=1):
        username = user['username'] if user['username'] else 'Unknown'
        first_name = html.escape(user['first_name'] or 'Unknown')

        if len(first_name) > 10:
            first_name = first_name[:15] + '...'
        character_count = user['character_count']
        leaderboard_message += f'{i}. <a href="https://t.me/{username}"><b>{first_name}</b></a> ➾ <b>{character_count}</b>\n'

    photo_url = random.choice(PHOTO_URL)
    await update.message.reply_photo(photo=photo_url, caption=leaderboard_message, parse_mode='HTML')

# Helper function to fetch leaderboard data for users
async def leaderboard(update: Update, context: CallbackContext) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT username, first_name, COUNT(character_id) AS character_count FROM user_characters
        JOIN users ON users.id = user_characters.user_id
        GROUP BY user_id ORDER BY character_count DESC LIMIT 10
    """)
    leaderboard_data = cursor.fetchall()
    conn.close()

    leaderboard_message = "<b>TOP 10 USERS WITH MOST CHARACTERS</b>\n\n"
    for i, user in enumerate(leaderboard_data, start=1):
        username = user['username'] if user['username'] else 'Unknown'
        first_name = html.escape(user['first_name'] or 'Unknown')

        if len(first_name) > 10:
            first_name = first_name[:15] + '...'
        character_count = user['character_count']
        leaderboard_message += f'{i}. <a href="https://t.me/{username}"><b>{first_name}</b></a> ➾ <b>{character_count}</b>\n'

    photo_url = random.choice(PHOTO_URL)
    await update.message.reply_photo(photo=photo_url, caption=leaderboard_message, parse_mode='HTML')

# Helper function for stats (admin only)
async def stats(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT group_id) FROM group_user_totals")
    group_count = cursor.fetchone()[0]

    conn.close()

    await update.message.reply_text(f'Total Users: {user_count}\nTotal groups: {group_count}')

# Helper function to send the list of users (admin only)
async def send_users_document(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in SUDO_USERS:
        update.message.reply_text('Only For Sudo users...')
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT first_name FROM users")
    users = cursor.fetchall()
    conn.close()

    user_list = "\n".join([user['first_name'] for user in users])

    with open('users.txt', 'w') as f:
        f.write(user_list)
    with open('users.txt', 'rb') as f:
        await context.bot.send_document(chat_id=update.effective_chat.id, document=f)
    os.remove('users.txt')

# Helper function to send the list of groups (admin only)
async def send_groups_document(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in SUDO_USERS:
        update.message.reply_text('Only For Sudo users...')
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT group_name FROM top_global_groups")
    groups = cursor.fetchall()
    conn.close()

    group_list = "\n".join([group['group_name'] for group in groups])

    with open('groups.txt', 'w') as f:
        f.write(group_list)
    with open('groups.txt', 'rb') as f:
        await context.bot.send_document(chat_id=update.effective_chat.id, document=f)
    os.remove('groups.txt')


# Add the command handlers
application.add_handler(CommandHandler('ctop', ctop, block=False))
application.add_handler(CommandHandler('stats', stats, block=False))
application.add_handler(CommandHandler('TopGroups', global_leaderboard, block=False))
application.add_handler(CommandHandler('list', send_users_document, block=False))
application.add_handler(CommandHandler('groups', send_groups_document, block=False))
application.add_handler(CommandHandler('top', leaderboard, block=False))
