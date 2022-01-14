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
from sagiri_bot.message_sender.strategy import QuoteSource, Revoke
from sagiri_bot.decorators import switch, blacklist

saya = Saya.current()
channel = Channel.current()

channel.name("RiddleEncoder")
channel.author("nullqwertyuiop")
channel.description("加密通话")


@channel.use(ListenerSchema(listening_events=[FriendMessage]))
async def riddle_encoder_handler(app: Ariadne, message: MessageChain, friend: Friend):
    if result := await RiddleEncoderHandler.handle(app, message, friend=friend):
        await MessageSender(result.strategy).send(app, result.message, message, friend, friend)


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def riddle_encoder_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await RiddleEncoderHandler.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class RiddleEncoderHandler(AbstractHandler):
    __name__ = "RiddleEncoderHandler"
    __description__ = "谜语编码解码 Handler"
    __usage__ = "None"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if re.match("加密通话#(编码|解码|encode|decode)#(.*)(#(.*))?", message.asDisplay()):
            processed = message.asDisplay().split("#", maxsplit=3)
            if len(processed) == 3:
                _, mode, key = processed
                offset = randrange(10000) + 1
                if mode in ("encode", "编码"):
                    return MessageItem(MessageChain.create([Plain(text=await RiddleEncoderHandler.encode(offset, key))]), Revoke(delay_second=10))
                elif mode in ("decode", "解码"):
                    return MessageItem(MessageChain.create([Plain(text=await RiddleEncoderHandler.decode(key))]), Revoke(delay_second=60))
            elif len(processed) == 4:
                _, mode, offset, key = processed
                try:
                    offset = int(offset)
                except ValueError:
                    return MessageItem(MessageChain.create([Plain(text=f"偏移量仅支持 1~10000 间整数")]), QuoteSource())
                if not (0 < offset <= 10000):
                    return MessageItem(MessageChain.create([Plain(text=f"偏移量仅支持 1~10000 间整数")]), QuoteSource())
                if mode in ("encode", "编码"):
                    return MessageItem(MessageChain.create([Plain(text=await RiddleEncoderHandler.encode(offset, key))]), Revoke(delay_second=10))
                elif mode in ("decode", "解码"):
                    return MessageItem(MessageChain.create([Plain(text=await RiddleEncoderHandler.decode(key, offset))]), Revoke(delay_second=60))
        else:
            return None

    @staticmethod
    async def encode(offset: int, key: str):
        encoded = chr(offset)
        step = randrange(10) + 1
        encoded = encoded + chr(step + offset)
        for i in key:
            encoded = encoded + chr(ord(i) + offset)
            offset += step
        return encoded

    @staticmethod
    async def decode(key: str, offset=None):
        remove_first = True if not offset else False
        offset = ord(key[0]) if not offset else offset
        step = ord(key[1]) - offset if remove_first else ord(key[0]) - offset
        decoded = ""
        for i in range(len(key)):
            if i == 0 and remove_first:
                continue
            if i == 1 and remove_first:
                continue
            try:
                decoded = decoded + chr(ord(key[i]) - offset)
                offset += step
            except ValueError:
                return "无效数据。"
        return decoded
