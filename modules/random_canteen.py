import json
import os
import random

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema

from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import QuoteSource
from sagiri_bot.decorators import switch, blacklist

saya = Saya.current()
channel = Channel.current()
with open(f"{os.getcwd()}/statics/food.json", "r", encoding="utf-8") as r:
    food = json.loads(r.read())


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def jue_jue_zi_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await RandomCanteenHandler.handle(app, message, group, member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class RandomCanteenHandler(AbstractHandler):
    __name__ = "RandomCanteen"
    __description__ = "随机饮食模块"
    __usage__ = "None"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group, member: Member):
        if message.asDisplay() in ("#这顿在哪吃", "#这顿去哪吃"):
            canteen = random.choice(
                ["新百味食堂（南一）", "汉鑫食堂（南二）", "心怡食堂（北一）", "龙江食堂（北四）", "金虔食堂（北三）", "北二食堂"]
            )
            return MessageItem(MessageChain.create([Plain(text=f"这顿去{canteen}吃")]),
                               QuoteSource())
