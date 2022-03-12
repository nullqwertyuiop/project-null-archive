import random
from datetime import datetime

from graia.ariadne.message.parser.twilight import Twilight, UnionMatch
from graia.ariadne.model import Friend
from graia.saya import Saya, Channel
from graia.ariadne.app import Ariadne
from graia.ariadne.message.element import Image
from graia.ariadne.message.chain import MessageChain
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.ariadne.event.message import Group, Member, GroupMessage, FriendMessage

from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.strategy import QuoteSource
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.decorators import frequency_limit_require_weight_free

saya = Saya.current()
channel = Channel.current()

channel.name("RandomWife")
channel.author("SAGIRI-kawaii")
channel.description("生成随机老婆图片的插件，在群中发送 `[来个老婆|随机老婆]`")

twilight = Twilight(
    [
        UnionMatch("来个老婆", "随机老婆")
    ]
)


@channel.use(
    ListenerSchema(
        listening_events=[FriendMessage],
        inline_dispatchers=[twilight]
    )
)
async def random_wife(app: Ariadne, message: MessageChain, friend: Friend):
    if result := await RandomWife.handle(app, message, friend=friend):
        await MessageSender(result.strategy).send(app, result.message, message, friend, friend)


@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[twilight]
    )
)
async def random_wife(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await RandomWife.handle(app, message, group, member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class RandomWife(AbstractHandler):
    __name__ = "RandomWife"
    __description__ = "生成随机老婆图片的插件"
    __usage__ = "在群中发送 `[来个老婆|随机老婆]`"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if message.asDisplay() in ("来个老婆", "随机老婆"):
            return await RandomWife.get_random_wife(group=group, member=member, friend=friend)

    @staticmethod
    @frequency_limit_require_weight_free(4)
    async def get_random_wife(group: Group, member: Member, friend: Friend):
        random.seed(int(datetime.today().strftime('%Y%m%d')
                        + str(member.id if member else friend.id)
                        + str(group.id if group else 0)))
        index = random.randint(1, 100000)
        random.seed()
        return MessageItem(
            MessageChain.create([
                Image(url=f"https://www.thiswaifudoesnotexist.net/example-{index}.jpg")
            ]),
            QuoteSource()
        )
