import base64
import binascii
import re

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.ariadne.model import MemberPerm, Friend
from graia.broadcast.interrupt import Waiter, InterruptControl
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
from sqlalchemy import select

from sagiri_bot.core.app_core import AppCore
from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import QuoteSource, Normal
from sagiri_bot.orm.async_orm import orm, Setting, UserPermission
from sagiri_bot.utils import user_permission_require, get_config

saya = Saya.current()
channel = Channel.current()

channel.name("Utilities")
channel.author("nullqwertyuiop")
channel.description("实用工具")


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def utilities_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await UtilitiesHandler.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class UtilitiesHandler(AbstractHandler):
    __name__ = "Utilities"
    __description__ = "Utilities Handler"
    __usage__ = "None"
    setting_cord = {
        "复读": {
            "index": "repeat",
            "permission": {
                "owner": True,
                "admin": True,
                "bot": 2,
            }
        },
        "频率限制": {
            "index": "frequency_limit",
            "permission": {
                "owner": True,
                "admin": True,
                "bot": 2
            }
        },
        "兽人图片": {
            "index": "setu",
            "permission": {
                "owner": False,
                "admin": False,
                "bot": 3
            }
        },
        "毛装图片": {
            "index": "real",
            "permission": {
                "owner": True,
                "admin": True,
                "bot": 2
            }
        },
        "兽人壁纸": {
            "index": "bizhi",
            "permission": {
                "owner": True,
                "admin": True,
                "bot": 2
            }
        },
        "搜图": {
            "index": "img_search",
            "permission": {
                "owner": True,
                "admin": True,
                "bot": 2
            }
        },
        "搜番": {
            "index": "bangumi_search",
            "permission": {
                "owner": True,
                "admin": True,
                "bot": 2
            }
        },
        "骰子": {
            "index": "dice",
            "permission": {
                "owner": True,
                "admin": True,
                "bot": 2
            }
        },
        "反撤回": {
            "index": "anti_revoke",
            "permission": {
                "owner": True,
                "admin": True,
                "bot": 3
            }
        },
        "反闪照": {
            "index": "anti_flash_image",
            "permission": {
                "owner": True,
                "admin": True,
                "bot": 3
            }
        },
        "艾特处理": {
            "index": "speak_mode",
            "permission": {
                "owner": True,
                "admin": True,
                "bot": 2
            },
            "valid": {
                "关闭": "normal",
                "自然语言处理": "chat",
                "彩红屁": "rainbow",
                "高级口臭": "zuanHigh",
                "低级口臭": "zuanLow"
            }
        },
        "文本转语音": {
            "index": "voice",
            "permission": {
                "owner": True,
                "admin": True,
                "bot": 2
            },
            "valid": ["0", "1", "2", "3", "4", "5", "6", "7", "1001", "1002", "1003", "1050", "1051", "101001",
                      "101002", "101003", "101004", "101005", "101006", "101007", "101008", "101009", "101010",
                      "101011", "101012", "101013", "101014", "101015", "101016", "101017", "101018", "101019",
                      "101050", "101051"]
        },
        "签到": {
            "index": "sign_in",
            "permission": {
                "owner": True,
                "admin": True,
                "bot": 2
            }
        },
        "帮你百度": {
            "index": "search_helper",
            "permission": {
                "owner": True,
                "admin": True,
                "bot": 2
            }
        },
        "事件监听": {
            "index": "event_listener",
            "permission": {
                "owner": True,
                "admin": True,
                "bot": 2
            }
        }
    }

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if message.asDisplay().startswith("工具#权限"):
            if len(message.asDisplay().split("#")) == 2:
                return MessageItem(MessageChain.create([
                    Plain(text=await UtilitiesHandler.get_permission_member(member, group))
                ]), QuoteSource())
            if len(message.asDisplay().split("#")) == 3:
                _, __, member_id = message.asDisplay().split("#")
                try:
                    member_id = int(member_id)
                    return MessageItem(MessageChain.create([
                        Plain(text=await UtilitiesHandler.get_permission_id(member_id, group, app))
                    ]), QuoteSource())
                except:
                    return MessageItem(MessageChain.create([
                        Plain(text=f"Integer expected, got {member_id}")
                    ]), QuoteSource())
        elif message.asDisplay().startswith("base64#"):
            if message.asDisplay().startswith("base64#encode#") or message.asDisplay().startswith("base64#编码#"):
                _, __, encode = message.asDisplay().split("#", maxsplit=2)
                return MessageItem(MessageChain.create([
                    Plain(text=await UtilitiesHandler.base64_encode(encode))
                ]), QuoteSource())
            elif message.asDisplay().startswith("base64#decode#") or message.asDisplay().startswith("base64#解码#"):
                _, __, decode = message.asDisplay().split("#", maxsplit=2)
                return MessageItem(MessageChain.create([
                    Plain(text=await UtilitiesHandler.base64_decode(decode))
                ]), QuoteSource())
        elif message.asDisplay().startswith("更改搜图消耗#"):
            _, cost = message.asDisplay().split("#", maxsplit=1)
            if await UtilitiesHandler.permission_check(member) or await user_permission_require(group, member, 2):
                return MessageItem(MessageChain.create([
                    Plain(text=await UtilitiesHandler.set_img_search_cost(group, cost))
                ]), QuoteSource())
            else:
                return MessageItem(MessageChain.create([
                    Plain(text="权限不足。")
                ]), QuoteSource())
        elif message.asDisplay().startswith("更改十连消耗#"):
            _, cost = message.asDisplay().split("#", maxsplit=1)
            if await UtilitiesHandler.permission_check(member) or await user_permission_require(group, member, 2):
                return MessageItem(MessageChain.create([
                    Plain(text=await UtilitiesHandler.set_ten_husband_cost(group, cost))
                ]), QuoteSource())
            else:
                return MessageItem(MessageChain.create([
                    Plain(text="权限不足。")
                ]), QuoteSource())
        elif message.asDisplay().startswith("更改十连次数#"):
            _, frequency = message.asDisplay().split("#", maxsplit=1)
            if await UtilitiesHandler.permission_check(member) or await user_permission_require(group, member, 2):
                return MessageItem(MessageChain.create([
                    Plain(text=await UtilitiesHandler.set_ten_husband_frequency_limit(group, frequency))
                ]), QuoteSource())
        elif message.asDisplay().replace(" ", "").startswith("更改LAH模拟抽卡消耗#"):
            _, cost = message.asDisplay().split("#", maxsplit=1)
            if await UtilitiesHandler.permission_check(member) or await user_permission_require(group, member, 2):
                return MessageItem(MessageChain.create([
                    Plain(text=await UtilitiesHandler.set_lah_simulation_cost(group, cost))
                ]), QuoteSource())
            else:
                return MessageItem(MessageChain.create([
                    Plain(text="权限不足。")
                ]), QuoteSource())
        elif message.asDisplay().replace(" ", "").startswith("更改LAH模拟抽卡次数#"):
            _, frequency = message.asDisplay().split("#", maxsplit=1)
            if await UtilitiesHandler.permission_check(member) or await user_permission_require(group, member, 2):
                return MessageItem(MessageChain.create([
                    Plain(text=await UtilitiesHandler.set_lah_simulation_frequency_limit(group, frequency))
                ]), QuoteSource())
            else:
                return MessageItem(MessageChain.create([
                    Plain(text="权限不足。")
                ]), QuoteSource())
        elif message.asDisplay().replace(" ", "").startswith("更改闲聊自信阈值#"):
            _, confidence = message.asDisplay().split("#", maxsplit=1)
            if await UtilitiesHandler.permission_check(member) or await user_permission_require(group, member, 2):
                return MessageItem(MessageChain.create([
                    Plain(text=await UtilitiesHandler.set_chat_confidence(group, confidence))
                ]), QuoteSource())
            else:
                return MessageItem(MessageChain.create([
                    Plain(text="权限不足。")
                ]), QuoteSource())
        elif message.asDisplay().replace(" ", "").startswith("更改搜图相似度阈值#"):
            _, similarity = message.asDisplay().split("#", maxsplit=1)
            if await UtilitiesHandler.permission_check(member) or await user_permission_require(group, member, 2):
                return MessageItem(MessageChain.create([
                    Plain(text=await UtilitiesHandler.set_img_search_similarity(group, similarity))
                ]), QuoteSource())
            else:
                return MessageItem(MessageChain.create([
                    Plain(text="权限不足。")
                ]), QuoteSource())
        elif message.asDisplay().replace(" ", "").startswith("更改塔罗牌抽取次数#"):
            _, frequency = message.asDisplay().split("#", maxsplit=1)
            if await UtilitiesHandler.permission_check(member) or await user_permission_require(group, member, 2):
                return MessageItem(MessageChain.create([
                    Plain(text=await UtilitiesHandler.set_tarot_limit(group, frequency))
                ]), QuoteSource())
            else:
                return MessageItem(MessageChain.create([
                    Plain(text="权限不足。")
                ]), QuoteSource())
        elif re.match("(不许|不可以|可以)帮忙百度", message.asDisplay()):
            reg = re.compile("(不许|不可以|可以)帮忙百度")
            match = reg.search(message.asDisplay()).group(1)
            value = True if match == "可以" else False
            if await UtilitiesHandler.permission_check(member) or await user_permission_require(group, member, 2):
                return MessageItem(MessageChain.create([
                    Plain(text=await UtilitiesHandler.set_search_helper(group, value))
                ]), QuoteSource())
            else:
                return MessageItem(MessageChain.create([
                    Plain(text="权限不足。")
                ]), QuoteSource())
        elif re.match("更改嗓音#(.*)", message.asDisplay()):
            reg = re.compile("更改嗓音#(.*)")
            voice = reg.search(message.asDisplay()).group(1)
            if await UtilitiesHandler.permission_check(member) or await user_permission_require(group, member, 2):
                return MessageItem(MessageChain.create([
                    Plain(text=await UtilitiesHandler.set_voice(group, voice))
                ]), QuoteSource())
            else:
                return MessageItem(MessageChain.create([
                    Plain(text="权限不足。")
                ]), QuoteSource())
        elif re.match("打开(.*)开关", message.asDisplay()):
            reg = re.compile("打开(.*)开关")
            setting = reg.search(message.asDisplay()).group(1)
            if setting in UtilitiesHandler.setting_cord.keys():
                item = UtilitiesHandler.setting_cord[setting]
                if "valid" in item.keys():
                    return MessageItem(MessageChain.create([
                        Plain(text=f"该设置项非布尔值。")
                    ]), QuoteSource())
                index = item["index"]
                permission = item["permission"]
                if (member.permission == MemberPerm.Administrator and permission["admin"]) or (
                        member.permission == MemberPerm.Owner and permission["owner"]) or (
                        await user_permission_require(group, member, permission["bot"])
                ):
                    await orm.insert_or_update(
                        Setting,
                        [Setting.group_id == group.id],
                        {"group_id": group.id,
                         index: True}
                    )
                    return MessageItem(MessageChain.create([Plain(text=f"已打开{setting}。")]),
                                       QuoteSource())
                else:
                    return MessageItem(MessageChain.create([Plain(text=f"权限不足。")]), QuoteSource())
        elif re.match("关闭(.*)开关", message.asDisplay()):
            reg = re.compile("关闭(.*)开关")
            setting = reg.search(message.asDisplay()).group(1)
            if setting in UtilitiesHandler.setting_cord.keys():
                item = UtilitiesHandler.setting_cord[setting]
                if "valid" in item.keys():
                    return MessageItem(MessageChain.create([
                        Plain(text=f"该设置项非布尔值。")
                    ]), QuoteSource())
                index = item["index"]
                permission = item["permission"]
                if (member.permission == MemberPerm.Administrator and permission["admin"]) or (
                        member.permission == MemberPerm.Owner and permission["owner"]) or (
                        await user_permission_require(group, member, permission["bot"])
                ):
                    await orm.insert_or_update(
                        Setting,
                        [Setting.group_id == group.id],
                        {"group_id": group.id,
                         index: False}
                    )
                    return MessageItem(MessageChain.create([Plain(text=f"已关闭{setting}。")]),
                                       QuoteSource())
                else:
                    return MessageItem(MessageChain.create([Plain(text=f"权限不足。")]), QuoteSource())
        elif message.asDisplay() == "/quit":
            if not (await user_permission_require(group, member, 3) or member.permission != MemberPerm.Member):
                return MessageItem(MessageChain.create([Plain(text=f"权限不足，需要管理员或 3 级以上权限。")]), QuoteSource())
            inc = InterruptControl(AppCore.get_core_instance().get_bcc())
            await app.sendGroupMessage(
                group.id, MessageChain.create([
                    Plain(text=f"请确认您的请求。\n（是/否）")]))

            @Waiter.create_using_function([GroupMessage])
            def quit_waiter(waiter_group: Group, waiter_member: Member, waiter_message: MessageChain):
                if all([
                    waiter_group.id == group.id,
                    waiter_member.id == member.id,
                    waiter_message.asDisplay() == "是"
                ]):
                    return 0
                elif all([
                    waiter_group.id == group.id,
                    waiter_member.id == member.id,
                    waiter_message.asDisplay() == "否"
                ]):
                    return 1
                elif all([
                    waiter_group.id == group.id,
                    waiter_member.id == member.id,
                    waiter_message.asDisplay() not in ("是", "否")
                ]):
                    return 2
            status_code = await inc.wait(quit_waiter)
            if status_code == 0:
                await app.sendGroupMessage(
                    group.id, MessageChain.create([
                        Plain(text=f"感谢您的使用！")]))
                await app.quitGroup(group)
                await app.sendFriendMessage(
                    get_config("HostQQ"), MessageChain.create([
                        Plain(text=f"机器人退出群聊 <{group.name}>。")
                    ])
                )
                return None
            elif status_code == 1:
                return MessageItem(MessageChain.create([Plain(text=f"已撤销请求。")]), Normal())
            elif status_code == 2:
                return MessageItem(MessageChain.create([Plain(text=f"非预期回复。")]), Normal())
        elif re.match("不?信任本群", message.asDisplay()):
            if await user_permission_require(group, member, 4):
                trust = False if message.asDisplay().startswith("不") else True
                await orm.insert_or_update(
                    Setting,
                    [Setting.group_id == group.id],
                    {"group_id": group.id,
                     "trusted": trust})
                return MessageItem(MessageChain.create([
                    Plain(text=f"已{'信任' if trust else '不信任'}本群")
                ]), QuoteSource())
            else:
                return MessageItem(MessageChain.create([
                    Plain(text="权限不足。")
                ]), QuoteSource())
        else:
            return None

    @staticmethod
    async def get_permission_member(member: Member, group: Group):
        fetch = await orm.fetchall(
            select(
                UserPermission.level
            ).where(UserPermission.group_id == group.id, UserPermission.member_id == member.id)
        )
        if not fetch:
            bot_permission = "1 (undefined)"
        else:
            bot_permission = str(fetch[0][0])
        group_permission = str(member.permission)
        return f"工具（权限服务）\n" \
               f"----------\n" \
               f"用户 {member.name}({member.id}) 在群 {group.name}({group.id}) 中的权限 \n" \
               f"群组权限: {group_permission}\n" \
               f"机器权限: {bot_permission}"

    @staticmethod
    async def get_permission_id(member_id: int, group: Group, app: Ariadne):
        fetch = await orm.fetchall(
            select(
                UserPermission.level
            ).where(UserPermission.group_id == group.id, UserPermission.member_id == member_id)
        )
        if not fetch:
            bot_permission = "1 (未定义)"
        else:
            bot_permission = str(fetch[0][0])
        if member := await app.getMember(group, member_id):
            group_permission = str(member.permission)
            return f"工具（权限服务）\n" \
                   f"----------\n" \
                   f"用户 {member.name}({member.id}) 在群 {group.name}({group.id}) 中的权限 \n" \
                   f"群组权限: {group_permission}\n" \
                   f"机器权限: {bot_permission}\n"
        else:
            return f"工具（权限服务）\n" \
                   f"----------\n" \
                   f"用户 {member.name}({member.id}) 的权限 \n" \
                   f"机器权限: {bot_permission}\n"

    @staticmethod
    async def base64_encode(encode: str):
        return base64.b64encode(encode.encode("utf-8")).decode("utf-8")

    @staticmethod
    async def base64_decode(decode: str):
        try:
            decoded = base64.b64decode(decode).decode("utf-8")
            if isinstance(decoded, str):
                return decoded
            return "暂不支持该格式。"
        except binascii.Error:
            return "非标准 Base64 字符串。"

    @staticmethod
    async def permission_check(member: Member):
        if member.permission == MemberPerm.Member:
            return False
        else:
            return True

    @staticmethod
    async def set_img_search_cost(group: Group, amount: int):
        try:
            amount = int(amount)
        except:
            return "仅支持设置整数值。"
        if amount <= 0:
            return f"设置值 {amount} 低于或等于最低值 0，中止本次操作。"
        try:
            await orm.insert_or_update(
                Setting,
                [Setting.group_id == group.id],
                {"group_id": group.id,
                 "img_search_cost": amount})
            if amount > 2000:
                return f"成功设置搜索消耗为 {amount} 硬币。\n我并不会阻止你本次操作，但是请再三考虑是否设置了合理的数值。"
            else:
                return f"成功设置搜索消耗为 {amount} 硬币。"
        except:
            return "设置出错，请联系机器人管理员。"

    @staticmethod
    async def set_ten_husband_cost(group: Group, amount: int):
        try:
            amount = int(amount)
        except:
            return "仅支持设置整数值。"
        if amount <= 0:
            return f"设置值 {amount} 低于或等于最低值 0，中止本次操作。"
        try:
            await orm.insert_or_update(
                Setting,
                [Setting.group_id == group.id],
                {"group_id": group.id,
                 "ten_husband_cost": amount})
            if amount < 250 or amount > 2500:
                return f"成功设置十连消耗为 {amount} 硬币。\n我并不会阻止你本次操作，但是请再三考虑是否设置了合理的数值。"
            else:
                return f"成功设置十连消耗为 {amount} 硬币。"
        except:
            return "设置出错，请联系机器人管理员。"

    @staticmethod
    async def set_ten_husband_frequency_limit(group: Group, frequency: int):
        try:
            frequency = int(frequency)
        except:
            return "仅支持设置整数值。"
        if frequency < -1:
            return f"设置值 {frequency} 低于或等于最低值 -1，中止本次操作。"
        try:
            await orm.insert_or_update(
                Setting,
                [Setting.group_id == group.id],
                {"group_id": group.id,
                 "ten_husband_limit": frequency})
            return f"成功设置十连次数限制为 {frequency} 次。"
        except:
            return "设置出错，请联系机器人管理员。"

    @staticmethod
    async def set_lah_simulation_cost(group: Group, amount: int):
        try:
            amount = int(amount)
        except:
            return "仅支持设置整数值。"
        if amount <= 0:
            return f"设置值 {amount} 低于或等于最低值 0，中止本次操作。"
        try:
            await orm.insert_or_update(
                Setting,
                [Setting.group_id == group.id],
                {"group_id": group.id,
                 "lah_simulation_cost": amount})
            if amount < 500 or amount > 5000:
                return f"成功设置 LAH 模拟抽卡消耗为 {amount} 硬币。\n我并不会阻止你本次操作，但是请再三考虑是否设置了合理的数值。"
            else:
                return f"成功设置 LAH 模拟抽卡消耗为 {amount} 硬币。"
        except:
            return "设置出错，请联系机器人管理员。"

    @staticmethod
    async def set_lah_simulation_frequency_limit(group: Group, frequency: int):
        try:
            frequency = int(frequency)
        except:
            return "仅支持设置整数值。"
        if frequency < -1:
            return f"设置值 {frequency} 低于或等于最低值 -1，中止本次操作。"
        try:
            await orm.insert_or_update(
                Setting,
                [Setting.group_id == group.id],
                {"group_id": group.id,
                 "lah_simulation_limit": frequency})
            return f"成功设置 LAH 模拟抽卡次数限制为 {frequency} 次。"
        except:
            return "设置出错，请联系机器人管理员。"

    @staticmethod
    async def set_chat_confidence(group: Group, confidence: str):
        try:
            confidence = round(float(confidence), 6)
        except:
            return "仅支持设置整数值、浮点数值。"
        if confidence < 0:
            return f"设置值 {confidence} 低于最低值 0，中止本次操作"
        elif confidence >= 1:
            return f"设置值 {confidence} 高于或等于最高值 1，中止本次操作"
        try:
            await orm.insert_or_update(
                Setting,
                [Setting.group_id == group.id],
                {"group_id": group.id,
                 "chat_confidence": confidence})
            return f"成功设置自然语言处理闲聊接口自信阈值为 {confidence}。"
        except:
            return "设置出错，请联系机器人管理员。"

    @staticmethod
    async def set_img_search_similarity(group: Group, similarity: str):
        try:
            similarity = round(float(similarity), 2)
        except:
            return "仅支持设置整数值、浮点数值。"
        if similarity < 0:
            return f"设置值 {similarity} 低于最低值 0，中止本次操作"
        elif similarity >= 100:
            return f"设置值 {similarity} 高于或等于最高值 100，中止本次操作"
        try:
            await orm.insert_or_update(
                Setting,
                [Setting.group_id == group.id],
                {"group_id": group.id,
                 "img_search_similarity": similarity})
            if similarity > 95:
                return f"成功设置搜图相似度阈值为 {similarity}。\n我并不会阻止你本次操作，但是请再三考虑是否设置了合理的数值。"
            else:
                return f"成功设置搜图相似度阈值为 {similarity}。"
        except:
            return "设置出错，请联系机器人管理员。"

    @staticmethod
    async def set_tarot_limit(group: Group, limit: str):
        try:
            limit = int(limit)
        except:
            return "仅支持设置整数值。"
        if limit < -1:
            return f"设置值 {limit} 低于最低值 -1，中止本次操作"
        try:
            await orm.insert_or_update(
                Setting,
                [Setting.group_id == group.id],
                {"group_id": group.id,
                 "tarot": limit})
            return f"成功设置塔罗牌次数限制为 {limit} 次。"
        except:
            return "设置出错，请联系机器人管理员。"

    @staticmethod
    async def set_search_helper(group: Group, value: bool):
        try:
            await orm.insert_or_update(
                Setting,
                [Setting.group_id == group.id],
                {"group_id": group.id,
                 "search_helper": value})
            return "可以帮忙百度。" if value else "不可以帮忙百度。"
        except:
            return "设置出错，请联系机器人管理员。"

    @staticmethod
    async def set_voice(group: Group, voice: str):
        available_voice = ["0", "1", "2", "3", "4", "5", "6", "7", "1001", "1002", "1003", "1050", "1051", "101001",
                           "101002", "101003", "101004", "101005", "101006", "101007", "101008", "101009", "101010",
                           "101011", "101012", "101013", "101014", "101015", "101016", "101017", "101018", "101019",
                           "101050", "101051"]
        if voice not in available_voice:
            return f'不支持的嗓音，请发送 "嗓音列表" 查看可用嗓音。'
        try:
            voice = int(voice)
            await orm.insert_or_update(
                Setting,
                [Setting.group_id == group.id],
                {"group_id": group.id,
                 "voice": voice})
            return f"已设置嗓音为 {voice}"
        except:
            return "设置出错，请联系机器人管理员。"
