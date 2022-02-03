import random
from datetime import datetime

from graia.ariadne.model import Friend
from graia.saya import Saya, Channel
from graia.ariadne.app import Ariadne
from graia.ariadne.message.element import Plain
from graia.ariadne.message.chain import MessageChain
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.ariadne.event.message import Group, Member, GroupMessage, FriendMessage

from sagiri_bot.decorators import switch, blacklist
from statics.furry_character_dict import furry_character_dict
from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.strategy import QuoteSource
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender

saya = Saya.current()
channel = Channel.current()

channel.name("RandomFursona")
channel.author("nullqwertyuiop")
channel.description("随机生成兽设插件，在群中发送 `随机兽设` 即可")


@channel.use(ListenerSchema(listening_events=[FriendMessage]))
async def random_character(app: Ariadne, message: MessageChain, friend: Friend):
    if result := await RandomFursona.handle(app, message, friend=friend):
        await MessageSender(result.strategy).send(app, result.message, message, friend, friend)


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def random_character(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await RandomFursona.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class RandomFursona(AbstractHandler):
    __name__ = "RandomFursona"
    __description__ = "随机生成兽设插件"
    __usage__ = "在群中发送 `随机兽设` 即可"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if message.asDisplay() == "随机兽设":
            return MessageItem(MessageChain.create([Plain(text=RandomFursona.get_rand(
                group=group, member=member, friend=friend
            ))]), QuoteSource())

    @staticmethod
    def get_rand(group: Group, member: Member, friend: Friend) -> str:
        random.seed(int(datetime.today().strftime('%Y%m%d')
                        + str(member.id if member else friend.id)
                        + str(group.id if group else 0)))
        items = []
        iris_color = False
        for k in furry_character_dict.keys():
            content = ''
            if isinstance(furry_character_dict[k], list):
                content = random.choice(furry_character_dict[k])
            elif isinstance(furry_character_dict[k], dict):
                sub_keys = furry_character_dict[k].keys()
                if all(isinstance(x, str) for x in sub_keys):
                    for sub_key in sub_keys:
                        content = random.choice(furry_character_dict[k][sub_key])
                        items.append(f"    {k}：{content}")
                    continue
                else:
                    values = list(furry_character_dict[k].keys())
                    value = furry_character_dict[k][values[max(range(len(values)),
                                                               key=lambda i: values[i] - random.uniform(0, 1) >= 0)]]
                    if isinstance(value, str):
                        content = value
                    elif isinstance(value, list):
                        if k == "瞳色":
                            if iris_color in value:
                                value.remove(iris_color)
                        content = random.choice(value)
            if k == "巩膜":
                iris_color = content
            items.append(f"{k}：{content}")
        return "\n".join(items)
