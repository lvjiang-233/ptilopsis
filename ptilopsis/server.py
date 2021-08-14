from . import config
from .behavior import after_login

from aiohttp import web
from aiogram import Bot

class Server(web.Application):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot
        self.add_routes([web.get(config.REDIRECT_PATH, self.getauth)])

    async def getauth(self, request:web.Request):
        try:
            user_id = request.query['state']
            code = request.query['code']
            await after_login(int(user_id), code)
            return web.Response(text='The code has been sent to the bot')
        except:
            error = request.query['error']
            description = request.query['error_description']
            return web.Response(text=f'Error {error} has occurred, details is {description}')
