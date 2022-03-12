import random

from graia.ariadne.message.parser.twilight import Twilight, FullMatch
from graia.ariadne.model import Friend
from graia.saya import Saya, Channel
from graia.ariadne.app import Ariadne
from graia.ariadne.message.element import Plain
from graia.ariadne.message.chain import MessageChain
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.ariadne.event.message import Group, Member, GroupMessage, FriendMessage

from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.message_sender.strategy import Normal
from sagiri_bot.handler.handler import AbstractHandler
from statics.pero_dog_contents import pero_dog_contents
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.utils import update_user_call_count_plus, UserCalledCount

saya = Saya.current()
channel = Channel.current()

channel.name("PeroDog")
channel.author("SAGIRI-kawaii")
channel.description("一个获取舔狗日记的插件，在群中发送 `舔` 即可")

twilight = Twilight(
    [
        FullMatch("舔")
    ]
)


@channel.use(
    ListenerSchema(
        listening_events=[FriendMessage],
        inline_dispatchers=[twilight]
    )
)
async def pero_dog(app: Ariadne, message: MessageChain, friend: Friend):
    if result := await PeroDog.handle(app, message, friend=friend):
        await MessageSender(result.strategy).send(app, result.message, message, friend, friend)


@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[twilight]
    )
)
async def pero_dog(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await PeroDog.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class PeroDog(AbstractHandler):
    __name__ = "PeroDog"
    __description__ = "一个获取舔狗日记的插件"
    __usage__ = "在群中发送 `舔` 即可"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if message.asDisplay() == "舔":
            if member and group:
                await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
            return MessageItem(
                MessageChain.create([Plain(text=random.choice(pero_dog_contents).replace('*', ''))]),
                Normal()
            )
        else:
            return None
