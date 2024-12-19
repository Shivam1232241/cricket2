import logging  
import json
import os
import sqlite3
from pyrogram import Client 
from telegram.ext import Application

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.FileHandler("log.txt"), logging.StreamHandler()],
    level=logging.INFO,
)

logging.getLogger("apscheduler").setLevel(logging.ERROR)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger("pyrate_limiter").setLevel(logging.ERROR)
LOGGER = logging.getLogger(__name__)

from shivu.config import Development as Config

# Configuration Variables
api_id = Config.api_id
api_hash = Config.api_hash
TOKEN = Config.TOKEN
GROUP_ID = Config.GROUP_ID
CHARA_CHANNEL_ID = Config.CHARA_CHANNEL_ID 
PHOTO_URL = Config.PHOTO_URL 
SUPPORT_CHAT = Config.SUPPORT_CHAT 
UPDATE_CHAT = Config.UPDATE_CHAT
BOT_USERNAME = Config.BOT_USERNAME 
sudo_users = Config.sudo_users
OWNER_ID = Config.OWNER_ID 

# Application Setup
application = Application.builder().token(TOKEN).build()
shivuu = Client("Shivu", api_id, api_hash, bot_token=TOKEN)

# Local SQLite Database Setup
conn = sqlite3.connect('local_database.db')
cursor = conn.cursor()

# Create Tables
cursor.execute("""
CREATE TABLE IF NOT EXISTS anime_characters_lol (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_name TEXT,
    character_data TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS user_totals_lmaoooo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    total_count INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS user_collection_lmaoooo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    collection_data TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS group_user_totalsssssss (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id TEXT,
    user_id TEXT,
    total_count INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS top_global_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id TEXT,
    group_name TEXT,
    total_score INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS total_pm_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    username TEXT
)
""")

conn.commit()

# Replace MongoDB Collections with SQLite Table Names
anime_characters_table = "anime_characters_lol"
user_totals_table = "user_totals_lmaoooo"
user_collection_table = "user_collection_lmaoooo"
group_user_totals_table = "group_user_totalsssssss"
top_global_groups_table = "top_global_groups"
pm_users_table = "total_pm_users"


def insert_anime_character(name, img_url, character_name, anime_name, rarity, description, additional_images):
    # Create a dictionary with all the character details
    character_data = {
        "character_name": character_name,
        "anime_name": anime_name,
        "rarity": rarity,
        "img_url": img_url,
        "description": description,
        "additional_images": additional_images
    }
    
    # Serialize the character data to a JSON string
    character_data_json = json.dumps(character_data)
    
    # Insert the data into the database
    cursor.execute(f"INSERT INTO {anime_characters_table} (character_name, character_data) VALUES (?, ?)", (name, character_data_json))
    conn.commit()

def get_anime_characters():
    cursor.execute(f"SELECT * FROM {anime_characters_table}")
    return cursor.fetchall()

def insert_user_total(user_id, total_count):
    cursor.execute(f"INSERT INTO {user_totals_table} (user_id, total_count) VALUES (?, ?)", (user_id, total_count))
    conn.commit()

def get_user_totals():
    cursor.execute(f"SELECT * FROM {user_totals_table}")
    return cursor.fetchall()


# Always close the database connection when shutting down
def close_connection():
    conn.close()

