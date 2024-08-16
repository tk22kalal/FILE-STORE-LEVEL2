#(©)CodeXBotz

import re
from datetime import datetime, timedelta
import pymongo
import os
import asyncio
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from Adarsh.bot import StreamBot
from config import ADMINS, FORCE_MSG, START_MSG, CUSTOM_CAPTION, DISABLE_CHANNEL_BUTTON, PROTECT_CONTENT, DB_URI, DB_NAME
from helper_func import subscribed, encode, decode, get_messages
from database.database import add_user, del_user, full_userbase, present_user
from Adarsh.utils.file_properties import get_name, get_hash, get_media_file_size
from urllib.parse import quote_plus
from Adarsh.vars import Var
from Adarsh.utils.human_readable import humanbytes

dbclient = pymongo.MongoClient(DB_URI)
database = dbclient[DB_NAME]
video_requests = database["video_requests"]

MAX_VIDEOS_PER_DAY = 10
TIME_LIMIT = timedelta(hours=12)

async def record_video_request(user_id: int):
    now = datetime.utcnow()
    video_requests.insert_one({"user_id": user_id, "timestamp": now})

def has_exceeded_limit(user_id: int):
    now = datetime.utcnow()
    start_time = now - TIME_LIMIT
    request_count = video_requests.count_documents({
        "user_id": user_id,
        "timestamp": {"$gte": start_time}
    })
    return request_count >= MAX_VIDEOS_PER_DAY
    
async def schedule_deletion(msgs, delay):
    await asyncio.sleep(delay)
    for msg in msgs:
        try:
            await msg.delete()
        except Exception as e:
            print(f"Error deleting message: {e}")

SECONDS = int(os.getenv("SECONDS", "21600"))

@StreamBot.on_message(filters.command('start') & filters.private & subscribed)
async def start_command(client: Client, message: Message):
    id = message.from_user.id
    if has_exceeded_limit(id):
        await message.reply_text("You have exceeded the limit of 10 videos in 24 hours. Please try again later.")
        return
    if not await present_user(id):
        try:
            await add_user(id)
        except:
            pass
    text = message.text
        
    if len(text) > 7:
        try:
            base64_string = text.split(" ", 1)[1]
        except:
            return
        string = await decode(base64_string)
        argument = string.split("-")
        if len(argument) == 3:
            try:
                start = int(int(argument[1]) / abs(client.db_channel.id))
                end = int(int(argument[2]) / abs(client.db_channel.id))
            except:
                return
            if start <= end:
                ids = range(start, end + 1)
            else:
                ids = []
                i = start
                while True:
                    ids.append(i)
                    i -= 1
                    if i < end:
                        break
        elif len(argument) == 2:
            try:
                ids = [int(int(argument[1]) / abs(client.db_channel.id))]
            except:
                return
        temp_msg = await message.reply("Please wait Baby...")
        try:
            messages = await get_messages(client, ids)
        except:
            await message.reply_text("Something went wrong..!")
            return
        await temp_msg.delete()


        for msg in messages:
            # Clean the caption to remove any text with @ and #
            original_caption = "" if not msg.caption else msg.caption.html
            cleaned_caption = re.sub(r'(\s|^)@[\w_]+', '', original_caption)
            cleaned_caption = re.sub(r'(\s|^)#[\w_]+', '', cleaned_caption).strip()
            
            # Add @mynextpulse to the caption
            caption = (
                CUSTOM_CAPTION.format(previouscaption=cleaned_caption, filename=msg.document.file_name)
                if CUSTOM_CAPTION and msg.document else 
                cleaned_caption
            ) + "\n@mynextpulse"

            if DISABLE_CHANNEL_BUTTON:
                reply_markup = msg.reply_markup
            else:
                reply_markup = None

            try:
                snt_msg = await msg.copy(
                    chat_id=message.from_user.id,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup      
                )

                await record_video_request(id)

                # Add streaming feature
                try:
                    log_msg = await msg.forward(chat_id=Var.BIN_CHANNEL)
                    stream_link = f"{Var.URL}watch/{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
                    online_link = f"{Var.URL}{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
                    
                    
                    msg_text ="""
<b> INSTRUCTIONS- <a href='https://telegra.ph/INSTRUCTIONS-08-03-3'>Click Here</a> </b>"""

                    x = await message.reply_text(
                        text=msg_text.format(get_name(log_msg), humanbytes(get_media_file_size(msg)), online_link, stream_link),
                        quote=True,
                        disable_web_page_preview=True,
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton('📥  ᴅᴏᴡɴʟᴏᴀᴅ  📥', url=online_link)]                       
                        ])
                    )
            
                except FloodWait as e:
                    print(f"Sleeping for {str(e.x)}s")
                    await asyncio.sleep(e.x)
                    await client.send_message(
                        chat_id=Var.BIN_CHANNEL,
                        text=f"Gᴏᴛ FʟᴏᴏᴅWᴀɪᴛ ᴏғ {str(e.x)}s from [{message.from_user.first_name}](tg://user?id={message.from_user.id})\n\n**𝚄𝚜𝚎𝚛 𝙸𝙳 :** `{str(message.from_user.id)}`",
                        disable_web_page_preview=True
                    )
                except MessageIdInvalid as e:
                    print(f"MessageIdInvalid: {e}")
                    await message.reply_text("Failed to generate stream link due to invalid message ID.")
                except ButtonUrlInvalid as e:
                    print(f"ButtonUrlInvalid: {e}")
                    await message.reply_text("Failed to generate stream link due to invalid button URL.")
            except Exception as e:
                print(f"Error copying message or generating stream link: {e}")


        asyncio.create_task(schedule_deletion([snt_msg, x], SECONDS))

        return
    else:
        reply_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("😊 About Me", callback_data="about"),
                    InlineKeyboardButton("🔒 Close", callback_data="close")
                ]
            ]
        )

        await message.reply_text(
            text=START_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            quote=True
        )
        return

    
#=====================================================================================##

WAIT_MSG = """"<b>Processing ...</b>"""

REPLY_ERROR = """<code>Use this command as a replay to any telegram message with out any spaces.</code>"""

#=====================================================================================##

    
    
@StreamBot.on_message(filters.command('start') & filters.private)
async def not_joined(client: Client, message: Message):
    buttons = [
        [
            InlineKeyboardButton(
                "Join Channel",
                url = client.invitelink)
        ]
    ]
    try:
        buttons.append(
            [
                InlineKeyboardButton(
                    text = 'Try Again',
                    url = f"https://t.me/{client.username}?start={message.command[1]}"
                )
            ]
        )
    except IndexError:
        pass

    await message.reply(
        text = FORCE_MSG.format(
                first = message.from_user.first_name,
                last = message.from_user.last_name,
                username = None if not message.from_user.username else '@' + message.from_user.username,
                mention = message.from_user.mention,
                id = message.from_user.id
            ),
        reply_markup = InlineKeyboardMarkup(buttons),
        quote = True,
        disable_web_page_preview = True
    )

@StreamBot.on_message(filters.command('users') & filters.private & filters.user(ADMINS))
async def get_users(client: StreamBot, message: Message):
    msg = await client.send_message(chat_id=message.chat.id, text=WAIT_MSG)
    users = await full_userbase()
    await msg.edit(f"{len(users)} users are using this bot")

@StreamBot.on_message(filters.private & filters.command('broadcast') & filters.user(ADMINS))
async def send_text(client: StreamBot, message: Message):
    if message.reply_to_message:
        query = await full_userbase()
        broadcast_msg = message.reply_to_message
        total = 0
        successful = 0
        blocked = 0
        deleted = 0
        unsuccessful = 0
        
        pls_wait = await message.reply("<i>Broadcasting Message.. This will Take Some Time</i>")
        for chat_id in query:
            try:
                await broadcast_msg.copy(chat_id)
                successful += 1
            except FloodWait as e:
                await asyncio.sleep(e.x)
                await broadcast_msg.copy(chat_id)
                successful += 1
            except UserIsBlocked:
                await del_user(chat_id)
                blocked += 1
            except InputUserDeactivated:
                await del_user(chat_id)
                deleted += 1
            except:
                unsuccessful += 1
                pass
            total += 1
        
        status = f"""<b><u>Broadcast Completed</u>

Total Users: <code>{total}</code>
Successful: <code>{successful}</code>
Blocked Users: <code>{blocked}</code>
Deleted Accounts: <code>{deleted}</code>
Unsuccessful: <code>{unsuccessful}</code></b>"""
        
        return await pls_wait.edit(status)

    else:
        msg = await message.reply(REPLY_ERROR)
        await asyncio.sleep(8)
        await msg.delete()
