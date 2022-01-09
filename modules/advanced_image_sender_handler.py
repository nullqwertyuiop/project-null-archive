import os
import random
import re
import traceback

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain, Image, FlashImage
from graia.broadcast.interrupt import InterruptControl
from graia.broadcast.interrupt.waiter import Waiter
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
from loguru import logger
from sqlalchemy import select

from SAGIRIBOT.Core.AppCore import AppCore
from SAGIRIBOT.Handler.Handler import AbstractHandler
from SAGIRIBOT.MessageSender.MessageItem import MessageItem
from SAGIRIBOT.MessageSender.MessageSender import GroupMessageSender
from SAGIRIBOT.MessageSender.Strategy import GroupStrategy, QuoteSource, Normal, Revoke
from SAGIRIBOT.ORM.AsyncORM import TriggerKeyword, Setting, UserCalledCount
from SAGIRIBOT.ORM.AsyncORM import orm
from SAGIRIBOT.decorators import frequency_limit_require_weight_free, switch, blacklist
from SAGIRIBOT.utils import get_config, get_setting

setting_column_index = {
    "setu": Setting.setu,
    "real": Setting.real,
    "realHighq": Setting.real_high_quality,
    "bizhi": Setting.bizhi,
    "sketch": Setting.setu
}

user_called_column_index = {
    "setu": UserCalledCount.setu,
    "real": UserCalledCount.real,
    "realHighq": UserCalledCount.real,
    "bizhi": UserCalledCount.bizhi,
    "sketch": UserCalledCount.setu
}

user_called_name_index = {
    "setu": "setu",
    "real": "real",
    "realHighq": "real",
    "bizhi": "bizhi",
    "sketch": "setu"
}
saya = Saya.current()
channel = Channel.current()


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def image_sender_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await AdvancedImageSenderHandler.handle(app, message, group, member):
        await GroupMessageSender(result.strategy).send(app, result.message, message, group, member)


class AdvancedImageSenderHandler(AbstractHandler):
    __name__ = "AdvancedImageSenderHandler"
    __description__ = "一个可以发送图片的Handler"
    __usage__ = "在群中发送设置好的关键词即可"
    functions = ("setu", "bizhi")

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group, member: Member):
        pass
        # if re.match(r"更新本群色图关键词#.*", message.asDisplay()):
        #     if await user_permission_require(group, member, 2):
        #         return await AdvancedImageSenderHandler.update_keyword(message.asDisplay())
        #     else:
        #         return MessageItem(MessageChain.create([Plain(text="权限不足，无法进行该操作。")]), QuoteSource(GroupStrategy()))
        # elif message.asDisplay() in (await orm.fetchall(select(AdvancedSetu.trigger_word).where(AdvancedSetu.trigger_word == message.asDisplay())))[0]:
        #     pass
        #     # resp_functions = resp_functions[0]
        #     # tfunc = None
        #     # for function in resp_functions:
        #     #     if function in AdvancedImageSenderHandler.functions:
        #     #         tfunc = function
        #     #         break
        #     # if not tfunc:
        #     #     return None
        #     # else:
        #     #     await update_user_call_count_plus1(group, member, user_called_column_index[tfunc], user_called_name_index[tfunc])
        #     #     if tfunc == "setu":
        #     #         if await get_setting(group.id, Setting.setu):
        #     #             if await get_setting(group.id, Setting.r18):
        #     #                 return await AdvancedImageSenderHandler.get_image_message(group, member, "setu18")
        #     #             else:
        #     #                 return await AdvancedImageSenderHandler.get_image_message(group, member, tfunc)
        #     #         else:
        #     #             return MessageItem(MessageChain.create([Plain(text="该功能已关闭，请阅读文档或者联系机器人管理员开启。")]), Normal(GroupStrategy()))
        #     #     elif tfunc == "realHighq":
        #     #         if await get_setting(group.id, Setting.real) and await get_setting(group.id, Setting.real_high_quality):
        #     #             return await AdvancedImageSenderHandler.get_image_message(group, member, tfunc)
        #     #         else:
        #     #             return MessageItem(MessageChain.create([Plain(text="该功能已关闭，请阅读文档或者联系机器人管理员开启。")]), Normal(GroupStrategy()))
        #     #     else:
        #     #         if await get_setting(group.id, setting_column_index[tfunc]):
        #     #             return await AdvancedImageSenderHandler.get_image_message(group, member, tfunc)
        #     #         else:
        #     #             return MessageItem(MessageChain.create([Plain(text="该功能已关闭，请阅读文档或者联系机器人管理员开启。")]), Normal(GroupStrategy()))
        # else:
        #     return None

    @staticmethod
    def random_pic(base_path: str) -> str:
        path_dir = os.listdir(base_path)
        path = random.sample(path_dir, 1)[0]
        return base_path + path

    @staticmethod
    async def get_pic(image_type: str) -> Image:

        async def color() -> str:
            base_path = get_config("setuPath")
            return f"{os.getcwd()}/statics/error/path_not_exists.png" if not os.path.exists(base_path) else AdvancedImageSenderHandler.random_pic(base_path)

        async def color18() -> str:
            base_path = get_config("setu18Path")
            return f"{os.getcwd()}/statics/error/path_not_exists.png" if not os.path.exists(base_path) else AdvancedImageSenderHandler.random_pic(base_path)

        async def real() -> str:
            base_path = get_config("realPath")
            return f"{os.getcwd()}/statics/error/path_not_exists.png" if not os.path.exists(base_path) else AdvancedImageSenderHandler.random_pic(base_path)

        async def real_highq() -> str:
            base_path = get_config("realHighqPath")
            return f"{os.getcwd()}/statics/error/path_not_exists.png" if not os.path.exists(base_path) else AdvancedImageSenderHandler.random_pic(base_path)

        async def wallpaper() -> str:
            base_path = get_config("wallpaperPath")
            return f"{os.getcwd()}/statics/error/path_not_exists.png" if not os.path.exists(base_path) else AdvancedImageSenderHandler.random_pic(base_path)

        async def sketch() -> str:
            base_path = get_config("sketchPath")
            return f"{os.getcwd()}/statics/error/path_not_exists.png" if not os.path.exists(base_path) else AdvancedImageSenderHandler.random_pic(base_path)

        switch = {
            "setu": color,
            "setu18": color18,
            "real": real,
            "realHighq": real_highq,
            "bizhi": wallpaper,
            "sketch": sketch
        }

        target_pic_path = await switch[image_type]()
        return Image(path=target_pic_path)

    @staticmethod
    @frequency_limit_require_weight_free(1)
    async def get_image_message(group: Group, member: Member, func: str) -> MessageItem:
        if func == "setu18":
            r18_process = await get_setting(group.id, Setting.r18_process)
            if r18_process == "revoke":
                return MessageItem(MessageChain.create([await AdvancedImageSenderHandler.get_pic(func)]), Revoke(GroupStrategy()))
            elif r18_process == "flashImage":
                return MessageItem(MessageChain.create([(FlashImage.fromImage(await AdvancedImageSenderHandler.get_pic(func)))]), Normal(GroupStrategy()))
            elif r18_process == "noProcess":
                return MessageItem(MessageChain.create([await AdvancedImageSenderHandler.get_pic(func)]), Normal(GroupStrategy()))
            else:
                return MessageItem(MessageChain.create([Plain(text=f"Error: r18_process 值非法: {r18_process}")]), QuoteSource(GroupStrategy()))
        return MessageItem(MessageChain.create([await AdvancedImageSenderHandler.get_pic(func)]), Normal(GroupStrategy()))

    @staticmethod
    async def update_keyword(message_serialization: str) -> MessageItem:
        _, function, keyword = message_serialization.split("#")
        if re.match(r"\[mirai:image:{.*}\..*]", keyword):
            keyword = re.findall(r"\[mirai:image:{(.*?)}\..*]", keyword, re.S)[0]
        if function not in AdvancedImageSenderHandler.functions:
            return MessageItem(MessageChain.create([Plain(text="非法方法名！")]), QuoteSource(GroupStrategy()))
        if await orm.fetchone(select(TriggerKeyword.keyword).where(TriggerKeyword.keyword == keyword)):
            return MessageItem(
                MessageChain.create([Plain(text="已存在的关键词！请先删除！")]),
                QuoteSource(GroupStrategy())
            )
        try:
            await orm.insert_or_ignore(
                TriggerKeyword,
                [TriggerKeyword.keyword == keyword, TriggerKeyword.function == function],
                {"keyword": keyword, "function": function}
            )
            return MessageItem(MessageChain.create([Plain(text=f"关键词添加成功！\n{keyword} -> {function}")]),
                               QuoteSource(GroupStrategy()))
        except Exception:
            logger.error(traceback.format_exc())
            return MessageItem(MessageChain.create([Plain(text="发生错误！请查看日志！")]), QuoteSource(GroupStrategy()))

    @staticmethod
    async def delete_keyword(app: Ariadne, group: Group, member: Member, message_serialization: str) -> MessageItem:
        _, keyword = message_serialization.split("#")
        if re.match(r"\[mirai:image:{.*}\..*]", keyword):
            keyword = re.findall(r"\[mirai:image:{(.*?)}\..*]", keyword, re.S)[0]
        if record := await orm.fetchone(select(TriggerKeyword.function).where(TriggerKeyword.keyword == keyword)):
            await app.sendGroupMessage(
                group,
                MessageChain.create([
                    Plain(text=f"查找到以下信息：\n{keyword} -> {record[0]}\n是否删除？（是/否）")
                ])
            )
            inc = InterruptControl(AppCore.get_core_instance().get_bcc())

            @Waiter.create_using_function([GroupMessage])
            def confirm_waiter(waiter_group: Group, waiter_member: Member, waiter_message: MessageChain):
                if all([
                    waiter_group.id == group.id,
                    waiter_member.id == member.id
                ]):
                    if re.match(r"[是否]", waiter_message.asDisplay()):
                        return waiter_message.asDisplay()
                    else:
                        return ""

            result = await inc.wait(confirm_waiter)

            if not result:
                return MessageItem(MessageChain.create([Plain(text="非预期回复，进程退出")]), Normal(GroupStrategy()))
            elif result == "是":
                try:
                    await orm.delete(TriggerKeyword, [TriggerKeyword.keyword == keyword])
                except:
                    logger.error(traceback.format_exc())
                    return MessageItem(MessageChain.create([Plain(text="发生错误！请查看日志！")]), QuoteSource(GroupStrategy()))
                return MessageItem(MessageChain.create([Plain(text=f"关键词 {keyword} 删除成功")]), Normal(GroupStrategy()))
            else:
                return MessageItem(MessageChain.create([Plain(text="进程退出")]), Normal(GroupStrategy()))
        else:
            return MessageItem(MessageChain.create([Plain(text="未找到关键词数据！请检查输入！")]), QuoteSource(GroupStrategy()))
