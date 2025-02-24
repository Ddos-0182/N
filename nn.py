import os
import qrcode
from telethon import TelegramClient, events, Button

# Bot Configuration
BOT_TOKEN = "7604224106:AAE5Tci8Bj2Psu5PNl48etPPqwtFoCCpU38"  # Replace with your bot token
API_ID = 25501022               # Replace with your API ID from my.telegram.org
API_HASH = "6b932f215d8a2ea940babbec6bc7181a"    # Replace with your API Hash from my.telegram.org
OWNER_ID = 5905476543          # Replace with the admin's Telegram numeric ID

# Payment Details
UPI_ID = "rohitpandit16253@oksbi"

# Pricing Dictionary
PRICES = {
    "normal_server": {
        "1Day": 120,
        "3Days": 300,
        "7Days": 550,
        "15Days": 799,
        "1Month": 1100,
        "1Season": 1700
    }
}

# Key Storage Files (ensure these files exist in a folder named "keys")
KEY_FILES = {
    "1Day": "keys/normal_server_1Day.txt",
    "3Days": "keys/normal_server_3Days.txt",
    "7Days": "keys/normal_server_7Days.txt",
    "15Days": "keys/normal_server_15Days.txt",
    "1Month": "keys/normal_server_1Month.txt",
    "1Season": "keys/normal_server_1Season.txt"
}

# Dictionary to store pending payments (keyed by user_id)
pending_payments = {}

# Initialize Telegram Bot Client
client = TelegramClient("buy_keys_session", API_ID, API_HASH)
client.start(bot_token=BOT_TOKEN)


@client.on(events.NewMessage(pattern=r"/start"))
async def start(event):
    """Handles the /start command."""
    welcome_message = (
        "👋 Welcome to the Key Buying Service Bot!\n\n"
        "Click the button below to buy a key.\n"
        "For any help, contact: @YourAdminUsername"
    )
    await event.reply(
        welcome_message,
        buttons=[Button.text("💳 Buy Key", resize=True)]
    )


@client.on(events.NewMessage(func=lambda e: e.raw_text == "💳 Buy Key"))
async def buy_key(event):
    """Shows available key durations as inline buttons."""
    message = "📌 Choose your key duration:"
    buttons = [
        [Button.inline("1 Day - ₹120", data=b"buy_1Day")],
        [Button.inline("3 Days - ₹300", data=b"buy_3Days")],
        [Button.inline("7 Days - ₹550", data=b"buy_7Days")],
        [Button.inline("15 Days - ₹799", data=b"buy_15Days")],
        [Button.inline("1 Month - ₹1100", data=b"buy_1Month")],
        [Button.inline("1 Season - ₹1700", data=b"buy_1Season")]
    ]
    await event.reply(message, buttons=buttons)


@client.on(events.CallbackQuery(pattern=b"buy_(.*)"))
async def select_duration(event):
    """Handles duration selection, generates a QR code, and stores pending payment."""
    try:
        user_id = event.sender_id
        duration = event.data.decode().split("_")[1].strip()
        if duration not in PRICES["normal_server"]:
            await event.answer("Invalid selection.", alert=True)
            return

        price = PRICES["normal_server"][duration]
        upi_string = f"upi://pay?pa={UPI_ID}&pn=YourName&am={price}&cu=INR"
        qr = qrcode.make(upi_string)
        file_path = f"qr_{duration}.png"
        qr.save(file_path)

        pending_payments[user_id] = {"duration": duration}

        await event.respond(
            f"✅ Selected: Normal Server ({duration})\n"
            f"💰 Price: ₹{price}\n\n"
            f"📌 Scan the QR code below to complete the payment.\n"
            f"Or use this UPI ID: `{UPI_ID}`"
        , file=file_path)

        os.remove(file_path)
    except Exception as e:
        await event.answer(f"Error: {str(e)}", alert=True)


@client.on(events.NewMessage(func=lambda e: bool(e.photo)))
async def handle_payment_screenshot(event):
    """Forwards the payment screenshot to the admin with an approval button."""
    user_id = event.sender_id
    if user_id in pending_payments:
        duration = pending_payments[user_id]["duration"]
        await client.send_file(
            OWNER_ID,
            event.message.photo,
            caption=f"📸 Payment screenshot received from user {user_id}\nDuration: {duration}",
            buttons=[Button.inline("✅ Approve Payment", data=f"approve_{user_id}")]
        )
        await event.reply("✅ Payment screenshot received. Please wait for admin approval.")
    else:
        await event.reply("❌ No pending payment found.")


@client.on(events.CallbackQuery(pattern=b"approve_(.*)"))
async def approve_payment(event):
    """Handles admin approval and sends the key to the user."""
    if event.sender_id != OWNER_ID:
        await event.answer("Unauthorized!", alert=True)
        return

    user_id = int(event.data.decode().split("_")[1])
    if user_id not in pending_payments:
        await event.edit("❌ No pending payment found.")
        return

    duration = pending_payments[user_id]["duration"]
    key_file = KEY_FILES[duration]

    try:
        with open(key_file, "r") as f:
            keys = f.readlines()

        if keys:
            key = keys.pop(0).strip()
            with open(key_file, "w") as f:
                f.writelines(keys)

            await client.send_message(
                user_id,
                f"✅ Payment Approved!\nHere is your key for Normal Server ({duration}):\n`{key}`"
            )
            await event.edit(f"✅ Payment approved and key sent to user {user_id}.")
            pending_payments.pop(user_id, None)
        else:
            await event.edit("❌ No keys available.")
    except Exception as e:
        await event.edit(f"⚠️ Error: {str(e)}")


@client.on(events.NewMessage(pattern=r"/addkeys"))
async def add_keys(event):
    """Allows admin to add bulk keys."""
    if event.sender_id != OWNER_ID:
        await event.reply("❌ Unauthorized access.")
        return

    await event.reply(
        "Send keys in this format:\n\n"
        "`1Day key1 key2 key3`\n"
        "`3Days key4 key5`\n"
        "`7Days key6 key7 key8`\n"
        "`15Days key9 key10`\n"
        "`1Month key11 key12`\n"
        "`1Season key13 key14`\n\n"
        "Each key should be separated by a space."
    )


@client.on(events.NewMessage())
async def save_keys(event):
    """Saves keys sent by the admin to the corresponding file."""
    if event.sender_id != OWNER_ID:
        return

    words = event.raw_text.split()
    if len(words) < 2:
        return

    duration = words[0]
    keys = words[1:]

    if duration in KEY_FILES:
        with open(KEY_FILES[duration], "a") as f:
            f.write("\n".join(keys) + "\n")
        await event.reply(f"✅ {len(keys)} keys added for {duration}.")
    else:
        await event.reply("❌ Invalid duration. Use 1Day, 3Days, 7Days, 15Days, 1Month, or 1Season.")


print("Bot is running...")
client.run_until_disconnected()
