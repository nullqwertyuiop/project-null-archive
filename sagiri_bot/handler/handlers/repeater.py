from graia.ariadne.message.element import Image
from graia.saya import Saya, Channel
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.ariadne.event.message import Group, Member, GroupMessage

from sagiri_bot.utils import get_setting
from sagiri_bot.orm.async_orm import Setting
from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.message_sender.strategy import Normal
from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender

saya = Saya.current()
channel = Channel.current()


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def repeater(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await Repeater.handle(app, message, group, member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class Repeater(AbstractHandler):
    """
    复读Handler
    """
    __name__ = "Repeater"
    __description__ = "一个复读Handler"
    __usage__ = "有两条以上相同信息时自动触发"

    group_repeat = {}
    
    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group, member: Member):
        message_serialization = message.asPersistentString()
        if await get_setting(group.id, Setting.repeat):
            if group.id in Repeater.group_repeat.keys():
                pass
            else:
                if message_serialization == Repeater.group_repeat[group.id]["msg"]:
                    count = Repeater.group_repeat[group.id]["count"] + 1
                    if count == 3:
                        if message.has(Image) and not await get_setting(group.id, Setting.trusted):
                            return None
                        Repeater.group_repeat[group.id]["count"] = count
                        return MessageItem(message.asSendable(), Normal())
                    else:
                        Repeater.group_repeat[group.id]["count"] = count
                        return None
                else:
                    Repeater.group_repeat[group.id]["msg"] = message_serialization
                    Repeater.group_repeat[group.id]["count"] = 1
                Repeater.group_repeat[group.id] = {"msg": message_serialization, "count": 1}
        return None
