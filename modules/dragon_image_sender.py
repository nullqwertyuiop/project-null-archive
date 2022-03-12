import os
import random

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.message.parser.twilight import Twilight, UnionMatch
from graia.ariadne.model import Friend
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema

from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import Normal
from sagiri_bot.utils import HelpPage, HelpPageElement

saya = Saya.current()
channel = Channel.current()

channel.name("DragonImageSender")
channel.author("nullqwertyuiop")
channel.description("随机龙图")

twilight = Twilight(
    [
        UnionMatch("随机龙图", "来张龙图")
    ]
)


@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[twilight]
    )
)
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


class DragonImageSenderHelp(HelpPage):
    __description__ = "随机龙图"
    __trigger__ = "\"随机龙图\"或者\"来张龙图\""
    __category__ = "entertainment"
    __switch__ = None
    __icon__ = "emoticon-devil"

    def __init__(self, group: Group = None, member: Member = None, friend: Friend = None):
        super().__init__()
        self.__help__ = None
        self.group = group
        self.member = member
        self.friend = friend

    async def compose(self):
        self.__help__ = [
            HelpPageElement(icon=self.__icon__, text="随机龙图", is_title=True),
            HelpPageElement(text="从图库随机抽取一张龙图"),
            HelpPageElement(icon="check-all", text="已全局开启"),
            HelpPageElement(icon="lightbulb-on", text="使用示例：\n直接发送\"随机龙图\"或者\"来张龙图\"即可"),
            HelpPageElement(icon="alert", text="本功能所指代的\"龙\"均仅指龙玉涛小姐")
        ]
        super().__init__(self.__help__)
        return await super().compose()
