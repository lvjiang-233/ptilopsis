from . import config
from .manager import OneDriveManager

import os
import logging
from typing import List
from marshmallow.utils import is_instance_or_subclass
from aiogram import Bot, Dispatcher, types
from aiogram.types.mixins import Downloadable
from aiogram.types.message import ContentType
from aiogram.utils import exceptions

bot = Bot(token=config.BOT_TOKEN, proxy=config.HTTP_PROXY)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    await message.reply("Hi!\nI'm EchoBot!\nPowered by aiogram.")

@dp.message_handler(commands=['login'])
async def generate_login_url(message: types.Message):
    user_id = message.from_user.id
    target_url = OneDriveManager.generate_login_url(user_id)
    await message.reply(text=target_url)

@dp.message_handler(commands=['folder'])
async def set_folder(message: types.Message):
    manager = OneDriveManager(message.from_user.id)
    if await manager.init():
        folder_path = message.get_args()
        if await manager.set_folder_path(folder_path):
            await message.reply(text='success')
        else:
            await message.reply(text='fail')
    else:
        await message.reply('Please login first')

@dp.message_handler(content_types=[ContentType.DOCUMENT, ContentType.VIDEO, ContentType.PHOTO])
async def download(message: types.Message):
    manager = OneDriveManager(message.from_user.id)
    if await manager.init():
        if not await manager.folder_path_validation():
            await message.reply(text='Please set the correct folder path')
            return
        else:
            content = getattr(message, message.content_type, None)
            if content is not None:
                # gain origin file from list
                if is_instance_or_subclass(content, List):
                    content = sorted(content, key=lambda file: file.file_size)[-1]
                # download suitable content
                if is_instance_or_subclass(content, Downloadable):
                    if hasattr(content, 'file_name'):
                        file_name = getattr(content, 'file_name')
                    else:
                        # Get file name through the File object generate by `get_file`
                        file = await bot.get_file(content.file_id)
                        file_name = file.file_path.split('/')[-1]
                    file_path=f'data/{message.from_user.id}/{file_name}'
                        
                    if not os.path.exists(f'data/{message.from_user.id}'):
                        os.makedirs(f'data/{message.from_user.id}')

                    try:
                        des = await content.download(destination=file_path)
                        logging.info(f'File download success, stored in {file_path}')

                        await manager.upload(des.name)
                        logging.info('File upload success')
                        
                        await message.reply('Done!')
                    except exceptions.FileIsTooBig as e:
                        await message.reply(text='This file is too big')
                    except Exception as e:
                        logging.error(str(e))
    else:
        await message.reply(text='Please login first.')

@dp.message_handler()
async def echo(message: types.Message):
    await bot.send_message(message.from_user.id, text=message.text)


async def set_webhook_for_bot(dp):
    await bot.set_webhook(url=config.WEBHOOK_URL + config.BOT_TOKEN)

async def after_login(user_id: int, auth_code: str):
    await OneDriveManager.get_token_by_auth_code(auth_code, user_id)
    await bot.send_message(user_id, text='Login success!')