import os
import random

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema

from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import Normal

saya = Saya.current()
channel = Channel.current()

channel.name("DragonImageSender")
channel.author("nullqwertyuiop")
channel.description("随机龙图")


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def dragon_image_sender_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await DragonImageSender.handle(app, message, group, member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class DragonImageSender(AbstractHandler):
    __name__ = "DragonImageSender"
    __description__ = "一个可以发送龙图的Handler"
    __usage__ = "随机龙图"
    dragon_images = os.listdir(f"{os.getcwd()}/statics/dragon_image/")

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group, member: Member):
        if message.asDisplay().strip() in ("随机龙图", "来张龙图"):
            return MessageItem(MessageChain.create([Image(
                path=f"{os.getcwd()}/statics/dragon_image/{random.choice(DragonImageSender.dragon_images)}"
            )]), Normal())
