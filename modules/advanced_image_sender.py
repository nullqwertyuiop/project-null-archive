import os
import random
import re
from datetime import datetime

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain, Image
from graia.ariadne.message.parser.twilight import Twilight, UnionMatch, WildcardMatch, SpacePolicy
from graia.ariadne.model import Friend, MemberPerm
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
from loguru import logger

from modules.twitter_preview import TwitterPreview
from sagiri_bot.core.app_core import AppCore
from sagiri_bot.decorators import frequency_limit_require_weight_free, switch, blacklist
from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import Normal, Revoke, QuoteSource
from sagiri_bot.orm.async_orm import Setting
from sagiri_bot.orm.async_orm import orm
from sagiri_bot.utils import group_setting, HelpPageElement, HelpPage, user_permission_require

saya = Saya.current()
channel = Channel.current()
core: AppCore = AppCore.get_core_instance()
config = core.get_config()

channel.name("AdvancedImageSender")
channel.author("nullqwertyuiop")
channel.description("高级(不)的色图插件")

twilight = Twilight(
    [
        UnionMatch("/setu", ".setu").space(SpacePolicy.NOSPACE),
        WildcardMatch()
    ]
)


@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[twilight]
    )
)
async def image_sender_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await AdvancedImageSenderHandler.handle(app, message, group, member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class AdvancedImageSenderHandler(AbstractHandler):
    __name__ = "AdvancedImageSenderHandler"
    __description__ = "一个可以发送图片的Handler"
    __usage__ = "在群中发送设置好的关键词即可"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group, member: Member):
        if message.asDisplay().startswith("/setu"):
            return MessageItem(MessageChain.create([
                Plain(text="本功能触发词已改为 \".setu\"，请通过新触发词使用。")
            ]), QuoteSource())
        elif message.asDisplay().startswith(".setu"):
            if len(message.asDisplay()) == 5:
                query = None
                return await AdvancedImageSenderHandler.get_image_message(group, member, query)
            elif message.asDisplay().startswith(".setu "):
                query = message.asDisplay().split(" ", maxsplit=1)[1]
                return await AdvancedImageSenderHandler.get_image_message(group, member, query)

    @staticmethod
    def sql_generate(
            restriction: str,
            conditions: list = None,
            img_id: int = -1,
            min_score: int = None,
            artist: str = None,
            exclude: list = None
    ):
        if conditions is None:
            conditions = []
        if exclude is None:
            exclude = []
        else:
            exclude = ["-" + e for e in exclude]
        if restriction == "s":
            restriction_sql = "(`restriction` = 's')"
        elif restriction == "q":
            restriction_sql = "(`restriction` = 's' OR `restriction` = 'q')"
        else:
            restriction_sql = "(`restriction` = 's' OR `restriction` = 'q' OR `restriction` = 'e')"
        sql = f"SELECT * FROM `advanced_setu` WHERE " + restriction_sql
        if img_id != -1:
            sql += f" AND `id` = {img_id}"
            return sql
        if conditions or exclude:
            sql_conditions_pos = []
            sql_conditions_neg = []
            for condition in conditions or exclude:
                if condition.startswith("-"):
                    is_exclude = True
                    condition = condition[1:]
                else:
                    is_exclude = False
                if special := re.findall(r"[ -/:-@\[-`\{-~]*", condition):
                    _temp = []
                    for _special in special:
                        if _special == "":
                            continue
                        if _special not in _temp:
                            _temp.append(_special)
                    for _special in _temp:
                        condition = condition.replace(_special, chr(92) + _special)
                if condition != "":
                    if not is_exclude:
                        if f"`tag` REGEXP '{condition}'" not in sql_conditions_pos:
                            sql_conditions_pos.append(f"`tag` REGEXP '{condition}'")
                    else:
                        if f"`tag` REGEXP '{condition}'" not in sql_conditions_neg:
                            sql_conditions_neg.append(f"`tag` NOT REGEXP '{condition}'")
            if sql_conditions_pos or sql_conditions_neg:
                sql += " AND " + " AND ".join(sql_conditions_pos + sql_conditions_neg)
        if isinstance(min_score, int):
            sql += f" AND `score` >= {min_score}"
        if artist:
            sql += f" AND `artist` = '{artist}'"
        return sql

    @staticmethod
    async def get_pic(restriction: str = "s", query: str = None):
        tags = None
        exclude = None
        img_id = -1
        min_score = None
        artist = None
        include_tags = False
        include_source = False
        count_only = False
        if query:
            _tags = query.split(' ')
            tags = []
            exclude = []
            for tag in _tags:
                if tag.startswith("id="):
                    if tag[3:].isdigit():
                        img_id = int(tag[3:])
                        break
                    else:
                        continue
                if tag.startswith("score="):
                    if tag[6:].isdigit():
                        min_score = int(tag[6:])
                        break
                    else:
                        continue
                if tag.startswith("artist="):
                    artist = tag[7:]
                    continue
                if tag == ":tag":
                    include_tags = True
                    continue
                if tag == ":source":
                    include_source = True
                    continue
                if tag == ":count":
                    count_only = True
                    continue
                if tag.startswith("#"):
                    tag = tag[1:]
                if tag.endswith("$"):
                    tag = f" {tag[:-1]} "
                if tag.startswith("-"):
                    if tag.startswith("#"):
                        exclude.append(tag[2:])
                    else:
                        exclude.append(tag[1:])
                    continue
                tags.append(tag)
        sql = AdvancedImageSenderHandler.sql_generate(
            restriction,
            tags,
            img_id=img_id,
            min_score=min_score,
            artist=artist,
            exclude=exclude
        )
        if results := (await orm.execute(sql)).fetchall():
            result = None
            img = None
            resp = None
            if not count_only:
                for _ in range(10):
                    result = random.choice(results)
                    if result[1] == 'twi':
                        if img := await TwitterPreview.get_tweet(core.get_app(), result[2], manual=False):
                            img = img.pic2bytes()
                            break
                    elif result[1] == 'img':
                        if os.path.isfile(config.functions['advanced_setu'] + result[2]):
                            img = config.functions['advanced_setu'] + result[2]
                            break
                if result:
                    tags = []
                    _tags = result[3].strip().split(" ")
                    for tag in _tags:
                        tag = "#" + tag
                        tags.append(tag)
                    restriction = result[4]
                    if restriction == 's':
                        restriction = 'Safe'
                    elif restriction == 'q':
                        restriction = 'Questionable'
                    elif restriction == 'e':
                        restriction = 'Explicit'
                    if include_tags:
                        if len(tags) > 25:
                            tags = ' '.join(tags[:25]) + ' ...'
                        else:
                            tags = ' '.join(tags)
                    else:
                        tags = str(len(tags)) + '个'
                    if include_source:
                        source = "来源：" + result[6] + "\n"
                    else:
                        source = ""
                    resp = [
                        Plain(text=f"编号：{result[0]}\n"
                                   f"分级：{restriction}\n"
                                   f"作者：{result[5]}\n"
                                   f"{source}"
                                   f"时间：{result[7]}\n"
                                   f"评分：{result[8]}\n"
                                   f"标签：{tags}"
                              ),
                        Image(data_bytes=img) if isinstance(img, bytes) else Image(path=img)
                    ]
            else:
                resp = [
                    Plain(text=f"组合：{' '.join(['#' + tag for tag in tags])}\n"
                               f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                               f"总数：{len(results)}")
                ]
            return resp
        else:
            return None

    @staticmethod
    @frequency_limit_require_weight_free(3)
    async def get_image_message(group: Group, member: Member, query: str = None) -> MessageItem:
        if query:
            if query.startswith(":set"):
                if query.startswith(":set="):
                    restriction_full = query[5:].lower()
                    if restriction_full not in ("off", "safe", "questionable", "explicit", "o", "s", "q", "e"):
                        return MessageItem(MessageChain.create([
                            Plain(text=f"无法找到分级 {restriction_full}，请发送 \".help 兽人图片\" 阅读文档。")
                        ]), QuoteSource())
                    restriction = query[5:6].lower()
                    if restriction in ("o", "s"):
                        if member.permission == MemberPerm.Member and not await user_permission_require(group, member,
                                                                                                        2):
                            return MessageItem(MessageChain.create([
                                Plain(text="权限不足，你需要来自管理员的权限才可更改本项。")
                            ]), QuoteSource())
                    elif restriction in ("q", "e"):
                        if not await user_permission_require(group, member, 4):
                            return MessageItem(MessageChain.create([
                                Plain(text="权限不足，你需要来自所有者的权限才可更改本项。")
                            ]), QuoteSource())
                    try:
                        await orm.insert_or_update(
                            Setting,
                            [Setting.group_id == group.id],
                            {"group_id": group.id,
                             "img_restriction": restriction})
                        return MessageItem(MessageChain.create([
                            Plain(text=f"已更改设置为 {restriction}")
                        ]), QuoteSource())
                    except:
                        return MessageItem(MessageChain.create([
                            Plain(text="设置出错，请联系机器人管理员")
                        ]), QuoteSource())
        restriction = await group_setting.get_setting(group.id, Setting.img_restriction)
        restriction = restriction if restriction else 's'
        if restriction == "o":
            return MessageItem(MessageChain.create([
                Plain(text="本群未开启本功能，请发送 \".help 兽人图片\" 阅读文档或联系管理员开启。")
            ]), Normal())
        if restriction == "e":
            r18_process = await group_setting.get_setting(group.id, Setting.r18_process)
            if r18_process == "revoke":
                if resp := await AdvancedImageSenderHandler.get_pic(restriction, query):
                    return MessageItem(MessageChain.create(
                        resp
                    ), Revoke(delay_second=60))
            elif r18_process == "flashImage":
                if resp := await AdvancedImageSenderHandler.get_pic(restriction, query):
                    return MessageItem(
                        MessageChain.create(
                            resp
                        ), Revoke(delay_second=60))
            elif r18_process == "noProcess":
                if resp := await AdvancedImageSenderHandler.get_pic(restriction, query):
                    return MessageItem(MessageChain.create(
                        resp
                    ), Normal())
            else:
                logger.error(f"r18_process 值 {r18_process} 非法，回落至 `rekove`")
                if resp := await AdvancedImageSenderHandler.get_pic(restriction, query):
                    return MessageItem(MessageChain.create(
                        resp
                    ), Revoke(delay_second=60))
            return MessageItem(MessageChain.create([Plain(text="无法找到符合条件的图片。")]), QuoteSource())
        else:
            if resp := await AdvancedImageSenderHandler.get_pic(restriction, query):
                return MessageItem(MessageChain.create(
                    resp
                ), Normal())
            return MessageItem(MessageChain.create([Plain(text="无法找到符合条件的图片。")]), QuoteSource())


class AdvancedImageSenderHelp(HelpPage):
    __description__ = "兽人图片"
    __trigger__ = ".setu"
    __category__ = "entertainment"
    __switch__ = None
    __icon__ = "image"

    def __init__(self, group: Group = None, member: Member = None, friend: Friend = None):
        super().__init__()
        self.__help__ = None
        self.group = group
        self.member = member
        self.friend = friend

    async def compose(self):
        if self.group or self.member:
            restriction = await group_setting.get_setting(self.group.id, Setting.img_restriction)
        else:
            restriction = "s"
        if restriction == 's':
            restriction = 'Safe'
        elif restriction == 'q':
            restriction = 'Questionable'
        elif restriction == 'e':
            restriction = 'Explicit'
        status = HelpPageElement(icon="lock-open", text=f"可用的分级为 {restriction}")
        self.__help__ = [
            HelpPageElement(icon=self.__icon__, text="兽人图片", is_title=True),
            HelpPageElement(text="字面意思（？）"),
            HelpPageElement(icon="check-all", text="已全局开启"),
            status,
            HelpPageElement(icon="lightbulb-on", text="使用示例：\n"
                                                      "全局随机：.setu\n"
                                                      "模糊搜索：.setu 肌\n"
                                                      "精确搜索：.setu 制服$\n"
                                                      "排除标签：.setu -胸肌\n"
                                                      "多个标签：.setu 腹肌 制服\n"
                                                      "编号搜索：.setu id=10\n"
                                                      "画师检索：.setu artist=画师名\n"
                                                      "评分筛选：.setu score=50"
                            ),
            HelpPageElement(icon="lightbulb-on", text="进阶示例：\n"
                                                      "包括标签：.setu :tag\n"
                                                      "包括来源：.setu :source\n"
                                                      "查找总数：.setu :count\n"
                            ),
            HelpPageElement(icon="texture", text="上文所列示例可自由组合形成更复杂更精准的匹配"),
            HelpPageElement(icon="pound-box", text="更改开关需要管理员权限\n"
                                                   "可用的开关值：off, safe\n"
                                                   "发送 \".setu :set=开关值\" 可更改开关"),
            HelpPageElement(icon="pound-box", text="更改图库需要所有者权限\n"
                                                   "可用的开关值：off, safe, questionable, explicit\n"
                                                   "如果你在看这里的话，那你应该就没权限更改这项设置\n")
        ]
        super().__init__(self.__help__)
        return await super().compose()
