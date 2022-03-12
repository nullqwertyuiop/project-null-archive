import re

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage, FriendMessage
from graia.ariadne.message.parser.twilight import Twilight, RegexMatch
from graia.ariadne.model import MemberPerm, Friend
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema

from sagiri_bot.core.app_core import AppCore
from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import QuoteSource
from sagiri_bot.orm.async_orm import orm, Setting
from sagiri_bot.utils import group_setting, user_permission_require

saya = Saya.current()
channel = Channel.current()
core: AppCore = AppCore.get_core_instance()
config = core.get_config()

channel.name("Notice")
channel.author("nullqwertyuiop")
channel.description("公告")

twilight = Twilight(
    [
        RegexMatch(r"(发送公告#(.+))|(#(关闭|开启)公告)")
    ]
)


@channel.use(
    ListenerSchema(
        listening_events=[FriendMessage],
        inline_dispatchers=[twilight]
    )
)
async def notice_handler(app: Ariadne, message: MessageChain, friend: Friend):
    if result := await Notice.handle(app, message, friend=friend):
        await MessageSender(result.strategy).send(app, result.message, message, friend, friend)


@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[twilight]
    )
)
async def notice_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await Notice.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class Notice(AbstractHandler):
    __name__ = "Notice"
    __description__ = "公告 Handler"
    __usage__ = "None"

    @staticmethod
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if message.asDisplay().startswith("发送公告#"):
            if re.match("发送公告#(.+)", message.asDisplay()):
                if member and group:
                    if await user_permission_require(group, member, 4):
                        return await Notice.notice(app, message)
                    else:
                        return MessageItem(MessageChain.create([
                            Plain(text="权限不足，需要 4 级权限才能发送公告。")]), QuoteSource())
                elif friend:
                    if friend.id == config.host_qq:
                        return await Notice.notice(app, message)
                    else:
                        return MessageItem(MessageChain.create([
                            Plain(text="权限不足。")]), QuoteSource())
        elif message.asDisplay() == "#关闭公告":
            return MessageItem(MessageChain.create([
                Plain(text=await Notice.disable(member, group))]), QuoteSource())
        elif message.asDisplay() == "#开启公告":
            return MessageItem(MessageChain.create([
                Plain(text=await Notice.enable(member, group))]), QuoteSource())

    @staticmethod
    async def notice(app: Ariadne, message: MessageChain):
        message_serialization = message.asPersistentString().replace(
            "发送公告#", "", 1
        )
        group_list = await app.getGroupList()
        for group in group_list:
            if await group_setting.get_setting(group.id, Setting.notice):
                try:
                    await app.sendGroupMessage(group, MessageChain.fromPersistentString(message_serialization))
                except:
                    continue
        return None

    @staticmethod
    async def disable(member: Member, group: Group):
        if member.permission == MemberPerm.Member and not await user_permission_require(group, member, 2):
            return "权限不足。"
        else:
            try:
                await orm.insert_or_update(
                    Setting,
                    [Setting.group_id == group.id],
                    {"group_id": group.id,
                     "notice": 0})
                return "关闭公告成功。"
            except:
                return "设置出错，请联系机器人管理员。"

    @staticmethod
    async def enable(member: Member, group: Group):
        if member.permission == MemberPerm.Member and not await user_permission_require(group, member, 2):
            return "权限不足。"
        else:
            try:
                await orm.insert_or_update(
                    Setting,
                    [Setting.group_id == group.id],
                    {"group_id": group.id,
                     "notice": 1})
                return "开启公告成功。"
            except:
                return "设置出错，请联系机器人管理员。"

