from typing import Optional
from asyncio import Semaphore

from graia.ariadne.message.element import Image, Plain, At, Quote, AtAll, Face, Poke
from graia.ariadne.model import Friend
from graia.saya import Saya, Channel
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.ariadne.event.message import Group, Member, GroupMessage

from sagiri_bot.utils import group_setting
from sagiri_bot.orm.async_orm import Setting
from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.message_sender.strategy import Normal
from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem

saya = Saya.current()
channel = Channel.current()

channel.name("Repeater")
channel.author("SAGIRI-kawaii")
channel.description("一个复读插件，有两条以上相同信息时自动触发")

mutex = Semaphore(1)


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def repeater(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await Repeater.handle(app, message, group=group, member=member):
        await app.sendMessage(group, result.message)


class Repeater(AbstractHandler):
    """
    复读Handler
    """
    __name__ = "Repeater"
    __description__ = "一个复读插件"
    __usage__ = "有两条以上相同信息时自动触发"

    group_repeat = {}
    
    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None) -> Optional[MessageItem]:
        message_serialization = message.asPersistentString()
        if await group_setting.get_setting(group.id, Setting.repeat):
            if group.id not in Repeater.group_repeat.keys():
                Repeater.group_repeat[group.id] = {"msg": message_serialization, "count": 1}
            else:
                if message_serialization == Repeater.group_repeat[group.id]["msg"]:
                    if Repeater.group_repeat[group.id]["count"] == -1:
                        return None
                    count = Repeater.group_repeat[group.id]["count"] + 1
                    if count == 3:
                        Repeater.group_repeat[group.id]["count"] = count
                        if message.has(Image) and not await group_setting.get_setting(group.id, Setting.trusted):
                            return None
                        msg = message.include(Plain, Image, At, Quote, AtAll, Face, Poke)
                        return MessageItem(msg.asSendable(), Normal())
                    else:
                        Repeater.group_repeat[group.id]["count"] = count
                        return None
                else:
                    Repeater.group_repeat[group.id]["msg"] = message_serialization
                    Repeater.group_repeat[group.id]["count"] = 1
        return None
