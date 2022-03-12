import json
import os
import random

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage, FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.ariadne.message.parser.twilight import Twilight, FullMatch, SpacePolicy, WildcardMatch, MatchResult
from graia.ariadne.model import Friend
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema

from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import QuoteSource
from sagiri_bot.utils import update_user_call_count_plus, UserCalledCount

saya = Saya.current()
channel = Channel.current()

channel.name("CPGenerator")
channel.author("SAGIRI-kawaii")
channel.description("生成CP文的插件，在群中发送 `/cp {攻名字} {受名字}`")

with open(f"{os.getcwd()}/statics/cp_data.json", "r", encoding="utf-8") as r:
    cp_data = json.loads(r.read())


@channel.use(
    ListenerSchema(
        listening_events=[FriendMessage],
        inline_dispatchers=[
            Twilight(
                [
                    FullMatch("/cp").space(SpacePolicy.FORCE),
                    "attack" @ WildcardMatch(greed=False).space(SpacePolicy.FORCE),
                    "defence" @ WildcardMatch(greed=False)
                ]
            )
        ]
    )
)
async def cp_generator(
        app: Ariadne,
        message: MessageChain,
        attack: MatchResult,
        defence: MatchResult,
        friend: Friend
):
    if result := await CPGenerator.handle(app, message, attack.result, defence.result, friend=friend):
        await MessageSender(result.strategy).send(app, result.message, message, friend, friend)


@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[
            Twilight(
                [
                    FullMatch("/cp").space(SpacePolicy.FORCE),
                    "attack" @ WildcardMatch(greed=False).space(SpacePolicy.FORCE),
                    "defence" @ WildcardMatch(greed=False)
                ]
            )
        ]
    )
)
async def cp_generator(
        app: Ariadne,
        message: MessageChain,
        attack: MatchResult,
        defence: MatchResult,
        group: Group,
        member: Member
):
    if result := await CPGenerator.handle(app, message, attack.result, defence.result, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class CPGenerator(AbstractHandler):
    __name__ = "CPGenerator"
    __description__ = "生成CP文的插件"
    __usage__ = "/cp {攻名字} {受名字}"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(
            app: Ariadne,
            message: MessageChain,
            attack: MessageChain,
            defence: MessageChain,
            group: Group = None,
            member: Member = None,
            friend: Friend = None
    ):
        if member and group:
            await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
        return await CPGenerator.generate_article(attack.asDisplay(), defence.asDisplay())

    @staticmethod
    async def generate_article(attack: str, defence: str) -> MessageItem:
        template = random.choice(cp_data["data"])
        content = template.replace("<攻>", attack).replace("<受>", defence)
        return MessageItem(
            MessageChain.create([
                Plain(text=content)
            ]),
            QuoteSource()
        )
