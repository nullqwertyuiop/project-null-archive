import json
import random

import aiohttp
import requests
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage, FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.ariadne.model import Friend
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema

from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import QuoteSource
from sagiri_bot.orm.async_orm import UserCalledCount
from sagiri_bot.utils import update_user_call_count_plus

saya = Saya.current()
channel = Channel.current()

channel.name("GarbageTranslation")
channel.author("nullqwertyuiop")
channel.description("翻译、瞎翻译")


@channel.use(ListenerSchema(listening_events=[FriendMessage]))
async def garbage_translation_handler(app: Ariadne, message: MessageChain, friend: Friend):
    if result := await GarbageTranslation.handle(app, message, friend=friend):
        await MessageSender(result.strategy).send(app, result.message, message, friend, friend)


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def garbage_translation_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await GarbageTranslation.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class GarbageTranslation(AbstractHandler):
    __name__ = "GarbageTranslation"
    __description__ = "瞎翻译模块"
    __usage__ = "None"
    # lang = ['en', 'ja', 'de', 'ko', 'ru', 'la', 'th', 'it', 'fr', 'ar', 'zh']
    lang = ['en', 'ja', 'ko', 'ru', 'zh']
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36'
    }
    cookies = None

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if message.asDisplay().startswith("瞎翻译#"):
            text = message.asDisplay().split("#", maxsplit=1)[1]
            if member and group:
                await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
            return MessageItem(MessageChain.create([Plain(text=await GarbageTranslation.get_translation(text))]),
                               QuoteSource())
        elif message.asDisplay() == "更新瞎翻译 Cookies":
            return MessageItem(MessageChain.create([Plain(text=await GarbageTranslation.update_cookie())]),
                               QuoteSource())
        elif message.asDisplay().startswith("翻译#"):
            text = message.asDisplay().split("#", maxsplit=1)[1]
            if member and group:
                await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
            return MessageItem(MessageChain.create([
                Plain(text=await GarbageTranslation.get_translation(msg=text, times=0))
            ]), QuoteSource())
        else:
            return None

    @staticmethod
    async def get_translation(msg: str, times: int = 50):
        split_list = msg.split("#", maxsplit=1)
        if len(split_list) == 2:
            try:
                times = int(split_list[0])
                if times > 1024:
                    return "重复次数过多。"
                translated = split_list[1]
            except ValueError:
                translated = msg
        else:
            translated = msg
        last_lang = ""
        session = aiohttp.ClientSession(
            cookies=GarbageTranslation.cookies,
            headers=GarbageTranslation.headers
        )
        for i in range(times):
            this_lang = random.choice(GarbageTranslation.lang)
            while this_lang == last_lang:
                this_lang = random.choice(GarbageTranslation.lang)
            url = f'https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=auto&tl={this_lang}&q={translated}'
            try:
                async with session.get(url=url, headers=GarbageTranslation.headers) as resp:
                    result = await resp.json()
            except json.decoder.JSONDecodeError:
                await GarbageTranslation.update_cookie()
                try:
                    async with session.get(url=url, headers=GarbageTranslation.headers) as resp:
                        result = await resp.json()
                except:
                    return "出错，请检查您的输入内容是否过长。"
            last_lang = this_lang
            translated = ""
            if isinstance(result['sentences'], str):
                translated = translated + result['sentences']
                continue
            for j in range(len(result['sentences'])):
                try:
                    translated = translated + result['sentences'][j]['trans']
                except:
                    continue
        url = f'https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=auto&tl=zh&q={translated}'
        try:
            async with session.get(url=url, headers=GarbageTranslation.headers) as resp:
                result = await resp.json()
        except json.decoder.JSONDecodeError:
            await GarbageTranslation.update_cookie()
            try:
                async with session.get(url=url, headers=GarbageTranslation.headers) as resp:
                    result = await resp.json()
            except:
                return "出错，请检查您的输入内容是否过长。"
        translated = ""
        for j in range(len(result['sentences'])):
            try:
                translated = translated + result['sentences'][j]['trans']
            except:
                pass
        return translated

    @staticmethod
    async def update_cookie():
        session = aiohttp.ClientSession(
            headers=GarbageTranslation.headers
        )
        try:
            async with session.get('https://translate.google.com') as resp:
                GarbageTranslation.cookies = resp.cookies
            return "更新 Cookie 成功。"
        except:
            return "更新 Cookie 失败。"
