import os
import json
import time
import samxode_ip
import requests
import logging
import threading
import sys
import pyautogui
import webbrowser
import cv2
import numpy as np
from dotenv import dotenv_values, set_key
from PIL import Image
import pytesseract
from dotenv import load_dotenv
from datetime import datetime, timedelta

if not os.path.exists(".env"):
    with open(".env", "w") as f:
        f.write("DISCORD_TOKENS={}\n")

load_dotenv()

FAUCETS_FILE = "faucets.json"
BOT_IMAGES_DIR = "bot_images"
os.makedirs(BOT_IMAGES_DIR, exist_ok=True)
skip_channels = {}
slowmode_channels = {}

# Make sure faucets.json file exists
if not os.path.exists(FAUCETS_FILE):
    with open(FAUCETS_FILE, "w") as f:
        json.dump({}, f, indent=4)


def load_tokens():
    try:
        return json.loads(os.getenv("DISCORD_TOKENS", "{}"))
    except json.JSONDecodeError:
        return {}


def save_tokens(tokens):
    set_key(".env", "DISCORD_TOKENS", json.dumps(tokens))


def load_faucets():
    """Read faucets.json file and return its data."""
    try:
        if not os.path.exists(FAUCETS_FILE):  
            with open(FAUCETS_FILE, "w") as file:
                json.dump({}, file)
            return {}

        with open(FAUCETS_FILE, "r") as file:
            content = file.read().strip()
            if not content:  
                return {}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}  


def save_faucets(data):
    """Save data to faucets.json."""
    with open("faucets.json", "w") as file:
        json.dump(data, file, indent=4)


def parse_time_input(time_input):
    if "h" in time_input:
        return int(time_input.replace("h", "")) * 3600
    elif "m" in time_input:
        return int(time_input.replace("m", "")) * 60
    else:
        raise ValueError("Invalid time format. Use lowercase 'h' or 'm' e.g., 6h = 6 hours, 30m = 30 minutes.")
        

def format_time(seconds):
    minutes = seconds // 60
    hours = minutes // 60
    minutes %= 60
    return f"{hours} hours {minutes} minutes" if hours > 0 else f"{minutes} minutes"

def convert_time(seconds):
    hours = seconds // 3600
    remaining_seconds = seconds % 3600
    minutes = remaining_seconds // 60
    seconds = remaining_seconds % 60
    return hours, minutes, seconds


def download_bot_profile_image(bot_profile_url, channel_id):
    """
    Download bot profile image and return both the local path and original URL
    """
    try:
        # Ensure the directory exists
        if not os.path.exists(BOT_IMAGES_DIR):
            os.makedirs(BOT_IMAGES_DIR)
            
        # Generate local file path
        local_filename = f"bot_avatar_{channel_id}.png"
        save_path = os.path.join(BOT_IMAGES_DIR, local_filename)
        
        # Download image
        response = requests.get(bot_profile_url, stream=True)
        if response.status_code == 200:
            with open(save_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        file.write(chunk)
            logging.info(f"✅ Bot profile image successfully saved: {save_path}")
            return {
                "local_path": save_path,
                "original_url": bot_profile_url
            }
        else:
            logging.error(f"⚠️ Failed to download bot profile image for {channel_id}. Status code: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"⚠️ Error while downloading bot profile image: {str(e)}")
        return None

def add_channel():
    faucets = load_faucets()
    tokens_input = input("\n🔷 Enter DISCORD_TOKENS list (separate with comma): ").split(",")
    tokens = [t.strip() for t in tokens_input if t.strip()]
    save_tokens(tokens)

    channel_id = input("\n🔷 Enter Channel ID: ")
    if channel_id in faucets:
        print(f"⚠️ Channel {channel_id} already exists in the database.")
        return

    faucet_name = input("🔷 Enter faucet name: ")
    message = input("🔷 Enter message to send: ")
    
    command_id, address, bot_profile_url = "", "", ""
    bot_image_data = None
    
    if message.startswith("/"):
        command_id = input("\n🔷 Enter Slash Command (example: /faucet): ")
        address = input("🔷 Enter Wallet Address: ")
        bot_profile_url = input("🔷 Enter Bot Profile URL: ")
        
        if bot_profile_url:
            bot_image_data = download_bot_profile_image(bot_profile_url, channel_id)
            if not bot_image_data:
                print("⚠️ Failed to download bot profile image. Continuing without image.")

    delay_input = input("Enter auto-claim interval (e.g., 6h or 30m): ")
    claim_interval = parse_time_input(delay_input)
    
    faucets[channel_id] = {
        "faucet_name": faucet_name,
        "messages": [f"{command_id} {address}" if command_id else message],
        "claim_times": {},
        "claim_interval": claim_interval,
        "command_id": command_id,
        "address": address,
        "bot_profile": bot_image_data if bot_image_data else None,
        "tokens": tokens
    }
    
    save_faucets(faucets)
    print(f"✅ Auto claim format for {faucet_name} on channel: [{channel_id}] successfully saved!")
    print("\nSelect option 1 to start auto claim.\n")


def get_bot_image(channel_id, faucets_data):
    """
    Get bot image path from stored data
    """
    channel_data = faucets_data.get(channel_id, {})
    bot_profile_data = channel_data.get("bot_profile")
    
    if not bot_profile_data:
        return None
        
    # Check if local file exists
    local_path = bot_profile_data.get("local_path")
    if local_path and os.path.exists(local_path):
        return local_path
        
    # If local file doesn't exist, try to re-download
    original_url = bot_profile_data.get("original_url")
    if original_url:
        new_image_data = download_bot_profile_image(original_url, channel_id)
        if new_image_data:
            # Update stored data with new local path
            channel_data["bot_profile"] = new_image_data
            faucets = load_faucets()
            faucets[channel_id] = channel_data
            save_faucets(faucets)
            return new_image_data["local_path"]
            
    return None


def claim_faucet_for_channel(channel_id, data):
    """Execute faucet claim for a specific channel"""
    global slowmode_channels
    current_time = datetime.now()

    faucet_name = data.get("faucet_name", "Unknown")
    messages = data.get("messages", [])
    tokens = data.get("tokens", [])
    
    if not messages or not tokens:
        print(f"❌ [ERROR] Incomplete data for {faucet_name} on channel: [{channel_id}].")
        return

    # Get claim interval and times
    claim_interval = data.get("claim_interval", 0)  # Get the interval
    claim_times_dict = data.get("claim_times", {})
    if not isinstance(claim_times_dict, dict):
        claim_times_dict = {}

    last_claim_time = claim_times_dict.get(channel_id)
    if last_claim_time:
        last_claim_dt = datetime.strptime(last_claim_time, "%Y-%m-%d %H:%M:%S")
        next_claim_time = last_claim_dt + timedelta(seconds=claim_interval)

        if current_time < next_claim_time:
            remaining_time = (next_claim_time - current_time).total_seconds()
            print(f"⏳ [WAIT] Channel [{channel_id}] - {faucet_name} - Next claim time: {format_time(int(remaining_time))}")
            return

    # Execute claims and update time
    for i, token in enumerate(tokens):
        headers = {"Authorization": token, "Content-Type": "application/json"}
        payload = {"content": messages[i % len(messages)]}

        try:
            response = requests.post(
                f"https://discord.com/api/v9/channels/{channel_id}/messages",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                claim_times_dict[channel_id] = current_time.strftime("%Y-%m-%d %H:%M:%S")
                data["claim_times"] = claim_times_dict
                faucets = load_faucets()
                faucets[channel_id] = data
                save_faucets(faucets)
                print(f"✅ [SUCCESS] {faucet_name} successfully claimed in [{channel_id}] by Token #{i+1}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ [ERROR] Failed to send request for {faucet_name}: {str(e)}")
            continue

        time.sleep(1)


def login_and_use_slash_command(channel_id, command, address, faucets_data, faucet_name):
    """Modified to use faucets_data instead of direct bot_profile_url"""
    webbrowser.open(f"https://discord.com/channels/@me/{channel_id}")
    time.sleep(10)
    
    pyautogui.write(command)
    time.sleep(4)

    bot_image_path = get_bot_image(channel_id, faucets_data)
    if bot_image_path:
        start_time = time.time()
        found = False
        while time.time() - start_time < 7:
            try:
                location = pyautogui.locateCenterOnScreen(bot_image_path, confidence=0.8)
                if location:
                    pyautogui.click(location)
                    time.sleep(2)
                    found = True
                    break
            except Exception as e:
                print(f"⚠️ Error while searching for bot image: {str(e)}")
                break
        
        if found:
            print(f"✅ Bot image found and selected in Channel: [{channel_id}]")
        else:
            print(f"⚠️ Bot image not found on screen within 5 seconds, continuing without selection.")

    time.sleep(2)
    pyautogui.write(address)
    time.sleep(3)
    pyautogui.press("enter")
    time.sleep(6)

    print(f"✅ (CLAIM {faucet_name} with Slash command successful in Channel: [{channel_id}])")
    time.sleep(8)


def get_bot_image(channel_id, bot_profile_url):
    """Returns the bot image path that matches the channel_id."""
    local_image_path = os.path.join(BOT_IMAGES_DIR, f"bot_avatar_{channel_id}.png")

    # If image already exists, use existing one
    if os.path.exists(local_image_path):
        return local_image_path

    # If not available, download new image from bot_profile_url
    if bot_profile_url:
        new_image_path = download_bot_profile_image(bot_profile_url, channel_id)
        if new_image_path:
            return new_image_path  # Make sure local image is used after download

    return None  # If no image, return None


def send_all_slash_commands():
    faucets = load_faucets()
    tokens = load_tokens()
    current_time = datetime.now()  # Use current_time instead of now
    claim_times = {key: data.get("claim times", 0) for key, data in faucets.items()}

    for channel_id, data in faucets.items():
        command = data.get("command_id", "").strip()
        address = data.get("address", "").strip()
        bot_profile_url = data.get("bot_profile_url", "")
        faucet_name = data.get("faucet_name", "").strip()

        if not command:
            print(f"⏩ Skipping {faucet_name} on Channel: [{channel_id}] because it doesn't require slash command feature.")
            continue 

        # Check if image exists locally, if not, re-download
        local_image_path = os.path.join(BOT_IMAGES_DIR, f"bot_avatar_{channel_id}.png")
        
        if not os.path.exists(local_image_path) and bot_profile_url:
            new_image_path = download_bot_profile_image(bot_profile_url, channel_id)
            if new_image_path:
                bot_profile_url = new_image_path  # Update with local path

                # Get the appropriate image path
        bot_image_path = get_bot_image(channel_id, bot_profile_url,)

        if not bot_image_path:
            print(f"⚠️ Cannot find bot image for Channel [{channel_id}].")
            continue

        if command and address:
            login_and_use_slash_command(channel_id, command, address, bot_image_path, faucet_name)
        else:
            print(f"⚠️ Incomplete data for Channel ID: [{channel_id}], skipping...")
            continue

        for token in tokens:
            headers = {"Authorization": token, "Content-Type": "application/json"}
            headers_list = [{"Authorization": token, "Content-Type": "application/json"} for token in tokens]
            payload = {
                "type": 2,
                "application_id": bot_profile_url,
                "guild_id": channel_id,
                "channel_id": channel_id,
                "data": {
                    "id": command,
                    "name": command.split("/")[-1] if command else "",
                    "type": 1,
                    "options": [{"name": "address", "value": address}]
                }
            }
            for i, headers in enumerate(headers_list):
                try:
                    response = requests.post(
                        "https://discord.com/api/v9/interactions",
                        headers=headers,
                        json=payload
                    )
                    response.raise_for_status()
                except requests.exceptions.HTTPError as e:
                    if response.status_code == 403:
                        print(f"\n❌ [ERROR] {faucet_name} Token #{i+1} doesn't have permission in channel [{channel_id}]")
                    elif response.status_code == 429:
                        retry_after = response.json().get("retry_after", 0)
                    continue
        
            if response.status_code == 200:
                claim_times[faucet_name] = current_time 
                print(f"\n✅ [SUCCESS] {faucet_name} successfully claimed in Channel: [{channel_id}] by Token #{i+1}")


def claim_faucet():
    global auto_claim_enabled
    faucets = load_faucets()
    if not faucets:
        print("\n⚠️ No faucet data stored. First add faucet claim data in option 3.")
        return

    print("\n✅ Auto claim activated!\n")
    auto_claim_enabled = True  # Set this to True and it should stay True
    
    print("\n📌 Auto claim will continue running in the background according to the set time.")
    print("📌 You can return to the main menu and use other options.\n")

    current_time = datetime.now()
    
    threads = []
    
    for channel_id, data in faucets.items():
        if channel_id in slowmode_channels:
            remaining = slowmode_channels[channel_id] - time.time()
            if remaining > 0:
                print(f"⏳ [SKIP] {data.get('faucet_name', 'Unknown')} Channel: [{channel_id}] still in slowmode ({remaining:.2f} seconds left).")
                continue

        thread = threading.Thread(target=perform_immediate_claim, args=(channel_id, data))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()


def check_slowmode():
    """Check if slowmode has ended for certain channels and remove from list."""
    global slowmode_channels
    while True:
        try:
            now = time.time()
            expired_channels = [ch for ch, end_time in slowmode_channels.items() if now >= end_time]
            
            # Claim faucet for channels whose slowmode has ended
            if expired_channels:
                faucets = load_faucets()
                
                for ch in expired_channels:
                    if ch in faucets and auto_claim_enabled:
                        print(f"\n✅ Slowmode finished on channel: [{ch}], attempting automatic claim...")
                        perform_claim(ch, faucets[ch])
                    
                    print(f"✅ Removing channel [{ch}] from slowmode list.")
                    del slowmode_channels[ch]
                
                save_slowmode_channels()
            
            time.sleep(5)
        except Exception as e:
            print(f"❌ [ERROR] Error in slowmode check: {str(e)}")
            time.sleep(10)

SLOWMODE_FILE = "slowmode_channels.json"
def load_slowmode_channels():
    """Read slowmode_channels.json file and return its data."""
    try:
        with open(SLOWMODE_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_slowmode_channels():
    """Save slowmode_channels data to slowmode_channels.json."""
    with open(SLOWMODE_FILE, "w") as file:
        json.dump(slowmode_channels, file, indent=4)

def list_slowmode_channels():
    """Display list of channels in slowmode."""
    if not slowmode_channels:
        print("\n ✅  No channels in slowmode.")
    else:
        print("\n ⚠️  List of channels in slowmode:")
        print("-----------------------------")
        for ch, end_time in slowmode_channels.items():
            remaining = max(0, end_time - time.time())  # Avoid negative values
            
            # Try to get faucet name if available
            faucets = load_faucets()
            faucet_name = "Unknown"
            if ch in faucets:
                faucet_name = faucets[ch].get("faucet_name", "Unknown")
                
            print(f"  - {faucet_name} Channel [{ch}]: {remaining:.2f} seconds left")

def perform_immediate_claim(channel_id, data):
    """Perform immediate claim for a channel, regardless of previous claim status"""
    current_time = datetime.now()
    faucet_name = data.get("faucet_name", "Unknown")
    messages = data.get("messages", [])
    tokens = data.get("tokens", [])
    
    if not messages or not tokens:
        print(f"❌ [ERROR] Incomplete data for {faucet_name} on channel: [{channel_id}]")
        return False

    # Process the claim
    success = False
    for i, token in enumerate(tokens):
        headers = {"Authorization": token, "Content-Type": "application/json"}
        payload = {"content": messages[i % len(messages)]}

        try:
            response = requests.post(
                f"https://discord.com/api/v9/channels/{channel_id}/messages",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                success = True
                # Update claim time
                claim_times_dict = data.get("claim_times", {})
                if not isinstance(claim_times_dict, dict):
                    claim_times_dict = {}
                claim_times_dict[channel_id] = current_time.strftime("%Y-%m-%d %H:%M:%S")
                data["claim_times"] = claim_times_dict
                
                # Save updated data
                faucets = load_faucets()
                faucets[channel_id] = data
                save_faucets(faucets)
                
                # Calculate and display next claim time
                claim_interval = data.get("claim_interval", 0)
                next_claim_time = current_time + timedelta(seconds=claim_interval)
                hours, minutes, seconds = convert_time(claim_interval)
                time_format = ""
                if hours > 0:
                    time_format += f"{hours} hours "
                if minutes > 0:
                    time_format += f"{minutes} minutes "
                if seconds > 0:
                    time_format += f"{seconds} seconds"
                
                print(f"✅ [SUCCESS] {faucet_name} successfully claimed in [{channel_id}] by Token #{i+1}")
                print(f"⏰ Next claim for [{channel_id}] - {faucet_name} will be in {time_format} at {next_claim_time.strftime('%H:%M:%S %d-%m-%Y')}")
                return True
                
            elif response.status_code == 429:
                retry_after = response.json().get("retry_after", 0)
                slowmode_channels[channel_id] = time.time() + retry_after
                print(f"⚠️ [SLOWMODE] {faucet_name} hit slowmode in channel: [{channel_id}], waiting {retry_after:.2f} seconds")
                save_slowmode_channels()
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ [ERROR] Failed to send request for {faucet_name}: {str(e)}")
            continue

        time.sleep(1)
    
    return success


def list_faucets():
    faucets = load_faucets()
    if not faucets:
        print(" 🚫  No faucet claim data registered.")
        return
    print("✅ Registered faucet claim data:")
    print("-----------------------------")
    for channel_id, data in faucets.items():
        print(f"- {data['faucet_name']} [{channel_id}]")


def show_claim_countdown():
    """Show the remaining time until the next automatic claim for each channel"""
    faucets = load_faucets()
    if not faucets:
        print("\n 🚫  No faucet claim data registered.")
        return
        
    current_time = datetime.now()
    print("\n ⏰  Faucet Claim Countdown:")
    print("-----------------------------")
    
    has_countdowns = False
    
    for channel_id, data in faucets.items():
        faucet_name = data.get("faucet_name", "Unknown")
        claim_interval = data.get("claim_interval", 0)
        claim_times_dict = data.get("claim_times", {})
        
        if not isinstance(claim_times_dict, dict):
            claim_times_dict = {}
            
        last_claim_time = claim_times_dict.get(channel_id)
        
        if last_claim_time and claim_interval > 0:
            try:
                last_claim_dt = datetime.strptime(last_claim_time, "%Y-%m-%d %H:%M:%S")
                next_claim_time = last_claim_dt + timedelta(seconds=claim_interval)
                
                if current_time < next_claim_time:
                    remaining_seconds = (next_claim_time - current_time).total_seconds()
                    hours, minutes, secs = convert_time(int(remaining_seconds))
                    
                    status = " ⏳  Waiting"
                    if channel_id in slowmode_channels:
                        status = " ⚠️  In Slowmode"
                    
                    countdown_str = ""
                    if hours > 0:
                        countdown_str += f"{hours}h "
                    if minutes > 0:
                        countdown_str += f"{minutes}m "
                    if secs > 0 or (hours == 0 and minutes == 0):
                        countdown_str += f"{secs}s"
                    
                    print(f"{status} | {faucet_name} [{channel_id}] | Next claim in: {countdown_str.strip()} | {next_claim_time.strftime('%H:%M:%S %d-%m-%Y')}")
                    has_countdowns = True
                else:
                    if auto_claim_enabled:
                        print(f" 🔄  Ready | {faucet_name} [{channel_id}] | Claim pending (will claim soon)")
                    else:
                        print(f" ⏳  Waiting | {faucet_name} [{channel_id}] | Ready to claim (waiting for next interval)")
                    has_countdowns = True
            except (ValueError, TypeError) as e:
                print(f"⚠️ Error with time data for {faucet_name} [{channel_id}]: {e}")
        else:
            if auto_claim_enabled:  # Jika auto claim aktif
                print(f" 🔄  Active | {faucet_name} [{channel_id}] | Will claim according to set interval")
            else:
                print(f" 🆕  New | {faucet_name} [{channel_id}] | No previous claims")
            has_countdowns = True
    
    if not has_countdowns:
        print("No active countdown timers found.")
    
    print("\n 📌  Status Data:")
    print("-----------------------------")
    print(" ⏳  Waiting - Will claim when timer expires")
    print(" ⚠️  In Slowmode - Channel is in slowmode, will attempt after slowmode ends")
    print(" 🔄  Active/Ready - Will claim according to set interval")
    print(" 🆕  New - First claim pending\n")


def claim_faucet_for_channel(channel_id, data):
    print(f"\n🔄 Claiming faucet for channel: {channel_id}")
    time.sleep(1) 


auto_claim_enabled = False

def start_auto_claim():
    """Manage auto claim process"""
    global auto_claim_enabled
    
    while True:
        try:
            faucets = load_faucets()
            if not faucets:
                time.sleep(5)
                continue
            
            current_time = datetime.now()
            
            if auto_claim_enabled:  # Check if auto claim is enabled
                for channel_id, data in faucets.items():
                    # Skip if channel in slowmode
                    if channel_id in slowmode_channels and time.time() < slowmode_channels[channel_id]:
                        continue
                        
                    # Get claim interval
                    claim_interval = data.get("claim_interval", 0)
                    if not isinstance(claim_interval, (int, float)):
                        if isinstance(claim_interval, dict):
                            claim_interval = next(iter(claim_interval.values())) if claim_interval else 0
                        else:
                            claim_interval = 0
                    
                    # Get last claim time
                    claim_times_dict = data.get("claim_times", {})
                    if not isinstance(claim_times_dict, dict):
                        claim_times_dict = {}
                    
                    last_claim_time = claim_times_dict.get(channel_id)
                    
                    should_claim = False
                    
                    if last_claim_time:
                        try:
                            last_claim_dt = datetime.strptime(last_claim_time, "%Y-%m-%d %H:%M:%S")
                            next_claim_time = last_claim_dt + timedelta(seconds=int(claim_interval))
                            
                            # If time has come for next claim
                            if current_time >= next_claim_time:
                                should_claim = True
                        except (ValueError, TypeError) as e:
                            print(f"⚠️ Error parsing time: {e}")
                            should_claim = True
                    else:
                        # For new channels, claim immediately
                        should_claim = True
                    
                    if should_claim:
                        perform_immediate_claim(channel_id, data)
            
            time.sleep(5)
        except Exception as e:
            print(f"❌ [ERROR] Error in auto claim: {str(e)}")
            time.sleep(10)


def perform_claim(channel_id, data):
    """Perform actual claim to Discord"""
    global slowmode_channels
    current_time = datetime.now()
    faucet_name = data.get("faucet_name", "Unknown")
    messages = data.get("messages", [])
    tokens = data.get("tokens", [])
    claim_interval = data.get("claim_interval", 0)
    
    if not messages or not tokens:
        return False

    # Check slowmode
    if channel_id in slowmode_channels:
        remaining = slowmode_channels[channel_id] - time.time()
        if remaining > 0:
            print(f"⏳ [WAIT] Channel [{channel_id}] - {faucet_name} still in slowmode ({remaining:.2f} seconds left)")
            return False

    # Perform claim
    success = False
    for i, token in enumerate(tokens):
        headers = {"Authorization": token, "Content-Type": "application/json"}
        payload = {"content": messages[i % len(messages)]}

        try:
            response = requests.post(
                f"https://discord.com/api/v9/channels/{channel_id}/messages",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                success = True
                # Update claim time only if successful
                claim_times_dict = data.get("claim_times", {})
                if not isinstance(claim_times_dict, dict):
                    claim_times_dict = {}
                claim_times_dict[channel_id] = current_time.strftime("%Y-%m-%d %H:%M:%S")
                data["claim_times"] = claim_times_dict
                faucets = load_faucets()
                faucets[channel_id] = data
                save_faucets(faucets)
                
                # Calculate next claim time
                next_claim_time = current_time + timedelta(seconds=claim_interval)
                hours, minutes, seconds = convert_time(claim_interval)
                time_format = ""
                if hours > 0:
                    time_format += f"{hours} hours "
                if minutes > 0:
                    time_format += f"{minutes} minutes "
                if seconds > 0:
                    time_format += f"{seconds} seconds"
                
                print(f"✅ [SUCCESS] {faucet_name} successfully claimed in [{channel_id}] by Token #{i+1}")
                print(f"⏰ [{channel_id}] - {faucet_name} will be automatically claimed in {time_format} at {next_claim_time.strftime('%H:%M:%S %d-%m-%Y')}")
                return True
                
            elif response.status_code == 429:
                retry_after = response.json().get("retry_after", 0)
                slowmode_channels[channel_id] = time.time() + retry_after
                print(f"⚠️ [SLOWMODE] {faucet_name} hit slowmode channel: [{channel_id}], waiting {retry_after:.2f} seconds")
                save_slowmode_channels()
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ [ERROR] Failed to send request for {faucet_name}: {str(e)}")
            continue

        time.sleep(1)
    
    return success


threading.Thread(target=start_auto_claim, daemon=True).start()

slowmode_channels = load_slowmode_channels()

slowmode_thread = threading.Thread(target=check_slowmode, daemon=True)
slowmode_thread.start()


def main():
    while True:
        print("\n📌  Select option:")
        print("-----------------------------")
        print("1. Send all regular messages")
        print("2. Send all messages with slash command (WINDOWS ONLY)")
        print("3. Add new channel & new messages")
        print("4. Show registered channels")
        print("5. Show channels in slowmode")
        print("6. Show faucet claim countdown")
        print("7. Exit")

        choice = input("\nEnter choice (1/2/3/4/5/6/7): " )
        print("\n")

        if choice == "1":
            claim_faucet()
        elif choice == "2":
            send_all_slash_commands()
        elif choice == "3":
            add_channel()
        elif choice == "4":
            list_faucets()
        elif choice == "5":
            list_slowmode_channels()
        elif choice == "6":
            show_claim_countdown()
        elif choice == "7":
            print("\n🚪 Exiting program. Thank you for using xode from <SamXode/>\n")
            exit()
        else:
            print("❌ [ERROR] Invalid choice, try again.")


if __name__ == "__main__":
    try:
        faucets = load_faucets()
        main()
    except KeyboardInterrupt:
        print("\n👋 Program stopped by user. Thank you for using xode from <SamXode/> \n")
        exit()
