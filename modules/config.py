import re
import time

from graia.ariadne.app import Ariadne, Friend
from graia.ariadne.event.message import Group, Member, FriendMessage, GroupMessage
from graia.ariadne.exception import AccountMuted
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain, Source
from graia.broadcast.interrupt import Waiter, InterruptControl
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema

from sagiri_bot.core.app_core import AppCore
from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import QuoteSource
from sagiri_bot.decorators import switch, blacklist

saya = Saya.current()
channel = Channel.current()

channel.name("Config")
channel.author("nullqwertyuiop")
channel.description("忘了这个是干什么的了")


# @channel.use(ListenerSchema(listening_events=[GroupMessage]))
# async def command_handler(app: Ariadne, message: MessageChain, friend: Friend):
#     if result := await Config.handle(app, message, friend=friend):
#         await MessageSender(result.strategy).send(app, result.message, message, friend, friend)
#
#
# @channel.use(ListenerSchema(listening_events=[GroupMessage]))
# async def command_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
#     if result := await Config.handle(app, message, group=group, member=member):
#         await MessageSender(result.strategy).send(app, result.message, message, group, member)


class Config(AbstractHandler):
    __name__ = "Config"
    __description__ = "配置 Handler"
    __usage__ = "None"
    available_variables = {
        "bilibili_link_resolve": [
            "%封面%",
            "%标题%",
            "%分区%",
            "%视频类型%",
            "%投稿时间%",
            "%视频长度%",
            "%up%",
            "%播放量%",
            "%弹幕量%",
            "%评论量%",
            "%点赞量%",
            "%投币量%",
            "%收藏量%",
            "%转发量%",
            "%简介%",
            "%av号%",
            "%bv号%",
            "%链接%"
        ],
        "bilibili_app_parse": [
            "%封面%",
            "%标题%",
            "%分区%",
            "%视频类型%",
            "%投稿时间%",
            "%视频长度%",
            "%up%",
            "%播放量%",
            "%弹幕量%",
            "%评论量%",
            "%点赞量%",
            "%投币量%",
            "%收藏量%",
            "%转发量%",
            "%简介%",
            "%av号%",
            "%bv号%",
            "%链接%"
        ]
    }
    group_config = {
        "0": {
            "bilibili_link_resolve": "",
            "bilibili_app_parse": ""
        }
    }
    cord = {
        "b站链接解析": "bilibili_link_resolve",
        "b站卡片解析": "bilibili_app_parse"
    }
    reversed_cord = {
        "bilibili_link_resolve": "B 站链接解析",
        "bilibili_app_parse": "B 站卡片解析"
    }

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        # if setting := re.compile("更改(.*)自定义设置").search(message.asDisplay()):
        #     if setting.group(1) == "":
        #         config_list = [Config.reversed_cord[item] for item in Config.reversed_cord.keys()]
        #         config_query = [Plain(text=f"支持自定义的模块如下：")]
        #         for index in range(len(config_list)):
        #             config_query.append(Plain(text=f"{index + 1}. {config_list[index]}"))
        #         try:
        #             await app.sendGroupMessage(group, MessageChain.create(config_query), quote=message[Source][0])
        #         except AccountMuted:
        #             return None
        #
        #         @Waiter.create_using_function([GroupMessage, FriendMessage])
        #         def quit_waiter(waiter_message: MessageChain, waiter_group: Group = None, waiter_member: Member = None,
        #                         waiter_friend: Friend = None):
        #             if time.time() - start_time > 30:
        #                 return None
        #             if all([
        #                 waiter_group,
        #                 waiter_member,
        #             ]):
        #                 if all([
        #                     waiter_group.id == group.id,
        #                     waiter_member.id == member.id,
        #                 ]):
        #                     return waiter_message
        #             elif waiter_friend:
        #                 if waiter_friend == friend.id:
        #                     return waiter_message
        #
        #         bcc = AppCore.get_core_instance().get_bcc()
        #         inc = InterruptControl(bcc)
        #         start_time = time.time()
        #         choice = await inc.wait(quit_waiter)
        #         print(choice.asDisplay())
        #     setting = setting.group(1).replace(" ", "").lower()
        #     if Config.cord[setting] == "bilibili_link_resolve":
                pass

    @staticmethod
    async def update_setting(item: str, settings: str, group: Group):
        if group.id in Config.group_config.keys():
            Config.group_config[str(group.id)][item] = settings
        else:
            Config.group_config.update({str(group.id): {item: settings}})

    @staticmethod
    async def bilibili_link_resolve(settings: str):
        pass
