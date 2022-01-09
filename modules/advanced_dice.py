import re
import random

from graia.saya import Saya, Channel
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.ariadne.event.message import Group, Member, GroupMessage

from SAGIRIBOT.utils import get_setting
from SAGIRIBOT.ORM.AsyncORM import Setting
from SAGIRIBOT.decorators import switch, blacklist
from SAGIRIBOT.Handler.Handler import AbstractHandler
from SAGIRIBOT.MessageSender.MessageItem import MessageItem
from SAGIRIBOT.MessageSender.MessageSender import GroupMessageSender
from SAGIRIBOT.MessageSender.Strategy import GroupStrategy, QuoteSource

saya = Saya.current()
channel = Channel.current()


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def dice_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await AdvancedDiceHandler.handle(app, message, group, member):
        await GroupMessageSender(result.strategy).send(app, result.message, message, group, member)


class AdvancedDiceHandler(AbstractHandler):
    __name__ = "AdvancedDiceHandler"
    __description__ = "投骰子"
    __usage__ = "None"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group, member: Member):
        if re.match(r"(\.|。)ra(\D+)(\d+)", message.asDisplay()):
            print(message.asDisplay())
            if not await get_setting(group.id, Setting.dice):
                return MessageItem(MessageChain.create([Plain(text="骰子功能尚未开启。")]), QuoteSource(GroupStrategy()))
            else:
                return MessageItem(MessageChain.create([
                    Plain(text=f"[{member.name}]进行的 "),
                    Plain(text=await AdvancedDiceHandler.ra(group, message.asDisplay()))
                ]), QuoteSource(GroupStrategy()))

    @staticmethod
    async def ra(group: Group, message: str):
        reg = re.compile("(\.|。)ra(\D+)(\d+)")
        text = reg.search(message).group(2)
        dice = int(reg.search(message).group(3))
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
            return f"{text} 检定：D{max_point}={point}/{dice}【大成功】"
        elif 5 < point < dice:
            return f"{text} 检定：D{max_point}={point}/{dice}【成功】"
        elif dice < point < (max_point - 5):
            return f"{text} 检定：D{max_point}={point}/{dice}【失败】"
        elif (max_point - 5) <= point <= max_point:
            return f"{text} 检定：D{max_point}={point}/{dice}【大失败】"
        else:
            return f"{text} 检定[Bug]：D{max_point}={point}/{dice}【请联系机器人管理员】"
