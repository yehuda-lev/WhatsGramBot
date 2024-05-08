# WhatsGramBot

## Description

WhatsGramBot is a Python bot primarily designed for managing a bot on WhatsApp. It utilizes a Telegram group to organize WhatsApp Chats according to topics, enhancing the management of WhatsApp conversations.


### Features:

1. User-Based Messaging Organization:
   - Each WhatsApp user is assigned a dedicated topic within a Telegram group.
   - Messages from WhatsApp users are forwarded to their respective topics within the Telegram group.
   - Telegram group administrators can respond to messages from WhatsApp within the Telegram group, facilitating collaborative communication.

2. Settings Configuration (/settings command):
   - Enable or disable welcome messages and customize their content.
   - Toggle automatic topic creation when a user opens a chat with the bot on WhatsApp. When enabled, a welcome message and topic creation occur immediately upon chat opening, even if the user hasn't sent a message yet.
   - Toggle mark messages as read as soon as new replies are sent to the user on WhatsApp.

3. Information Retrieval (/info command):
   - Obtain details about specific user topics and their configurations.


## Setup

1. Clone the repository

```bash
git clone https://github.com/yehuda-lev/WhatsGramBot.git
```


## Setting up Environment Variables

To set up the environment variables for the project, follow these steps:

1. **Copy the `.env.example` file:**

```bash
cp .env.example .env
```

1. **Edit the `.env` file:**
   - Open the `.env` file in a text editor of your choice.
   - Replace the placeholder values with your actual credentials. You can obtain these credentials from the following sources:

     - **Telegram Credentials:**
       - `TG_API_ID` and `TG_API_HASH`: Obtain from [my.telegram.org](https://my.telegram.org).
       - `TG_BOT_TOKEN`: Create a new bot on [BotFather](https://t.me/BotFather).
       - `TG_GROUP_TOPIC_ID`: ID of the Telegram group where the bot will operate.

     - **WhatsApp Credentials:**
       - `WA_PHONE_ID`, `WA_BUSINESS_ID`, `WA_VERIFY_TOKEN`, `WA_TOKEN`, `WA_PHONE_NUMBER`: Create a WhatsApp application following the guide [here](https://pywa.readthedocs.io/en/latest/content/getting-started.html#create-a-whatsapp-application).
       - `WA_APP_ID` and `WAAPP_SECRET`: Obtain from your Facebook developers account under "App Settings" > "Basic". Access all your apps [here](https://developers.facebook.com/apps/).
       - `WA_CALLBACK_URL`: URL for the webhook to receive incoming messages from WhatsApp. You can use a service like [ngrok](https://ngrok.com/) to create a secure tunnel to your local server.
       - `WEBHOOK_ENDPOINT`: Endpoint to register the webhook for the bot (will become `WA_CALLBACK_URL/WEBHOOK_ENDPOINT`)
     
     - **General Settings:**
       - `PORT`: Port number to run the server on (default is 8080).
       - `DEBUG`: Set to `true` to enable debug mode, which logs additional information to the console (default is `false`).
       - `HTTPX_TIMEOUT`: Timeout for HTTP requests in seconds. change if running on a slow network or server (default is 15.0 seconds).

2. **Save the `.env` file:**
   - After editing, save the changes to the `.env` file.

By completing these steps, your environment variables will be properly configured for the project.


## Installation

Clone the repository to your local machine. Then, build the Docker image using the following command:

> If you want to rebuild the image, you can use the `--build` flag to force a rebuild:
> If you want to run the bot in the background, you can use the `-d` flag:
```bash
docker compose up
```

##  Credits
This project was created by [@yehudalev](https://t.me/yehudalev).


## Screenshots


<details>
  <summary>Telegram Group (Desktop)</summary>

![image](https://gist.github.com/assets/42866208/77c1da4e-1ab7-4d78-8984-56bb70901e24)
</details>


<details>
  <summary>WhatsApp Chat (Mobile)</summary>

  ![image](https://gist.github.com/assets/42866208/7f2388af-c488-4ffe-8185-b1c77a830878)
</details>

<details>
  <summary>Telegram Group (Mobile)</summary>

![image](https://gist.github.com/assets/42866208/5620636a-e6c2-40b2-a9c2-a6541f40a33e)
</details>


<details>
  <summary>WhatsApp Chat (Desktop)</summary>

   ![image](https://gist.github.com/assets/42866208/ef097026-857f-4d77-ac44-26875e076498)
</details>


