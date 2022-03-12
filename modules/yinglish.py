import random

import jieba
import jieba.posseg as pseg
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.parser.twilight import Twilight, RegexMatch
from graia.ariadne.model import Group, Member, Friend
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema

from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import QuoteSource

jieba.setLogLevel(20)

saya = Saya.current()
channel = Channel.current()

channel.name("Yinglish")
channel.author("nullqwertyuiop")
channel.description("淫语")

twilight = Twilight(
    [
        RegexMatch(r"淫语 .+")
    ]
)


@channel.use(
    ListenerSchema(
        listening_events=[FriendMessage],
        inline_dispatchers=[twilight]
    )
)
async def yinglish_handler(app: Ariadne, message: MessageChain, friend: Friend):
    if result := await Yinglish.handle(app, message, friend=friend):
        await MessageSender(result.strategy).send(app, result.message, message, friend, friend)


@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[twilight]
    )
)
async def yinglish_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await Yinglish.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class Yinglish(AbstractHandler):
    __name__ = "Yinglish"
    __description__ = "None"
    __usage__ = "None"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if message.asDisplay().startswith("淫语 "):
            original = message.asDisplay()[3:]
            if original != "":
                return MessageItem(MessageChain.create(Yinglish.chs2yin(original)), QuoteSource())

    @staticmethod
    def _trans(x, y, degree):
        if random.random() > degree:
            return x
        if x in ["，", "。", ","]:
            if random.random() < 0.333333:
                return "♡"
            if random.random() < 0.333333:
                return "☆"
            return "……"
        if x in ["!", "！"]:
            return "♡"
        if len(x) > 1 and random.random() < 0.333333:
            return f"{x[0]}……{x}"
        else:
            if y.startswith("n") and random.random() < 0.333333:
                x = "〇" * len(x)
            if random.random() < 0.5:
                return f"……{x}"
            return x

    @staticmethod
    def chs2yin(s, degree=0.5):
        return "".join([Yinglish._trans(x, y, degree) for x, y in pseg.cut(s, use_paddle=True)])
