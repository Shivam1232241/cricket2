import sqlite3
from telegram import Update
from telegram.ext import CallbackContext, CommandHandler

from shivu import application, OWNER_ID

# Local SQLite Database Setup
conn = sqlite3.connect('local_database.db')
cursor = conn.cursor()

async def broadcast(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    message_to_broadcast = update.message.reply_to_message

    if message_to_broadcast is None:
        await update.message.reply_text("Please reply to a message to broadcast.")
        return

    # Fetch all group_ids from the top_global_groups table
    cursor.execute("SELECT group_id FROM top_global_groups")
    all_chats = [row[0] for row in cursor.fetchall()]

    # Fetch all user_ids from the total_pm_users table
    cursor.execute("SELECT user_id FROM total_pm_users")
    all_users = [row[0] for row in cursor.fetchall()]

    shuyaa = list(set(all_chats + all_users))

    failed_sends = 0

    for chat_id in shuyaa:
        try:
            await context.bot.forward_message(chat_id=chat_id,
                                              from_chat_id=message_to_broadcast.chat_id,
                                              message_id=message_to_broadcast.message_id)
        except Exception as e:
            print(f"Failed to send message to {chat_id}: {e}")
            failed_sends += 1

    await update.message.reply_text(f"Broadcast complete. Failed to send to {failed_sends} chats/users.")

application.add_handler(CommandHandler("broadcast", broadcast, block=False))
