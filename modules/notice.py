import re

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage
from graia.ariadne.model import MemberPerm
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema

from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import QuoteSource
from sagiri_bot.orm.async_orm import orm, Setting
from sagiri_bot.utils import get_setting, user_permission_require

saya = Saya.current()
channel = Channel.current()


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def speak_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await NoticeHandler.handle(app, message, group, member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class NoticeHandler(AbstractHandler):
    __name__ = "NoticeHandler"
    __description__ = "公告 Handler"
    __usage__ = "None"

    @staticmethod
    async def handle(app: Ariadne, message: MessageChain, group: Group, member: Member):
        if message.asDisplay().startswith("发送公告#"):
            if re.match("发送公告#(.*)", message.asDisplay()):
                if await user_permission_require(group, member, 4):
                    return await NoticeHandler.notice(app, message)
                else:
                    return MessageItem(MessageChain.create([
                        Plain(text="权限不足，需要 4 级权限才能发送公告。")]), QuoteSource())
        elif message.asDisplay() == "#关闭公告":
            return MessageItem(MessageChain.create([
                Plain(text=await NoticeHandler.disable(member, group))]), QuoteSource())
        elif message.asDisplay() == "#开启公告":
            return MessageItem(MessageChain.create([
                Plain(text=await NoticeHandler.enable(member, group))]), QuoteSource())

    @staticmethod
    async def notice(app: Ariadne, message: MessageChain):
        message_serialization = message.asPersistentString().replace(
            "发送公告#", "", 1
        )
        group_list = await app.getGroupList()
        for group in group_list:
            if await get_setting(group.id, Setting.notice):
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

