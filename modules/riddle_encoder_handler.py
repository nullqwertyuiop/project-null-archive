import re

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage, FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.ariadne.model import Friend
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
from loguru import logger

from sagiri_bot.core.app_core import AppCore
from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import Revoke

saya = Saya.current()
channel = Channel.current()
core: AppCore = AppCore.get_core_instance()
config = core.get_config()

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
    __base = config.functions['riddle']['base']
    if __base.isdigit():
        __base = int(__base)
        if __base > 20901:
            logger.error("Base 值超过最大值，取最大值 `20901`")
            __base = 20901
    else:
        logger.error("Base 类型错误，回落至默认值 `100`")
        __base = 100
    __mod = config.functions['riddle']['mod']
    if __mod.isdigit():
        __mod = int(__base)
        if __mod <= __base:
            logger.error("Mod 值无效，回落至默认值 `65535`")
            __mod = 65535
        while __base % __mod == 0:
            __mod += 1
        if __mod != int(config.functions['riddle']['mod']):
            logger.error(f"Mod 值无效，自动偏移至 {__mod}")
    else:
        logger.error("Base 类型错误，回落至默认值 `65535`")
        __mod = 65535
    __keys = "".join([chr(char) for char in range(19968, 19968 + __base)])

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if re.match("加密通话#(编码|解码|encode|decode)#(.*)", message.asDisplay()):
            processed = message.asDisplay().split("#", maxsplit=3)
            _, mode, key = processed
            if mode in ("encode", "编码"):
                return MessageItem(MessageChain.create([
                    Plain(text=RiddleEncoderHandler.base100encode(
                        RiddleEncoderHandler.base114514decode(key))
                    )
                ]), Revoke(delay_second=10))
            elif mode in ("decode", "解码"):
                return MessageItem(MessageChain.create([
                    Plain(text=RiddleEncoderHandler.base114514encode(
                        RiddleEncoderHandler.base100decode(key))
                    )
                ]), Revoke(delay_second=60))
        else:
            return None

    @staticmethod
    def base100encode(n):
        result = ''
        while n > 0:
            result = RiddleEncoderHandler.__keys[n % 100] + result
            n //= 100
        return result

    @staticmethod
    def base114514decode(s):
        result = 0
        for c in s:
            result = result * 114514 + ord(c)
        return result

    @staticmethod
    def base114514encode(n):
        result = ''
        while n > 0:
            result = chr(n % 114514) + result
            n //= 114514
        return result

    @staticmethod
    def base100decode(s):
        result = 0
        for c in s:
            result = result * 100 + RiddleEncoderHandler.__keys.find(c)
        return result
