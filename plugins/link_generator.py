import re
from pyrogram import Client, filters
from pyrogram.types import Message
from Adarsh.bot import StreamBot
from config import ADMINS, CUSTOM_CAPTION, CHANNEL_ID
from helper_func import encode, get_message_id
from pyrogram.errors import FloodWait
import asyncio

# Helper function to clean the caption
def clean_caption(caption):
    # Remove words starting with # or @
    caption = re.sub(r'\s?[@#]\S+', '', caption)
    # Remove URLs
    caption = re.sub(r'http\S+', '', caption)
    return caption

@StreamBot.on_message(filters.private & filters.user(ADMINS) & filters.command('batch'))
async def batch(client: Client, message: Message):
    # Step 1: Get the first message from the DB Channel
    while True:
        try:
            first_message = await client.ask(
                text="Forward the First Message from DB Channel (with Quotes)..\n\nor Send the DB Channel Post Link",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except:
            return  # Return if there's an exception (e.g., timeout)

        f_msg_id = await get_message_id(client, first_message)

        if f_msg_id:
            break
        else:
            await first_message.reply("❌ Error\n\nThis forwarded post is not from my DB Channel or the link is not valid.", quote=True)
            continue

    # Step 2: Get the last message from the DB Channel
    while True:
        try:
            second_message = await client.ask(
                text="Forward the Last Message from DB Channel (with Quotes)..\nor Send the DB Channel Post link",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except:
            return  # Return if there's an exception (e.g., timeout)

        s_msg_id = await get_message_id(client, second_message)

        if s_msg_id:
            break
        else:
            await second_message.reply("❌ Error\n\nThis forwarded post is not from my DB Channel or the link is not valid.", quote=True)
            continue

    # PART 1: Process and send with xyz = "{\"X\"}"
    xyz = "{\"X\"}"  # First replacement for generating the new message links
    message_links = []
    for msg_id in range(min(f_msg_id, s_msg_id), max(f_msg_id, s_msg_id) + 1):
        try:
            # Generate the first link and append it to the list
            string = f"get-{msg_id * abs(client.db_channel.id)}"
            base64_string = await encode(string)
            linka = f"https://t.me/{xyz}?start={base64_string}"
            message_links.append((linka, msg_id))  # Append a tuple with link and msg_id
        except Exception as e:
            await message.reply(f"Error generating link for message {msg_id}: {e}")

    # Send generated links and captions to the CHANNEL_ID (Database Channel)
    new_message_ids = []
    for linka, msg_id in message_links:
        try:
            # Fetch the message object for the current msg_id
            current_message = await client.get_messages(client.db_channel.id, msg_id)

            # Determine the caption for this message
            if bool(CUSTOM_CAPTION) and current_message.document:
                raw_caption = "" if not current_message.caption else current_message.caption.html
                cleaned_caption = clean_caption(raw_caption)
                caption = CUSTOM_CAPTION.format(
                    previouscaption=cleaned_caption,
                    filename=current_message.document.file_name
                )
            else:
                raw_caption = "" if not current_message.caption else current_message.caption.html
                caption = clean_caption(raw_caption)

            # Send the caption followed by the link to CHANNEL_ID
            try:
                sent_message = await client.send_message(chat_id=CHANNEL_ID, text=f"{caption}\n{linka}")
                
                # Get the message ID using the `get_message_id` function
                sent_message_id = await get_message_id(client, sent_message)
                new_message_ids.append(sent_message_id)  # Store the new message IDs using the correct function
                
            except FloodWait as e:
                await asyncio.sleep(e.value)
                sent_message = await client.send_message(chat_id=CHANNEL_ID, text=f"{caption}\n{linka}")
                
                # Get the message ID using the `get_message_id` function after handling FloodWait
                sent_message_id = await get_message_id(client, sent_message)
                new_message_ids.append(sent_message_id)

        except Exception as e:
            await message.reply(f"Error processing message {msg_id}: {e}")

    # PART 2: Process and send with xyz = "{{botUsername}}"
    xyz = "{{botUsername}}"  # Second replacement for generating the new links of the new messages in the DB Channel
    for new_msg_id in new_message_ids:
        try:
            # Generate the second link for the user based on the new message ID in the DB channel
            string = f"get-{new_msg_id * abs(client.db_channel.id)}"
            base64_string = await encode(string)
            linka = f"https://t.me/{xyz}?start={base64_string}"

            # Fetch the current message using the newly generated message ID
            current_message = await client.get_messages(CHANNEL_ID, new_msg_id)

            # Clean and format the caption for the user
            if bool(CUSTOM_CAPTION) and current_message.document:
                caption = CUSTOM_CAPTION.format(
                    previouscaption="" if not current_message.caption else current_message.caption.html,
                    filename=current_message.document.file_name
                )
            else:
                caption = "" if not current_message.caption else current_message.caption.html

            clean_caption_text = clean_caption(caption)  # Ensure this line is properly defined

            # Send the cleaned caption followed by the link to the user who triggered the batch command
            try:
                await client.send_message(chat_id=message.from_user.id, text=f"{clean_caption_text}\n{linka}")
            except FloodWait as e:
                await asyncio.sleep(e.x)
                await client.send_message(chat_id=message.from_user.id, text=f"{clean_caption_text}\n{linka}")

        except Exception as e:
            await message.reply(f"Error processing message {new_msg_id}: {e}")

    # Inform the user that batch processing is completed
    await message.reply("Batch processing completed.")
