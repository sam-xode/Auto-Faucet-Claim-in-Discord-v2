# Auto-Faucet-Claim-in-Discord-v2
This Xode is designed to automatically claim faucets by sending messages to configured Discord channels. It also handles rate limits and slow mode automatically. In this latest version, you can claim the faucet if the bot requires you to use the slash command feature in Discord.

## 📌 Features

- 🔑 Uses `DISCORD_TOKENS` from `.env` for security. Supports multiple Discord tokens.
- 💬 Sends messages to multiple configured channels.
- ⏳ Automatically manages Slow Mode & Rate Limits.
- 📝 Allows users to add new faucets directly from the CLI.
- 🔄 Uses multi-threading to handle slow mode without blocking other processes.
- 📸 Supports auto-detection of bot profile images for enhanced interaction.
- 🛠 Supports both text-based and slash command-based faucet claims.
- 🔁 Auto-resends messages based on user-defined intervals.
- 💜 Logs all bot activity in `bot.log`.

## 💞 Installation

### 1. Obtain Your Discord Token
Ensure you are logged into your Discord account.

1. Open Developer Tools (`F12` or `Ctrl + Shift + I`).
2. Navigate to the Console tab.
3. Paste the following code into the Console and press Enter:

```js
(
    webpackChunkdiscord_app.push(
        [
            [''],
            {},
            e => {
                m=[];
                for(let c in e.c)
                    m.push(e.c[c])
            }
        ]
    ),
    m
).find(
    m => m?.exports?.default?.getToken !== void 0
).exports.default.getToken()
```

Your Discord token will be displayed in the console. Save it securely!

### 2. Clone the Repository
```sh
git clone https://github.com/sam-xode/Auto-Faucet-Claim-in-Discord-v2.git
cd Discord-auto-claim-faucet
```

### 3. Install Dependencies
```sh
pip install -r requirements.txt
```

### 4. First-Time Run
The script will automatically create a `.env` file and `.json` file :
```sh
python sam.py
```

## 🛠 How to Use

### Running the Bot:
```sh
python sam.py
```

### Menu Options:

#### 1️⃣ CLAIM ALL FAUCETS
Automatically claims all configured faucets.

#### 2️⃣ Add a New Faucet
Allows users to add a new faucet claim configuration. Follow these steps:

1. Enter Discord Tokens, separated by commas. Example:
   ```
   TOKEN_1,TOKEN_2,TOKEN_3
   ```
2. Enter the faucet name.
3. Enter the Channel ID where the message will be sent.
4. Choose the method:
   - **Text-based claim**: Enter the claim message.
   - **Slash command claim**: Enter the slash command (e.g., `/faucet`), the wallet address, and the bot profile image URL.

   NOTE: If you claim a faucet, you only need to send a normal message, just write the message, but if the claim requires the slash command input feature `/` on the message you want to send, it will take you to input your wallet and bot profile link.
5. Enter the auto-claim interval, e.g.:
   ```
   6h → Bot will resend the message every 6 hours.
   30m → Bot will resend the message every 30 minutes.
   ```
   NOTE: Make sure to use lowercase letters, not uppercase letters!

6. Confirm and save the settings.
7. To activate the auto-claim feature, select `1️⃣ CLAIM ALL FAUCETS` in the main menu.

#### 3️⃣ View Channels Affected by Slow Mode
Displays channels under slow mode and their respective wait times before the next claim attempt.

#### 4️⃣ Exit
Quits the program.

## 📌 How to Mention Users or Channels in Messages

### 🔹 Mentioning Users
Use `<@user_id>` format. To get a user ID:
1. Open Discord and enable Developer Mode:
   - `User Settings` → `Advanced` → Enable Developer Mode.
2. Right-click the user profile you want to mention.
3. Select `Copy ID`.
4. Insert it in your message, e.g.:
   ```
   <@123456789012345678> 0x1232141512123321
   ```
   The bot will send a message mentioning the user.

### 🔹 Mentioning Channels
Use `<#channel_id>` format:
1. Enable Developer Mode.
2. Right-click the channel you want to mention.
3. Select `Copy ID`.
4. Insert it in the message input.

## ⚠️ IMPORTANT INFORMATION MUST BE READ!
If you use the slash command feature and don't need to solve the captcha. You can enter multiple discord tokens and choose option 1 to claim the faucet, but if you claim you need to solve a captcha, you cannot enter more than 1 discord token and you cannot use a VPS to run option 2. Option 2 can be run on Windows and make sure your browser is open and your Discord is logged in.

## 🎥 Video Tutorial
Watch the tutorial on how to get a channel ID here: ➡️ [YouTube Tutorial](#)

## 👤 Join Our Telegram Group!
Join our Telegram group for more bot scripts and discussions:
➡️ [Join Telegram Group](https://t.me/sam_xode)

## 💌 Contact
For questions or contributions, reach out via:
- **GitHub**: [sam-xode](https://github.com/sam-xode)
- **Twitter**: [@Sam_xode](https://twitter.com/Sam_xode)

