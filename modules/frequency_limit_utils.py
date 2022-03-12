import datetime
import re
from typing import Union

from graia.ariadne.app import Ariadne, Friend
from graia.ariadne.event.message import Group, Member, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.ariadne.message.parser.twilight import Twilight, FullMatch, SpacePolicy, UnionMatch, WildcardMatch
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema

from sagiri_bot.core.app_core import AppCore
from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import Normal
from sagiri_bot.utils import user_permission_require

saya = Saya.current()
channel = Channel.current()
core: AppCore = AppCore.get_core_instance()
config = core.get_config()

channel.name("FrequencyLimitUtils")
channel.author("nullqwertyuiop")
channel.description("频率限制实用工具 [4 级权限]\n"
                    "/frequency check [--all]\n"
                    "/frequency add [ID/@目标]+\n"
                    "/frequency remove -g=[*/ID/(ID,)+] -m=[*/ID/(ID,)+\n"
                    "/frequency purge")

twilight = Twilight(
    [
        FullMatch("/frequency").space(SpacePolicy.FORCE),
        UnionMatch("check", "add", "remove", "purge"),
        WildcardMatch()
    ]
)


@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[twilight]
    )
)
async def image_to_url_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await FrequencyLimitUtils.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class FrequencyLimitUtils(AbstractHandler):
    __name__ = "FrequencyLimitUtils"
    __description__ = "频率限制实用工具"
    __usage__ = "None"
    __initialized = False
    __instance = None
    __temp_blacklist = None

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if message.asDisplay().startswith("/frequency "):
            err = []
            if not await user_permission_require(group, member, 4):
                err = [Plain(text="权限不足，你需要 4 级权限才可使用")]
            params = message.asDisplay().split(" ")
            params.pop(0)
            if params[0] == '':
                err = [Plain(text="缺少参数")]
            warn = []
            resp = []
            if not FrequencyLimitUtils.__initialized:
                try:
                    FrequencyLimitUtils.__instance = core.get_frequency_limit_instance()
                    FrequencyLimitUtils.__temp_blacklist = FrequencyLimitUtils.__instance\
                        ._GlobalFrequencyLimitDict__temp_blacklist
                    FrequencyLimitUtils.__initialized = True
                    warn = [Plain(text="初始化成功\n")]
                except AttributeError:
                    warn = [Plain(text="无法获取频率限制实例\n")]
            if params[0] == "add":
                if len(params) == 1:
                    err = [Plain(text="缺少参数")]
                success_count = 0
                for member_id in params[1:]:
                    try:
                        member_id = member_id.replace("@", "")
                        member_id = int(member_id)
                    except ValueError:
                        err = [Plain(text=f"参数类型错误：{member_id}")]
                        break
                    FrequencyLimitUtils.__instance.add_temp_blacklist(group.id, member_id)
                    success_count += 1
                resp = [Plain(text=f"成功添加 {success_count} 名用户至临时黑名单")]
            elif params[0] == "check":
                if len(params) == 1:
                    resp = await FrequencyLimitUtils.check_blacklist(app, group)
                elif params[1] == "--all":
                    resp = await FrequencyLimitUtils.check_blacklist(app)
                else:
                    err = [Plain(text=f"意外参数：{' '.join(params[1:])}")]
            elif params[0] == "remove":
                if len(params) != 3:
                    err = [Plain(text="缺少参数")]
                if re.match("-g=(\d+,?)+", params[1]):
                    groups = params[1][3:].split(",")
                elif params[1] == "-g=*":
                    groups = None
                else:
                    groups = -1
                    err = [Plain(text="缺少参数 `-g` 或参数 `-g` 类型错误")]
                if re.match("-m=(\d+,?)+", params[2]):
                    members = params[2][3:].split(",")
                elif params[2] == "-m=*":
                    members = None
                else:
                    members = -1
                    err = [Plain(text="缺少参数 `-m` 或参数 `-m` 类型错误")]
                if not (groups or members):
                    resp = FrequencyLimitUtils.purge()
                elif not err:
                    resp = FrequencyLimitUtils.remove(members, groups)
            elif params[0] == "purge":
                resp = FrequencyLimitUtils.purge()
            if err:
                return MessageItem(MessageChain.create(err), Normal())
            if resp or warn:
                return MessageItem(MessageChain.create(warn + resp), Normal())


    @staticmethod
    async def check_blacklist(app: Ariadne, group: Union[Group, None] = None):
        if group:
            group = group.id
            resp = [Plain(text="本群临时黑名单及解除时间")]
            count = 0
            if group in FrequencyLimitUtils.__temp_blacklist.keys():
                for member in FrequencyLimitUtils.__temp_blacklist[group].keys():
                    time = FrequencyLimitUtils.__temp_blacklist[group][member]
                    if time <= datetime.datetime.now():
                        continue
                    count += 1
                    if _member := await app.getMember(group, member):
                        member = _member.name
                    resp.append(Plain(text=f"\n{member}: {time.strftime('%Y/%m/%d %H:%M:%S')}"))
            return resp if count else [Plain(text="本群临时黑名单为空")]
        else:
            resp = [Plain(text="所有临时黑名单及解除时间")]
            count = 0
            for group in FrequencyLimitUtils.__temp_blacklist.keys():
                group_name = None
                if _group := await app.getGroup(group):
                    group_name = _group.name
                resp.append(Plain(text=f"\n{group if not group_name else group_name}:"))
                group_count = 0
                for member in FrequencyLimitUtils.__temp_blacklist[group].keys():
                    time = FrequencyLimitUtils.__temp_blacklist[group][member]
                    if time <= datetime.datetime.now():
                        continue
                    group_count += 1
                    if _member := await app.getMember(group, member):
                        member = _member.name
                    resp.append(Plain(text=f"\n    {member}: {time.strftime('%Y/%m/%d %H:%M:%S')}"))
                if not group_count:
                    resp.pop()
                    continue
                count += 1
            return resp if count else [Plain(text="临时黑名单为空")]

    @staticmethod
    def remove(member: Union[list, None] = None, group: Union[list, None] = None):
        def remove_temp_blacklist(m: int, g: int):
            if g not in FrequencyLimitUtils.__temp_blacklist.keys():
                return False
            return FrequencyLimitUtils.__temp_blacklist[g].pop(m, False)
        if not group:
            group = [g_id for g_id in FrequencyLimitUtils.__temp_blacklist.keys()]
        for group_id in group:
            if not member:
                FrequencyLimitUtils.__temp_blacklist.pop(group_id, False)
                continue
            for member_id in member:
                remove_temp_blacklist(member_id, group_id)
        resp = [Plain(text="成功从临时黑名单中删除")]
        return resp

    @staticmethod
    def purge():
        FrequencyLimitUtils.__temp_blacklist = {}
        return [Plain(text="清空临时黑名单成功")]
