import environs
import logging

env = environs.Env()
env.read_env()

BOT_TOKEN = env.str('BOT_TOKEN')
WEBHOOK_URL = env.str('WEBHOOK_URL', default='')
ADMIN_ID = env.int('ADMIN_ID')
MODE = env.str('MODE', default='polling')
PORT = env.int('PORT', default=80)
HTTP_PROXY = env.str('HTTP_PROXY', default='')

CLIENT_ID = env.str('CLIENT_ID')
CLIENT_SECRET = env.str('CLIENT_SECRET')
REDIRECT_PATH = env.str('REDIRECT_PATH')

GOOGLE_CERT = env.str('GOOGLE_CERT')
FIREBASE_NAME = env.str('FIREBASE_NAME', default='onedrive-bot')

logging.basicConfig(level=logging.INFO)