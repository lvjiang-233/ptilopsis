from . import config
from .behavior import bot, dp, set_webhook_for_bot
from .server import Server

from aiogram import executor

if __name__ == '__main__':
    if config.MODE == 'polling':
        executor.start_polling(dp, skip_updates=True)
    elif config.MODE == 'webhook':
        executor = executor.set_webhook(dispatcher=dp,
                                        webhook_path='/' + config.BOT_TOKEN,
                                        on_startup=set_webhook_for_bot,
                                        web_app=Server(bot))
        executor.run_app(host="0.0.0.0", port=config.PORT)