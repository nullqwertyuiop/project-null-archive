from graia.ariadne.message.parser.twilight import WildcardMatch, Twilight, FullMatch, SpacePolicy
from graia.ariadne.model import Friend
from graia.saya import Saya, Channel
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain, Image
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.ariadne.event.message import Group, Member, GroupMessage, FriendMessage

from sagiri_bot.utils import MessageChainUtils
from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.strategy import QuoteSource
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.utils import update_user_call_count_plus, UserCalledCount

saya = Saya.current()
channel = Channel.current()

channel.name("MessageMerger")
channel.author("SAGIRI-kawaii")
channel.description("将收到的消息合并为图片，在群中发送 `/merge 文字/图片`")

twilight = Twilight(
    [
        FullMatch("/merge").space(SpacePolicy.FORCE),
        WildcardMatch()
    ]
)


@channel.use(
    ListenerSchema(
        listening_events=[FriendMessage],
        inline_dispatchers=[twilight]
    )
)
async def message_merger(app: Ariadne, message: MessageChain, friend: Friend):
    if result := await MessageMerger.handle(app, message, friend=friend):
        await MessageSender(result.strategy).send(app, result.message, message, friend, friend)


@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[twilight]
    )
)
async def message_merger(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await MessageMerger.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class MessageMerger(AbstractHandler):
    __name__ = "MessageMerger"
    __description__ = "将收到的消息合并为图片"
    __usage__ = "在群中发送 `/merge 文字/图片`"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if message.asDisplay().startswith("/merge "):
            if member and group:
                await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
            elements = [
                element for element in message.__root__ if (isinstance(element, Image) or isinstance(element, Plain))
            ]
            elements[0].text = elements[0].text[7:]
            return MessageItem(
                await MessageChainUtils.messagechain_to_img(MessageChain.create(elements)),
                QuoteSource()
            )
        else:
            return None
