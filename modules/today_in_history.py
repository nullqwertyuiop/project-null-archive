import json
import math
import os
import re
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema

from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import QuoteSource, Normal
from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.utils import MessageChainUtils

saya = Saya.current()
channel = Channel.current()


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def jue_jue_zi_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await TodayInHistoryHandler.handle(app, message, group, member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class TodayInHistoryHandler(AbstractHandler):
    __name__ = "TodayInHistoryHandler"
    __description__ = "历史上的今天 Handler"
    __usage__ = "None"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group, member: Member):
        if message.asDisplay().startswith("历史上的今天"):
            msg = message.asDisplay().split(" ")
            if len(msg) == 1:
                return MessageItem(MessageChain.create(
                    await TodayInHistoryHandler.get_today()
                ), Normal())
            elif len(msg) == 2:
                try:
                    page = int(msg[1])
                    if page == 0:
                        text_msg = MessageChain.create(await TodayInHistoryHandler.get_today(page=0))
                        return MessageItem(await MessageChainUtils.messagechain_to_img(text_msg),
                                           Normal())
                    return MessageItem(MessageChain.create(
                        await TodayInHistoryHandler.get_today(page=page)
                    ), Normal())
                except ValueError:
                    event_type = str(msg[1])
                    if event_type not in ("大事记", "出生", "逝世"):
                        return MessageItem(MessageChain.create([Plain(text=f"类型非法。")]), QuoteSource())
                    return MessageItem(MessageChain.create(
                        await TodayInHistoryHandler.get_today(event_type=event_type)
                    ), Normal())
            elif len(msg) == 3:
                try:
                    event_type = str(msg[1])
                    page = int(msg[2])
                    if page == 0:
                        text_msg = MessageChain.create(await TodayInHistoryHandler.get_today(page=0))
                        return MessageItem(await MessageChainUtils.messagechain_to_img(text_msg),
                                           Normal())
                    if event_type not in ("大事记", "出生", "逝世"):
                        return MessageItem(MessageChain.create([Plain(text=f"类型非法。")]), QuoteSource())
                    return MessageItem(MessageChain.create(
                        await TodayInHistoryHandler.get_today(page=page, event_type=event_type)
                    ), Normal())
                except ValueError:
                    return MessageItem(MessageChain.create([Plain(text=f"页数非法。")]), QuoteSource())
        else:
            return None

    @staticmethod
    async def get_today(page: int = 1, event_type: str = "大事记"):
        with open(f"{os.getcwd()}/statics/censor.json", "r", encoding="utf-8") as r:
            censored_words = json.loads(r.read())
        date = f"{datetime.now().month}月{datetime.now().day}日"
        url = "https://zh.wikipedia.org/zh-cn/%s" % date
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url) as resp:
                html = await resp.text()
        flag = re.compile(
            "(<h2><span id=\".*?\"></span><span class=\"mw-headline\" id=.*?" + event_type + "[\s\S]*?</ul>\s*?)<h2>"
        ).search(html)
        if flag:
            obj = BeautifulSoup(flag.group(1), "html.parser").findAll("li")
            events = []
            for li in obj:
                li = re.sub("\[.*]", "", li.get_text())
                events.append(li)
            events.reverse()
            minimum = (page - 1) * 10
            response = []
            if page == 0:
                minimum = 0
                maximum = len(events)
            elif page * 10 - len(events) >= 10:
                response.append(Plain(text=f"页数非法。"))
                return response
            else:
                maximum = minimum + 10
            response.extend([
                Plain(text=f"历史上的今天"),
                Plain(text=f"\n----------")
            ])
            for event in events[minimum:maximum]:
                for censored in censored_words['censor']:
                    event = event.replace(censored, "[CENSORED]")
                response.append(Plain(f"\n{event}"))
            if page != 0:
                response.extend([
                    Plain(text=f"\n----------"),
                    Plain(text=f"\n第 {page} 页，共 {math.ceil(len(events) / 10)} 页"),
                    Plain(text=f'\n发送 "历史上的今天 页数" 翻页'),
                    Plain(text=f'\n发送 "历史上的今天 0" 查看所有内容')
                ])
            return response
