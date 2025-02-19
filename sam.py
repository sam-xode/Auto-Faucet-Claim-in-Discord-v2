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



# Pastikan file faucets.json ada
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
    """Membaca file faucets.json dan mengembalikan datanya."""
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
    """Menyimpan data ke faucets.json."""
    with open("faucets.json", "w") as file:
        json.dump(data, file, indent=4)


def parse_time_input(time_input):
    if "h" in time_input:
        return int(time_input.replace("h", "")) * 3600
    elif "m" in time_input:
        return int(time_input.replace("m", "")) * 60
    else:
        raise ValueError("Format waktu tidak valid. Gunakan huruf kecil 'h' atau 'm' contoh 6h = 6jam, 30m = 30menit.")
        

def format_time(seconds):
    minutes = seconds // 60
    hours = minutes // 60
    minutes %= 60
    return f"{hours} jam {minutes} menit" if hours > 0 else f"{minutes} menit"

def konversi_waktu(detiks):
    jam = detiks // 3600
    detik_sisa = detiks % 3600
    menit = detik_sisa // 60
    detik = detik_sisa % 60
    return jam, menit, detik



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
            logging.info(f"✅ Gambar profil bot berhasil disimpan: {save_path}")
            return {
                "local_path": save_path,
                "original_url": bot_profile_url
            }
        else:
            logging.error(f"⚠️ Gagal mengunduh gambar profil bot untuk {channel_id}. Status code: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"⚠️ Error saat mengunduh gambar profil bot: {str(e)}")
        return None

def add_channel():
    faucets = load_faucets()
    tokens_input = input("\n🔷 Masukkan daftar DISCORD_TOKENS (pisahkan dengan koma): ").split(",")
    tokens = [t.strip() for t in tokens_input if t.strip()]
    save_tokens(tokens)

    channel_id = input("\n🔷 Masukkan ID Channel: ")
    if channel_id in faucets:
        print(f"⚠️ Channel {channel_id} sudah ada di database.")
        return

    faucet_name = input("🔷 Masukkan nama faucet: ")
    message = input("🔷 Masukkan pesan yang ingin dikirim: ")
    
    command_id, address, bot_profile_url = "", "", ""
    bot_image_data = None
    
    if message.startswith("/"):
        command_id = input("\n🔷 Masukkan Slash Command (contoh: /faucet): ")
        address = input("🔷 Masukkan Alamat Wallet: ")
        bot_profile_url = input("🔷 Masukkan Bot Profile URL: ")
        
        if bot_profile_url:
            bot_image_data = download_bot_profile_image(bot_profile_url, channel_id)
            if not bot_image_data:
                print("⚠️ Gagal mengunduh gambar bot profile. Melanjutkan tanpa gambar.")

    delay_input = input("Masukkan waktu klaim ulang otomatis (misal: 6h atau 30m): ")
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
    print(f"✅ Format auto claim {faucet_name} pada channel: [{channel_id}] berhasil disimpan!")
    print("\nPilih opsi 1 untuk memulai auto claim.\n")



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
        print(f"❌ [ERROR] Data tidak lengkap untuk {faucet_name} pada channel: [{channel_id}].")
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
            print(f"⏳ [WAIT] Channel [{channel_id}] - {faucet_name} - Waktu claim berikutnya: {format_time(int(remaining_time))}")
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
                print(f"✅ [SUKSES] {faucet_name} berhasil diklaim di [{channel_id}] oleh Token ke-{i+1}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ [ERROR] Gagal mengirim request untuk {faucet_name}: {str(e)}")
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
                print(f"⚠️ Error saat mencari gambar bot: {str(e)}")
                break
        
        if found:
            print(f"✅ Gambar bot ditemukan dan dipilih di Channel: [{channel_id}]")
        else:
            print(f"⚠️ Gambar bot tidak ditemukan di layar dalam 5 detik, lanjut tanpa memilih.")

    time.sleep(2)
    pyautogui.write(address)
    time.sleep(3)
    pyautogui.press("enter")

    print(f"✅ (CLAIM {faucet_name} dengan Slash command berhasil di Channel: [{channel_id}])")
    time.sleep(8)


def get_bot_image(channel_id, bot_profile_url):
    """Mengembalikan path gambar bot yang sesuai dengan channel_id."""
    local_image_path = os.path.join(BOT_IMAGES_DIR, f"bot_avatar_{channel_id}.png")

    # Jika gambar sudah ada, gunakan yang ada
    if os.path.exists(local_image_path):
        return local_image_path

    # Jika tidak ada, unduh gambar baru dari bot_profile_url
    if bot_profile_url:
        new_image_path = download_bot_profile_image(bot_profile_url, channel_id)
        if new_image_path:
            return new_image_path  # Pastikan gambar lokal digunakan setelah diunduh

    return None  # Jika tidak ada gambar, return None


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
            print(f"⏩ Melewati {faucet_name} pada Channel: [{channel_id}] karena tidak membutuhkan fitur slash command.")
            continue 
        


        # Cek apakah gambar ada secara lokal, jika tidak, unduh ulang
        local_image_path = os.path.join(BOT_IMAGES_DIR, f"bot_avatar_{channel_id}.png")
        
        if not os.path.exists(local_image_path) and bot_profile_url:
            new_image_path = download_bot_profile_image(bot_profile_url, channel_id)
            if new_image_path:
                bot_profile_url = new_image_path  # Perbarui dengan path lokal

                # Ambil path gambar yang sesuai
        bot_image_path = get_bot_image(channel_id, bot_profile_url,)

        if not bot_image_path:
            print(f"⚠️ Tidak dapat menemukan gambar bot untuk Channel [{channel_id}].")
            continue

        if command and address:
            login_and_use_slash_command(channel_id, command, address, bot_image_path, faucet_name)
        else:
            print(f"⚠️ Data tidak lengkap untuk Channel ID: [{channel_id}], melewati...")
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
                                print(f"\n❌ [ERROR] {faucet_name} Token ke-{i+1} tidak memiliki izin di channel [{channel_id}]")
                            elif response.status_code == 429:
                                retry_after = response.json().get("retry_after", 0)
                            continue
        
            if response.status_code == 200:
                    claim_times[faucet_name] = current_time 
                    print(f"\n✅ [SUKSES] {faucet_name} berhasil diklaim di Channel: [{channel_id}] oleh Token ke-{i+1}")






def claim_faucet():
    global auto_claim_enabled
    faucets = load_faucets()
    if not faucets:
        print("\n ⚠️  Tidak ada data faucet yang tersimpan. Tambahkan data klaim faucet dulu di opsi 3.")
        return


    print("\n✅ Auto claim diaktifkan!\n")
    auto_claim_enabled = True

    current_time = datetime.now()

    for channel_id, data in faucets.items():
        perform_claim(channel_id, data)
        faucet_name = data.get("faucet_name", "Unknown")
        messages = data.get("messages", [])
        claim_times = data.get("claim_times", {})  # Pastikan ini dictionary
        tokens = data.get("tokens", [])

        if not isinstance(claim_times, dict):  # Jika bukan dictionary, reset ke dictionary kosong
            claim_times = {}

        if not messages:
            print(f"\n❌ [ERROR] Tidak ada pesan yang disimpan untuk {faucet_name}.")
            continue

        if not tokens:
            print(f"\n❌ [ERROR] Tidak ada discord token yang tersedia untuk {faucet_name}.")
            continue
        
        threads = []

    remaining = slowmode_channels.get(channel_id, 0) - time.time()
    if channel_id not in slowmode_channels:
        remaining = 0
    for channel_id, data in faucets.items():
        if channel_id in slowmode_channels:
            print(f"\n⏳ [SKIP]  {faucet_name} Channel: [{channel_id}] masih dalam slowmode ({remaining:.2f} detik lagi).")
            continue



        thread = threading.Thread(target=claim_faucet_for_channel, args=(channel_id, data))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

        # Gunakan setiap bot token untuk mengklaim faucet
        for i, token in enumerate(tokens):
            headers = {"Authorization": token, "Content-Type": "application/json"}
            payload = {"content": messages[i % len(messages)]}  # Rotasi pesan jika banyak

            try:
                response = requests.post(
                    f"https://discord.com/api/v9/channels/{channel_id}/messages",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if response.status_code == 403:
                    print(f"\n❌ [ERROR] {faucet_name} Tidak ada izin untuk mengirim pesan ke channel [{channel_id}]")
                elif response.status_code == 429:
                    retry_after = response.json().get("retry_after", 0)
                    print(f"\n⚠️  [SLOWMODE] {faucet_name} terkena slowmode channel: [{channel_id}], menunggu {retry_after} detik")
                    print("\n🔄 Kembali ke menu utama...\n")
                else:
                    print(f"\n❌ [GAGAL] {faucet_name} channel: [{channel_id}] tidak diklaim. Status: {response.status_code}")
                continue

            if response.status_code == 200:
                claim_times[channel_id] = current_time.strftime("%Y-%m-%d %H:%M:%S")  # Simpan waktu klaim sebagai string
                data["claim_times"] = claim_times  # Update ke dalam data faucet
                save_faucets(faucets)  # Simpan perubahan ke JSON

                print(f"\n✅ [SUKSES] {faucet_name} berhasil diklaim di Channel: {channel_id} oleh Token ke-{i+1}")

            time.sleep(1)  # Delay antar request untuk menghindari spam


def check_slowmode():
    """Periksa apakah slowmode telah berakhir untuk channel tertentu dan hapus dari daftar."""
    global slowmode_channels
    while True:
        now = time.time()
        expired_channels = [ch for ch, end_time in slowmode_channels.items() if now >= end_time]

        for ch in expired_channels:
            print(f"\n ✅   Slowmode selesai pada channel: [{ch}], menghapus dari daftar slowmode.")
            del slowmode_channels[ch]
        
        if expired_channels:
            save_slowmode_channels()

        time.sleep(10) 

SLOWMODE_FILE = "slowmode_channels.json"
def load_slowmode_channels():
    """Membaca file slowmode_channels.json dan mengembalikan datanya."""
    try:
        with open(SLOWMODE_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_slowmode_channels():
    """Menyimpan data slowmode_channels ke slowmode_channels.json."""
    with open(SLOWMODE_FILE, "w") as file:
        json.dump(slowmode_channels, file, indent=4)

def list_slowmode_channels():
    """Tampilkan daftar channel yang terkena slowmode."""
    if not slowmode_channels:
        print("\n✅ Tidak ada channel yang terkena slowmode.")
    else:
        print("\n ⚠️  Daftar channel dalam slowmode:")
        for ch, end_time in slowmode_channels.items():
            remaining = max(0, end_time - time.time())  # Hindari nilai negatif
            print(f"  - Channel {ch}: {remaining:.2f} detik lagi")


def list_faucets():
    faucets = load_faucets()
    if not faucets:
        print("🚫 Tidak ada data claim faucet yang terdaftar.")
        return
    print("Data claim faucet yang terdaftar:")
    for channel_id, data in faucets.items():
        print(f"- {data['faucet_name']} [{channel_id}]")


def claim_faucet_for_channel(channel_id, data):
    print(f"\n🔄 Mengklaim faucet untuk channel: {channel_id}")
    time.sleep(1) 


auto_claim_enabled = False

def start_auto_claim():
    """Mengelola proses auto claim"""
    global auto_claim_enabled
    
    while True:
        # Tunggu sampai data tersedia
        while True:
            faucets = load_faucets()
            if faucets:
                break
            time.sleep(1)
        
        # Tunggu sampai auto claim diaktifkan melalui opsi 1
        if not auto_claim_enabled:
            time.sleep(1)
            continue
            
        current_time = datetime.now()
        
        for channel_id, data in faucets.items():
            # Dapatkan interval klaim
            claim_interval = data.get("claim_interval", 0)
            if isinstance(claim_interval, dict):
                claim_interval = next(iter(claim_interval.values())) if claim_interval else 0
            
            # Dapatkan waktu klaim terakhir
            claim_times_dict = data.get("claim_times", {})
            if not isinstance(claim_times_dict, dict):
                claim_times_dict = {}
            
            last_claim_time = claim_times_dict.get(channel_id)
            if last_claim_time:
                try:
                    last_claim_dt = datetime.strptime(last_claim_time, "%Y-%m-%d %H:%M:%S")
                    next_claim_time = last_claim_dt + timedelta(seconds=int(claim_interval))
                    
                    if current_time >= next_claim_time:
                        perform_claim(channel_id, data)
                except (ValueError, TypeError) as e:
                    continue
            else:
                # Untuk klaim pertama, tunggu aktivasi dari opsi 1
                if auto_claim_enabled:
                    perform_claim(channel_id, data)

        time.sleep(60)



def perform_claim(channel_id, data):
    """Melakukan klaim aktual ke Discord"""
    current_time = datetime.now()
    faucet_name = data.get("faucet_name", "Unknown")
    messages = data.get("messages", [])
    tokens = data.get("tokens", [])
    
    if not messages or not tokens:
        return

    # Periksa slowmode
    if channel_id in slowmode_channels:
        remaining = slowmode_channels[channel_id] - time.time()
        if remaining > 0:
            return

    # Lakukan klaim
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
                # Update waktu klaim hanya jika berhasil
                claim_times_dict = data.get("claim_times", {})
                if not isinstance(claim_times_dict, dict):
                    claim_times_dict = {}
                claim_times_dict[channel_id] = current_time.strftime("%Y-%m-%d %H:%M:%S")
                data["claim_times"] = claim_times_dict
                faucets = load_faucets()
                faucets[channel_id] = data
                save_faucets(faucets)
                print(f"✅ [SUKSES] {faucet_name} berhasil diklaim di [{channel_id}] oleh Token ke-{i+1}\n")
                
            elif response.status_code == 429:
                retry_after = response.json().get("retry_after", 0)
                slowmode_channels[channel_id] = time.time() + retry_after
                save_slowmode_channels()
                break
                
        except requests.exceptions.RequestException:
            continue

        if success:
            break
            
        time.sleep(1)


threading.Thread(target=start_auto_claim, daemon=True).start()

slowmode_channels = load_slowmode_channels()

slowmode_thread = threading.Thread(target=check_slowmode, daemon=True)
slowmode_thread.start()



def main():
    while True:
        print("\n📌  Pilih opsi:")
        print("1. Kirim semua pesan biasa")
        print("2. Kirim semua pesan dengan slash command (WINDOWS ONLY)")
        print("3. Tambahkan channel baru")
        print("4. Tampilkan channel yang terdaftar")
        print("5. Tampilkan channel yang terkena slowmode")
        print("6. Keluar")

        choice = input("\nMasukkan pilihan (1/2/3/4/5/6): ")

        if choice == "1":
            claim_faucet()
        elif choice == "2":
            send_all_slash_commands()
        elif choice == "3":
            add_channel()
        elif choice == "4":
            list_faucets()
        elif choice == "5":
            list_slowmode_channels ()
        elif choice == "6":
            print("\n🚪 Keluar dari program. Terimakasih telah menggunakan xode dari <SamXode/>\n")
            exit()
        else:
            print("❌ [ERROR] Pilihan tidak valid, coba lagi.")

if __name__ == "__main__":
    try:
        faucets = load_faucets()
        main()
    except KeyboardInterrupt:
        print("\n👋 Program dihentikan oleh pengguna. Terimakasih telah menggunakan xode dari <SamXode/> \n")
        exit()