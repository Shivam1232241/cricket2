import json
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3

from shivu import shivuu

# Function to get database connection
def get_db_connection():
    conn = sqlite3.connect('local_database.db')
    conn.row_factory = sqlite3.Row  # Access rows by column name
    return conn

# Helper function to get a user's data
async def get_user_data(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    return user_data

# Helper function to update user's characters
async def update_user_characters(user_id, characters):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET characters = ? WHERE user_id = ?", (json.dumps(characters), user_id))
    conn.commit()
    conn.close()

# Helper function to add a new user
async def add_user(user_id, username, first_name, characters):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (user_id, username, first_name, characters) VALUES (?, ?, ?, ?)",
                   (user_id, username, first_name, json.dumps(characters)))
    conn.commit()
    conn.close()

pending_trades = {}

@shivuu.on_message(filters.command("trade"))
async def trade(client, message):
    sender_id = message.from_user.id

    if not message.reply_to_message:
        await message.reply_text("You need to reply to a user's message to trade a character!")
        return

    receiver_id = message.reply_to_message.from_user.id

    if sender_id == receiver_id:
        await message.reply_text("You can't trade a character with yourself!")
        return

    if len(message.command) != 3:
        await message.reply_text("You need to provide two character IDs!")
        return

    sender_character_id, receiver_character_id = message.command[1], message.command[2]

    sender = await get_user_data(sender_id)
    receiver = await get_user_data(receiver_id)

    if sender:
        sender_characters = json.loads(sender['characters'])
        sender_character = next((character for character in sender_characters if character['id'] == sender_character_id), None)
    else:
        sender_character = None

    if receiver:
        receiver_characters = json.loads(receiver['characters'])
        receiver_character = next((character for character in receiver_characters if character['id'] == receiver_character_id), None)
    else:
        receiver_character = None

    if not sender_character:
        await message.reply_text("You don't have the character you're trying to trade!")
        return

    if not receiver_character:
        await message.reply_text("The other user doesn't have the character they're trying to trade!")
        return

    pending_trades[(sender_id, receiver_id)] = (sender_character_id, receiver_character_id)

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Confirm Trade", callback_data="confirm_trade")],
            [InlineKeyboardButton("Cancel Trade", callback_data="cancel_trade")]
        ]
    )

    await message.reply_text(f"{message.reply_to_message.from_user.mention}, do you accept this trade?", reply_markup=keyboard)


@shivuu.on_callback_query(filters.create(lambda _, __, query: query.data in ["confirm_trade", "cancel_trade"]))
async def on_callback_query(client, callback_query):
    receiver_id = callback_query.from_user.id

    # Get sender and receiver details
    for (sender_id, _receiver_id), (sender_character_id, receiver_character_id) in pending_trades.items():
        if _receiver_id == receiver_id:
            break
    else:
        await callback_query.answer("This is not for you!", show_alert=True)
        return

    if callback_query.data == "confirm_trade":
        sender = await get_user_data(sender_id)
        receiver = await get_user_data(receiver_id)

        sender_characters = json.loads(sender['characters'])
        receiver_characters = json.loads(receiver['characters'])

        sender_character = next((character for character in sender_characters if character['id'] == sender_character_id), None)
        receiver_character = next((character for character in receiver_characters if character['id'] == receiver_character_id), None)

        # Remove and add characters for sender and receiver
        sender_characters.remove(sender_character)
        receiver_characters.remove(receiver_character)

        await update_user_characters(sender_id, sender_characters)
        await update_user_characters(receiver_id, receiver_characters)

        sender_characters.append(receiver_character)
        receiver_characters.append(sender_character)

        await update_user_characters(sender_id, sender_characters)
        await update_user_characters(receiver_id, receiver_characters)

        del pending_trades[(sender_id, receiver_id)]

        await callback_query.message.edit_text(f"You have successfully traded your character with {callback_query.message.reply_to_message.from_user.mention}!")

    elif callback_query.data == "cancel_trade":
        del pending_trades[(sender_id, receiver_id)]
        await callback_query.message.edit_text("❌️ Trade Cancelled...")


pending_gifts = {}

@shivuu.on_message(filters.command("gift"))
async def gift(client, message):
    sender_id = message.from_user.id

    if not message.reply_to_message:
        await message.reply_text("You need to reply to a user's message to gift a character!")
        return

    receiver_id = message.reply_to_message.from_user.id
    receiver_username = message.reply_to_message.from_user.username
    receiver_first_name = message.reply_to_message.from_user.first_name

    if sender_id == receiver_id:
        await message.reply_text("You can't gift a character to yourself!")
        return

    if len(message.command) != 2:
        await message.reply_text("You need to provide a character ID!")
        return

    character_id = message.command[1]

    sender = await get_user_data(sender_id)

    if sender:
        sender_characters = json.loads(sender['characters'])
        character = next((character for character in sender_characters if character['id'] == character_id), None)
    else:
        character = None

    if not character:
        await message.reply_text("You don't have this character in your collection!")
        return

    pending_gifts[(sender_id, receiver_id)] = {
        'character': character,
        'receiver_username': receiver_username,
        'receiver_first_name': receiver_first_name
    }

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Confirm Gift", callback_data="confirm_gift")],
            [InlineKeyboardButton("Cancel Gift", callback_data="cancel_gift")]
        ]
    )

    await message.reply_text(f"Do you really want to gift {message.reply_to_message.from_user.mention}?", reply_markup=keyboard)


@shivuu.on_callback_query(filters.create(lambda _, __, query: query.data in ["confirm_gift", "cancel_gift"]))
async def on_callback_query(client, callback_query):
    sender_id = callback_query.from_user.id

    for (_sender_id, receiver_id), gift in pending_gifts.items():
        if _sender_id == sender_id:
            break
    else:
        await callback_query.answer("This is not for you!", show_alert=True)
        return

    if callback_query.data == "confirm_gift":
        sender = await get_user_data(sender_id)
        receiver = await get_user_data(receiver_id)

        sender_characters = json.loads(sender['characters'])
        sender_characters.remove(gift['character'])
        await update_user_characters(sender_id, sender_characters)

        if receiver:
            receiver_characters = json.loads(receiver['characters'])
            receiver_characters.append(gift['character'])
            await update_user_characters(receiver_id, receiver_characters)
        else:
            await add_user(receiver_id, gift['receiver_username'], gift['receiver_first_name'], [gift['character']])

        del pending_gifts[(sender_id, receiver_id)]

        await callback_query.message.edit_text(f"You have successfully gifted your character to [{gift['receiver_first_name']}](tg://user?id={receiver_id})!")

    elif callback_query.data == "cancel_gift":
        del pending_gifts[(sender_id, receiver_id)]
        await callback_query.message.edit_text("❌️ Gift Cancelled...")

