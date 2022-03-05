import random
from datetime import datetime

from graia.ariadne.model import Friend
from graia.saya import Saya, Channel
from graia.ariadne.app import Ariadne
from graia.ariadne.message.element import Plain
from graia.ariadne.message.chain import MessageChain
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.ariadne.event.message import Group, Member, GroupMessage, FriendMessage

from statics.character_dict import character_dict
from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.strategy import QuoteSource
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender

saya = Saya.current()
channel = Channel.current()

channel.name("RandomCharacter")
channel.author("SAGIRI-kawaii")
channel.description("随机生成人设插件，在群中发送 `随机人设` 即可")


@channel.use(ListenerSchema(listening_events=[FriendMessage]))
async def random_character(app: Ariadne, message: MessageChain, friend: Friend):
    if result := await RandomCharacter.handle(app, message, friend=friend):
        await MessageSender(result.strategy).send(app, result.message, message, friend, friend)


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def random_character(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await RandomCharacter.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class RandomCharacter(AbstractHandler):
    __name__ = "RandomCharacter"
    __description__ = "随机生成人设插件"
    __usage__ = "在群中发送 `随机人设` 即可"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if message.asDisplay() == "随机人设":
            return MessageItem(MessageChain.create([Plain(text=RandomCharacter.get_rand(
                group=group, member=member, friend=friend
            ))]), QuoteSource())

    @staticmethod
    def get_rand(group: Group, member: Member, friend: Friend) -> str:
        random.seed(int(datetime.today().strftime('%Y%m%d')
                        + str(member.id if member else friend.id)
                        + str(group.id if group else 0)))
        text = "\n".join([f"{k}：{random.choice(character_dict[k])}" for k in character_dict.keys()])
        random.seed()
        return text
