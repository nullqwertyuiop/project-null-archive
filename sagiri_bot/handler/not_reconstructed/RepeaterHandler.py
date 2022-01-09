import re

from graia.ariadne.message.element import Image
from graia.saya import Saya, Channel
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.ariadne.event.message import Group, Member, GroupMessage

from SAGIRIBOT.utils import get_setting
from SAGIRIBOT.ORM.AsyncORM import Setting
from SAGIRIBOT.decorators import switch, blacklist
from SAGIRIBOT.Handler.Handler import AbstractHandler
from SAGIRIBOT.MessageSender.MessageItem import MessageItem
from SAGIRIBOT.MessageSender.Strategy import GroupStrategy, Normal
from SAGIRIBOT.MessageSender.MessageSender import GroupMessageSender

saya = Saya.current()
channel = Channel.current()


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def repeater_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await RepeaterHandler.handle(app, message, group, member):
        await GroupMessageSender(result.strategy).send(app, result.message, message, group, member)


class RepeaterHandler(AbstractHandler):
    """
    复读Handler
    """
    __name__ = "RepeaterHandler"
    __description__ = "一个复读Handler"
    __usage__ = "有两条以上相同信息时自动触发"

    group_repeat = {}

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group, member: Member):
        message_serialization = message.asPersistentString()
        if await get_setting(group.id, Setting.repeat):
            if message.has(Image) and not await get_setting(group.id, Setting.trusted):
                return None
            if group.id in RepeaterHandler.group_repeat.keys():
                if message_serialization == RepeaterHandler.group_repeat[group.id]["msg"]:
                    count = RepeaterHandler.group_repeat[group.id]["count"] + 1
                    if count == 3:
                        RepeaterHandler.group_repeat[group.id]["count"] = count
                        return MessageItem(message.asSendable(), Normal())
                    else:
                        RepeaterHandler.group_repeat[group.id]["count"] = count
                        return None
                else:
                    RepeaterHandler.group_repeat[group.id]["msg"] = message_serialization
                    RepeaterHandler.group_repeat[group.id]["count"] = 1
            else:
                RepeaterHandler.group_repeat[group.id] = {"msg": message_serialization, "count": 1}
        return None
