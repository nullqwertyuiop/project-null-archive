import json
import os
import random
import re
from random import randrange

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema

from SAGIRIBOT.Handler.Handler import AbstractHandler
from SAGIRIBOT.MessageSender.MessageItem import MessageItem
from SAGIRIBOT.MessageSender.MessageSender import GroupMessageSender
from SAGIRIBOT.MessageSender.Strategy import GroupStrategy, QuoteSource
from SAGIRIBOT.decorators import switch, blacklist

saya = Saya.current()
channel = Channel.current()
with open(f"{os.getcwd()}/statics/juejuezi.json", "r", encoding="utf-8") as r:
    juejuezi = json.loads(r.read())


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def jue_jue_zi_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await JueJueZiHandler.handle(app, message, group, member):
        await GroupMessageSender(result.strategy).send(app, result.message, message, group, member)


class JueJueZiHandler(AbstractHandler):
    __name__ = "JueJueZiHandler"
    __description__ = "绝绝子 Handler"
    __usage__ = "None"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group, member: Member):
        if re.match("绝绝子#.*#.*", message.asDisplay()):
            _, do, what = message.asDisplay().split("#")
            return MessageItem(MessageChain.create([Plain(text=await JueJueZiHandler.generate(do, what))]),
                               QuoteSource(GroupStrategy()))

    @staticmethod
    async def generate(do: str, what: str):
        result = ""
        divider = random.choice(juejuezi["dividers"])
        part1 = str(random.choice(juejuezi["beginning"])).replace("who", str(random.choice(juejuezi["who"]))).replace("someone", str(random.choice(juejuezi["someone"])))
        part2 = str(random.choice(juejuezi["emotions"]["emoji"]))
        part3 = str(random.choice(juejuezi["fashion"]))
        part4 = str(random.choice(juejuezi["todosth"])).replace("dosth", str(do + what))
        part5 = str(random.choice(juejuezi["attribute"])).replace("dosth", str(do)) + str(random.choice(juejuezi["auxiliaryWords"]))
        part6 = str(random.choice(juejuezi["collections"])) + str(random.choice(juejuezi["fashion"]))
        part7 = str(random.choice(juejuezi["attribute"])).replace("dosth", str(do))
        part8 = str(random.choice(juejuezi["ending"]))
        part_list = [part1, part2, part3, part4, part5, part6, part7, part8]
        for i in part_list:
            result = result + i
            if randrange(0, 2) and i != part5:
                result = result + str(random.choice(juejuezi["auxiliaryWords"]))
            if randrange(0, 2):
                result = result + str(random.choice(juejuezi["symbols"]))
            if randrange(0, 2):
                result = result + str(random.choice(juejuezi["emotions"]["emoji"]))
            result = result + divider
        return result
