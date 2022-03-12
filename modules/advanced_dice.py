import random

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage, FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.ariadne.message.parser.twilight import Twilight, FullMatch, RegexMatch, MatchResult
from graia.ariadne.model import Friend
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema

from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import QuoteSource
from sagiri_bot.orm.async_orm import Setting
from sagiri_bot.utils import group_setting, HelpPage, HelpPageElement

saya = Saya.current()
channel = Channel.current()

channel.name("AdvancedDice")
channel.author("nullqwertyuiop")
channel.description("高级(不)的骰子")

twilight = Twilight(
    [
        FullMatch(".ra"),
        FullMatch(" ", optional=True),
        "content" @ RegexMatch(r"\D+"),
        "num" @ RegexMatch(r"\d+")
    ]
)


@channel.use(
    ListenerSchema(
        listening_events=[FriendMessage],
        inline_dispatchers=[twilight]
    )
)
async def advanced_dice_handler(
        app: Ariadne,
        message: MessageChain,
        content: MatchResult,
        num: MatchResult,
        friend: Friend):
    if result := await AdvancedDice.handle(app, content, num, friend=friend):
        await MessageSender(result.strategy).send(app, result.message, message, friend, friend)


@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[twilight]
    )
)
async def advanced_dice_handler(
        app: Ariadne,
        message: MessageChain,
        content: MatchResult,
        num: MatchResult,
        group: Group,
        member: Member):
    if result := await AdvancedDice.handle(app, content, num, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class AdvancedDice(AbstractHandler):
    __name__ = "AdvancedDice"
    __description__ = "投骰子"
    __usage__ = "None"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(
            app: Ariadne,
            content: MatchResult,
            num: MatchResult,
            group: Group = None,
            member: Member = None,
            friend: Friend = None
    ):
        if member and group:
            if not await group_setting.get_setting(group.id, Setting.dice):
                return MessageItem(MessageChain.create([Plain(text="骰子功能尚未开启。")]), QuoteSource())
        else:
            return MessageItem(
                MessageChain.create(
                    [
                        Plain(text=f"[]进行的 "),
                        Plain(text=AdvancedDice.ra(
                            content.result.asDisplay(),
                            int(num.result.asDisplay())
                        ))
                    ]
                ), QuoteSource())

    @staticmethod
    def ra(text: str, dice: int):
        max_point = 100
        # max = await orm.fetchall()
        if dice > max_point:
            return f"错误：点数 {dice} 大于 {max_point}。"
        elif dice <= 0:
            return f"错误：点数不得等于 0。"
        point = int(random.choice([num for num in range(1, max_point + 1)]))
        if point == dice:
            return f"{text} 检定：D{max_point}={point}/{dice}【刚好成功】"
        elif 0 < point <= 5:
            if point < dice:
                return f"{text} 检定：D{max_point}={point}/{dice}【大成功】"
            else:
                return f"{text} 检定：D{max_point}={point}/{dice}【失败】"
        elif 5 < point < dice:
            return f"{text} 检定：D{max_point}={point}/{dice}【成功】"
        elif dice < point < (max_point - 5):
            return f"{text} 检定：D{max_point}={point}/{dice}【失败】"
        elif (max_point - 5) <= point <= max_point:
            return f"{text} 检定：D{max_point}={point}/{dice}【大失败】"
        else:
            return f"{text} 检定[Bug]：D{max_point}={point}/{dice}【请联系机器人管理员】"


class AdvancedDiceHelp(HelpPage):
    __description__ = "简易骰子"
    __trigger__ = ".ra检定65"
    __category__ = "utility"
    __switch__ = Setting.dice
    __icon__ = "dice-6"

    def __init__(self, group: Group = None, member: Member = None, friend: Friend = None):
        super().__init__()
        self.__help__ = None
        self.group = group
        self.member = member
        self.friend = friend

    async def compose(self):
        if self.group or self.member:
            if not await group_setting.get_setting(self.group.id, self.__switch__):
                status = HelpPageElement(icon="toggle-switch-off", text="已关闭")
            else:
                status = HelpPageElement(icon="toggle-switch", text="已开启")
        else:
            status = HelpPageElement(icon="check-all", text="已全局开启")
        self.__help__ = [
            HelpPageElement(icon=self.__icon__, text="简易骰子", is_title=True),
            HelpPageElement(text="投掷一面可自定义面数的骰子（最高支持 100 面）"),
            status,
            HelpPageElement(icon="pound-box", text="更改设置需要权限不记得多少级"),
            HelpPageElement(icon="lightbulb-on", text="使用示例：\n.ra检定65")
        ]
        super().__init__(self.__help__)
        return await super().compose()
