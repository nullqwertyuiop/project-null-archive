from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.ariadne.model import Friend
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
from sqlalchemy import select

from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import QuoteSource
from sagiri_bot.orm.async_orm import orm, Setting, BlackList, PermanentBlackList

saya = Saya.current()
channel = Channel.current()

channel.name("SettingsCheck")
channel.author("nullqwertyuiop")
channel.description("设置检查")


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def settings_check_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await SettingsCheckHandler.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class SettingsCheckHandler(AbstractHandler):
    __name__ = "Notice"
    __description__ = "公告 Handler"
    __usage__ = "None"
    status_cord = {
        "speak_mode": {
            "normal": "不回应",
            "zuanLow": "低级口臭",
            "zuanHigh": "高级口臭",
            "rainbow": "彩虹屁",
            "chat": "自然语言处理"
        },
        "r18_process": {
            "noProcess": "不作处理",
            "revoke": "撤回",
            "flashImage": "闪照"
        }
    }

    @staticmethod
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if message.asDisplay().startswith("本群授权状态"):
            check = await orm.fetchall(
                select(
                    Setting.switch,
                    Setting.trusted,
                    Setting.frequency_limit,
                    Setting.speak_mode,
                    Setting.notice,
                    Setting.setu,
                    Setting.r18,
                    Setting.r18_process,
                    Setting.img_search,
                    Setting.sign_in,
                    Setting.prostitute,
                    Setting.anti_revoke,
                    Setting.anti_flash_image,
                    Setting.voice,
                    Setting.repeat,
                    Setting.dice,
                    Setting.search_helper
                ).where(Setting.group_id == group.id)
            )
            if not check:
                return MessageItem(MessageChain.create([Plain(text=f"无本群数据。")]), QuoteSource())
            if await orm.fetchall(
                    select(
                        PermanentBlackList.id
                    ).where(PermanentBlackList.id == group.id, PermanentBlackList.type == "group")
            ):
                return MessageItem(MessageChain.create([Plain(text="本群已在黑名单中。")]), QuoteSource())
            resp = [Plain(text=f"[本群功能授权状态]"),
                    Plain(text=f"\n总开关：　　　{'开启' if check[0][0] else '关闭'}"),
                    Plain(text=f"\n├白名单：　　{'是' if check[0][1] else '否'}"),
                    Plain(text=f"\n├频率限制：　{'开启' if check[0][2] else '关闭'}"),
                    Plain(text=f"\n├艾特处理：　{SettingsCheckHandler.status_cord['speak_mode'][check[0][3]]}"),
                    Plain(text=f"\n├公告：　　　{'开启' if check[0][4] else '关闭'}"),
                    Plain(text=f"\n├兽人图片：　{'开启' if check[0][5] else '关闭'}")]
            if check[0][5]:
                if check[0][6]:
                    resp.append(Plain(text=f"\n│├扩充图库：开启"))
                    resp.append(Plain(text=f"\n│└图片处理：{SettingsCheckHandler.status_cord['r18_process'][check[0][7]]}"))
                else:
                    resp.append(Plain(text=f"\n│└扩充图库：关闭"))
            resp.append(Plain(text=f"\n├搜图：　　　{'开启' if check[0][8] else '关闭'}"))
            if check[0][8]:
                resp.append(Plain(text=f"\n│└缩略图：　{'开启' if check[0][1] else '关闭'}"))
            resp.append(Plain(text=f"\n├签到：　　　{'开启' if check[0][9] else '关闭'}"))
            if check[0][10]:
                resp.append(Plain(text=f"\n├站街：　　　开启"))
            resp.append(Plain(text=f"\n├反撤回：　　{'开启' if check[0][11] else '关闭'}"))
            resp.append(Plain(text=f"\n├反闪照：　　{'开启' if check[0][12] else '关闭'}"))
            resp.append(Plain(text=f"\n├文本转语音：{'开启' if check[0][13] != 'off' else '关闭'}"))
            resp.append(Plain(text=f"\n├复读：　　　{'开启' if check[0][14] else '关闭'}"))
            if check[0][14]:
                resp.append(Plain(text=f"\n│└复读图片：{'开启' if check[0][1] else '关闭'}"))
            resp.append(Plain(text=f"\n├骰子：　　　{'开启' if check[0][15] else '关闭'}"))
            resp.append(Plain(text=f"\n└帮你百度：　{'开启' if check[0][16] else '关闭'}"))
            if values := await orm.fetchall(
                    select(
                        Setting.chat_confidence,
                        Setting.img_search_cost,
                        Setting.img_search_similarity,
                        Setting.ten_husband_cost,
                        Setting.ten_husband_limit,
                        Setting.tarot,
                        Setting.lah_simulation_cost,
                        Setting.lah_simulation_limit
                    )
            ):
                values_resp = [Plain(text=f"\n----------"),
                               Plain(text=f"\n[本群功能具体数值]")]
                if check[0][3] == "chat":
                    values_resp.append(Plain(text=f"\n艾特处理"))
                    values_resp.append(Plain(text=f"\n└自信阈值：　{values[0][0]}"))
                if check[0][8]:
                    values_resp.append(Plain(text=f"\n搜图"))
                    values_resp.append(Plain(text=f"\n├搜图消耗：　{values[0][1]} 枚硬币"))
                    values_resp.append(Plain(text=f"\n└相似度阈值：{values[0][2]}%"))
                if check[0][13] != "off":
                    values_resp.append(Plain(text=f"\n文本转语音"))
                    values_resp.append(Plain(text=f"\n└使用嗓音：　{check[0][13]}"))
                if check[0][4] != "0":
                    values_resp.append(Plain(text=f"\n十连老公"))
                    values_resp.append(Plain(text=f"\n├十连消耗：　{values[0][3]} β币"))
                    values_resp.append(Plain(text=f"\n└次数限制：　{'无' if values[0][4] == -1 else str(values[0][4]) + '次'}"))
                if check[0][5] != "0":
                    values_resp.append(Plain(text=f"\n塔罗牌"))
                    values_resp.append(Plain(text=f"\n└次数限制：　{'无' if values[0][5] == -1 else str(values[0][5]) + '次'}"))
                if check[0][7] != "0":
                    values_resp.append(Plain(text=f"\nLAH 模拟抽卡"))
                    values_resp.append(Plain(text=f"\n├模拟消耗：　{values[0][6]} β币"))
                    values_resp.append(Plain(text=f"\n└次数限制：　{'无' if values[0][7] == -1 else str(values[0][7]) + '次'}"))
                if len(values_resp) != 2:
                    resp.extend(values_resp)
            if black_check := await orm.fetchall(
                    select(
                        BlackList.member_id
                    ).where(BlackList.group_id == group.id)
            ):
                resp.extend([
                    Plain(text=f"\n----------"),
                    Plain(text=f"\n本群黑名单用户")
                ])
                count = 1
                for member_id in black_check[0]:
                    if member := await app.getMember(group, member_id):
                        resp.append(Plain(text=f"{count}. {member.name}"))
                    else:
                        resp.append(Plain(text=f"{count}. {member_id}"))
                    count += 1
            return MessageItem(MessageChain.create(resp), QuoteSource())
