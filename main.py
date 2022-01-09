# -*- coding: utf-8 -*-
import os
import yaml
import traceback
import threading
from loguru import logger

from graia.ariadne.app import Ariadne
from graia.ariadne.message.element import Plain
from graia.ariadne.event.lifecycle import ApplicationLaunched
from graia.ariadne.event.message import Group, Member, MessageChain, Friend

from sagiri_bot.core.app_core import AppCore
from sagiri_bot.utils import online_notice, load_config

core = AppCore(load_config())

app = core.get_app()
bcc = core.get_bcc()
saya = core.get_saya()
config = core.get_config()

logger.add(
    f"{os.getcwd()}/log/common.log",
    level="INFO",
    retention=f"{config.log_related['common_retention']} days",
    encoding="utf-8"
)
logger.add(
    f"{os.getcwd()}/log/error.log",
    level="ERROR",
    retention=f"{config.log_related['error_retention']} days",
    encoding="utf-8"
)

ignore = ["__init__.py", "__pycache__"]
with saya.module_context():
    for module in os.listdir("sagiri_bot/handler/handlers"):
        if module in ignore:
            continue
        try:
            if os.path.isdir(module):
                saya.require(f"sagiri_bot.handler.handlers.{module}")
            else:
                saya.require(f"sagiri_bot.handler.handlers.{module.split('.')[0]}")
        except ModuleNotFoundError:
            pass

core.load_saya_modules()


@bcc.receiver("GroupMessage")
async def group_message_handler(message: MessageChain, group: Group, member: Member):
    message_text_log = message.asDisplay().replace("\n", "\\n")
    logger.info(f"收到来自群 <{group.name}> 中成员 <{member.name}> 的消息：{message_text_log}")


@bcc.receiver("FriendMessage")
async def friend_message_listener(message: MessageChain, friend: Friend):
    message_text_log = message.asDisplay().replace("\n", "\\n")
    logger.info(f"收到来自好友 <{friend.nickname}> 的消息：{message_text_log}")


@bcc.receiver("TempMessage")
async def friend_message_listener(app: Ariadne, message: MessageChain, group: Group, member: Member):
    message_text_log = message.asDisplay().replace("\n", "\\n")
    logger.info(f"收到来自群 <{group.name}> 中成员 <{member.name}> 的临时消息：{message_text_log}")
    try:
        await app.sendTempMessage(group=group, target=member,
                                  message=MessageChain.create([
                                      Plain(text='本项目暂时无法响应临时消息，请见谅。')
                                  ]))
    except Exception as e:
        logger.error(e)


@logger.catch
@bcc.receiver(ApplicationLaunched)
async def init():
    await core.bot_launch_init()
    await online_notice(app)


core.launch()
