import json
import random

import aiohttp
import requests
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage, FriendMessage, TempMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.ariadne.model import Friend
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema

from SAGIRIBOT.Handler.Handler import AbstractHandler
from SAGIRIBOT.MessageSender import Strategy
from SAGIRIBOT.MessageSender.MessageItem import MessageItem
from SAGIRIBOT.MessageSender.MessageSender import GroupMessageSender, FriendMessageSender, TempMessageSender
from SAGIRIBOT.MessageSender.Strategy import GroupStrategy, QuoteSource, FriendStrategy, TempStrategy
from SAGIRIBOT.ORM.AsyncORM import UserCalledCount
from SAGIRIBOT.decorators import switch, blacklist
from SAGIRIBOT.utils import update_user_call_count_plus1

saya = Saya.current()
channel = Channel.current()


@channel.use(ListenerSchema(listening_events=[FriendMessage]))
async def garbage_translation_handler(app: Ariadne, message: MessageChain, friend: Friend):
    if result := await GarbageTranslationHandler.handle(app, message, strategy=FriendStrategy, friend=friend):
        await FriendMessageSender(result.strategy).send(app, result.message, message, friend)


@channel.use(ListenerSchema(listening_events=[TempMessage]))
async def garbage_translation_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await GarbageTranslationHandler.handle(app, message, strategy=TempStrategy, group=group, member=member):
        await TempMessageSender(result.strategy).send(app, result.message, message, group, member)


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def garbage_translation_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await GarbageTranslationHandler.handle(app, message, strategy=GroupStrategy, group=group, member=member):
        await GroupMessageSender(result.strategy).send(app, result.message, message, group, member)


class GarbageTranslationHandler(AbstractHandler):
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
    async def handle(app: Ariadne, message: MessageChain, strategy: Strategy,
                     group: Group = None, member: Member = None, friend: Friend = None):
        if message.asDisplay().startswith("瞎翻译#"):
            text = message.asDisplay().split("#", maxsplit=1)[1]
            if member and group:
                await update_user_call_count_plus1(group, member, UserCalledCount.functions, "functions")
            return MessageItem(MessageChain.create([Plain(text=await GarbageTranslationHandler.get_translation(text))]),
                               QuoteSource(strategy()))
        elif message.asDisplay() == "更新瞎翻译 Cookies":
            return MessageItem(MessageChain.create([Plain(text=await GarbageTranslationHandler.update_cookie())]),
                               QuoteSource(strategy()))
        elif message.asDisplay().startswith("翻译#"):
            text = message.asDisplay().split("#", maxsplit=1)[1]
            if member and group:
                await update_user_call_count_plus1(group, member, UserCalledCount.functions, "functions")
            return MessageItem(MessageChain.create([
                Plain(text=await GarbageTranslationHandler.get_translation(msg=text, times=0))
            ]), QuoteSource(strategy()))
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
        for i in range(times):
            this_lang = random.choice(GarbageTranslationHandler.lang)
            while this_lang == last_lang:
                this_lang = random.choice(GarbageTranslationHandler.lang)
            url = f'https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=auto&tl={this_lang}&q={translated}'
            try:
                async with aiohttp.ClientSession(
                        cookies=GarbageTranslationHandler.cookies,
                        headers=GarbageTranslationHandler.headers) as session:
                    async with session.get(url=url, headers=GarbageTranslationHandler.headers) as resp:
                        result = await resp.json()
            except json.decoder.JSONDecodeError:
                await GarbageTranslationHandler.update_cookie()
                try:
                    async with aiohttp.ClientSession(
                            cookies=GarbageTranslationHandler.cookies,
                            headers=GarbageTranslationHandler.headers) as session:
                        async with session.get(url=url, headers=GarbageTranslationHandler.headers) as resp:
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
            async with aiohttp.ClientSession(
                    cookies=GarbageTranslationHandler.cookies,
                    headers=GarbageTranslationHandler.headers) as session:
                async with session.get(url=url, headers=GarbageTranslationHandler.headers) as resp:
                    result = await resp.json()
        except json.decoder.JSONDecodeError:
            await GarbageTranslationHandler.update_cookie()
            try:
                async with aiohttp.ClientSession(
                        cookies=GarbageTranslationHandler.cookies,
                        headers=GarbageTranslationHandler.headers) as session:
                    async with session.get(url=url, headers=GarbageTranslationHandler.headers) as resp:
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
        try:
            GarbageTranslationHandler.cookies = requests.Session().get('https://translate.google.com',
                                                                       headers=GarbageTranslationHandler.headers).cookies
            return "更新 Cookie 成功。"
        except:
            return "更新 Cookie 失败。"
