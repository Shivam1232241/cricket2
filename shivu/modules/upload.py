import urllib.request
from pymongo import ReturnDocument
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, sudo_users, collection, db, CHARA_CHANNEL_ID, SUPPORT_CHAT

WRONG_FORMAT_TEXT = """Wrong ❌️ format...  eg. /upload Img_url muzan-kibutsuji Demon-slayer 3

img_url character-name anime-name rarity-number

use rarity number accordingly rarity Map

rarity_map = 1 (⚪️ Common), 2 (🟣 Rare), 3 (🟡 Legendary), 4 (🟢 Medium)"""


async def get_next_sequence_number(sequence_name):
    sequence_collection = db.sequences
    sequence_document = await sequence_collection.find_one_and_update(
        {'_id': sequence_name}, 
        {'$inc': {'sequence_value': 1}}, 
        return_document=ReturnDocument.AFTER
    )
    if not sequence_document:
        await sequence_collection.insert_one({'_id': sequence_name, 'sequence_value': 0})
        return 0
    return sequence_document['sequence_value']


async def upload(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('Ask My Owner...')
        return

    try:
        args = context.args
        if len(args) != 4:
            await update.message.reply_text(WRONG_FORMAT_TEXT)
            return

        img_url, character_name, anime, rarity_num = args
        character_name = character_name.replace('-', ' ').title()
        anime = anime.replace('-', ' ').title()

        # Validate the image URL
        try:
            urllib.request.urlopen(img_url)
        except:
            await update.message.reply_text('Invalid URL.')
            return

        # Validate rarity
        rarity_map = {1: "⚪ Common", 2: "🟣 Rare", 3: "🟡 Legendary", 4: "🟢 Medium"}
        try:
            rarity = rarity_map[int(rarity_num)]
        except KeyError:
            await update.message.reply_text('Invalid rarity. Please use 1, 2, 3, or 4.')
            return

        character_id = str(await get_next_sequence_number('character_id')).zfill(2)

        character = {
            'img_url': img_url,
            'name': character_name,
            'anime': anime,
            'rarity': rarity,
            'id': character_id
        }

        try:
            # Send photo to channel and store the message ID
            message = await context.bot.send_photo(
                chat_id=CHARA_CHANNEL_ID,
                photo=img_url,
                caption=f'<b>Character Name:</b> {character_name}\n<b>Anime Name:</b> {anime}\n<b>Rarity:</b> {rarity}\n<b>ID:</b> {character_id}\nAdded by <a href="tg://user?id={update.effective_user.id}">{update.effective_user.first_name}</a>',
                parse_mode='HTML'
            )
            character['message_id'] = message.message_id

            # Insert the character into the database
            await collection.insert_one(character)
            await update.message.reply_text('CHARACTER ADDED....')
        except Exception as e:
            # In case sending to the channel fails, add to the database
            await collection.insert_one(character)
            await update.message.reply_text(f"Character Added, but no Database Channel Found. Error: {str(e)}")
        
    except Exception as e:
        await update.message.reply_text(f'Character Upload Unsuccessful. Error: {str(e)}\nIf you think this is a source error, forward to: {SUPPORT_CHAT}')


async def delete(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('Ask my Owner to use this Command...')
        return

    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text('Incorrect format... Please use: /delete ID')
            return

        character = await collection.find_one_and_delete({'id': args[0]})

        if character:
            await context.bot.delete_message(chat_id=CHARA_CHANNEL_ID, message_id=character['message_id'])
            await update.message.reply_text('Character deleted successfully!')
        else:
            await update.message.reply_text('Character not found in the database or channel.')
    except Exception as e:
        await update.message.reply_text(f'Error: {str(e)}')


async def update(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('You do not have permission to use this command.')
        return

    try:
        args = context.args
        if len(args) != 3:
            await update.message.reply_text('Incorrect format. Please use: /update id field new_value')
            return

        character_id, field, new_value = args
        # Get character by ID
        character = await collection.find_one({'id': character_id})
        if not character:
            await update.message.reply_text('Character not found.')
            return

        # Check if field is valid
        valid_fields = ['img_url', 'name', 'anime', 'rarity']
        if field not in valid_fields:
            await update.message.reply_text(f'Invalid field. Please use one of the following: {", ".join(valid_fields)}')
            return

        # Update field
        if field in ['name', 'anime']:
            new_value = new_value.replace('-', ' ').title()
        elif field == 'rarity':
            rarity_map = {1: "⚪ Common", 2: "🟣 Rare", 3: "🟡 Legendary", 4: "🟢 Medium", 5: "💮 Special edition"}
            try:
                new_value = rarity_map[int(new_value)]
            except KeyError:
                await update.message.reply_text('Invalid rarity. Please use 1, 2, 3, 4, or 5.')
                return
        # Update the character in the database
        await collection.find_one_and_update({'id': character_id}, {'$set': {field: new_value}})

        # If updating image, delete and send new image
        if field == 'img_url':
            await context.bot.delete_message(chat_id=CHARA_CHANNEL_ID, message_id=character['message_id'])
            message = await context.bot.send_photo(
                chat_id=CHARA_CHANNEL_ID,
                photo=new_value,
                caption=f'<b>Character Name:</b> {character["name"]}\n<b>Anime Name:</b> {character["anime"]}\n<b>Rarity:</b> {character["rarity"]}\n<b>ID:</b> {character["id"]}\nUpdated by <a href="tg://user?id={update.effective_user.id}">{update.effective_user.first_name}</a>',
                parse_mode='HTML'
            )
            character['message_id'] = message.message_id
            await collection.find_one_and_update({'id': character_id}, {'$set': {'message_id': message.message_id}})
        else:
            await context.bot.edit_message_caption(
                chat_id=CHARA_CHANNEL_ID,
                message_id=character['message_id'],
                caption=f'<b>Character Name:</b> {character["name"]}\n<b>Anime Name:</b> {character["anime"]}\n<b>Rarity:</b> {character["rarity"]}\n<b>ID:</b> {character["id"]}\nUpdated by <a href="tg://user?id={update.effective_user.id}">{update.effective_user.first_name}</a>',
                parse_mode='HTML'
            )

        await update.message.reply_text('Character updated in database. Changes may take a few moments to reflect in the channel.')

    except Exception as e:
        await update.message.reply_text(f'Error: {str(e)}')


# Handlers for commands
UPLOAD_HANDLER = CommandHandler('upload', upload, block=False)
application.add_handler(UPLOAD_HANDLER)

DELETE_HANDLER = CommandHandler('delete', delete, block=False)
application.add_handler(DELETE_HANDLER)

UPDATE_HANDLER = CommandHandler('update', update, block=False)
application.add_handler(UPDATE_HANDLER)
