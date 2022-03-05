import json
import os
import random
import re
from random import randrange

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage, FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.ariadne.model import Friend
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema

from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import QuoteSource
from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.utils import HelpPage, HelpPageElement

saya = Saya.current()
channel = Channel.current()

channel.name("JueJueZi")
channel.author("nullqwertyuiop")
channel.description("绝绝子")


with open(f"{os.getcwd()}/statics/juejuezi.json", "r", encoding="utf-8") as r:
    juejuezi = json.loads(r.read())


@channel.use(ListenerSchema(listening_events=[FriendMessage]))
async def jue_jue_zi_handler(app: Ariadne, message: MessageChain, friend: Friend):
    if result := await JueJueZi.handle(app, message, friend=friend):
        await MessageSender(result.strategy).send(app, result.message, message, friend, friend)


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def jue_jue_zi_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await JueJueZi.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class JueJueZi(AbstractHandler):
    __name__ = "JueJueZi"
    __description__ = "绝绝子 Handler"
    __usage__ = "None"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if re.match("绝绝子#.*#.*", message.asDisplay()):
            _, do, what = message.asDisplay().split("#")
            return MessageItem(MessageChain.create([Plain(text=await JueJueZi.generate(do, what))]),
                               QuoteSource())

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


class JueJueZiHelp(HelpPage):
    __description__ = "绝绝子"
    __trigger__ = "绝绝子#内容#内容"
    __category__ = 'entertainment'
    __switch__ = None
    __icon__ = "heart"

    def __init__(self, group: Group = None, member: Member = None, friend: Friend = None):
        super().__init__()
        self.__help__ = None
        self.group = group
        self.member = member
        self.friend = friend

    async def compose(self):
        self.__help__ = [
            HelpPageElement(icon=self.__icon__, text="绝绝子", is_title=True),
            HelpPageElement(text="自动生成\"绝绝子风格\"的文本"),
            HelpPageElement(icon="check-all", text="已全局开启"),
            HelpPageElement(icon="lightbulb-on", text="使用示例：\n发送\"绝绝子#动词#名词\"即可")
        ]
        super().__init__(self.__help__)
        return await super().compose()
