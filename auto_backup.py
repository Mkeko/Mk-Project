from dotenv import load_dotenv
import os
from discord_webhook import DiscordWebhook
from datetime import datetime

# Load environment variables from a .env file
load_dotenv()

# Fetch the webhook URL from the environment variables
webhook_url = os.getenv("WEBHOOK_URL")

# List of database file paths to be backed up
DB_PATHS = [
    "db/economy.db",
    "db/giveaways.db",
    "db/levelsys.db",
    "db/configs.db",
    "db/automod.db"
]

# Ensure the webhook URL is provided
if not webhook_url:
    print("Error: WEBHOOK_URL not found in environment variables.")
    exit(1)

try:
    # Create the webhook with the current timestamp
    webhook = DiscordWebhook(
        url=webhook_url,
        content=f"Backup Timestamp: <t:{round(datetime.now().timestamp())}:f>"
    )

    # Attach each database file to the webhook
    for db_path in DB_PATHS:
        if os.path.exists(db_path):
            with open(db_path, "rb") as f:
                webhook.add_file(file=f.read(), filename=os.path.basename(db_path))
        else:
            print(f"Warning: {db_path} not found, skipping.")

    # Send the webhook and handle the response
    response = webhook.execute()

    if response.status_code == 200:
        print("Backup successfully sent.")
    else:
        print(f"Failed to send backup. HTTP Status Code: {response.status_code}")

except Exception as e:
    print(f"An unexpected error occurred: {e}")
