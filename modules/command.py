import json
import math
import os
from typing import Union

from graia.ariadne.app import Ariadne, Friend
from graia.ariadne.event.message import Group, Member, FriendMessage, TempMessage, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain, Image
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema

from SAGIRIBOT.Handler.Handler import AbstractHandler
from SAGIRIBOT.MessageSender.MessageItem import MessageItem
from SAGIRIBOT.MessageSender.MessageSender import FriendMessageSender, TempMessageSender, GroupMessageSender
from SAGIRIBOT.MessageSender.Strategy import FriendStrategy, TempStrategy, \
    StrategyType, QuoteSource, GroupStrategy
from SAGIRIBOT.decorators import switch, blacklist
from SAGIRIBOT.utils import get_config

saya = Saya.current()
channel = Channel.current()


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def command_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await CommandHandler.handle(app, message, group=group, member=member, strategy=GroupStrategy()):
        await GroupMessageSender(result.strategy).send(app, result.message, message, group, member)


@channel.use(ListenerSchema(listening_events=[FriendMessage]))
async def command_handler(app: Ariadne, message: MessageChain, friend: Friend):
    if result := await CommandHandler.handle(app, message, friend=friend, strategy=FriendStrategy()):
        await FriendMessageSender(result.strategy).send(app, result.message, message, friend)


@channel.use(ListenerSchema(listening_events=[TempMessage]))
async def command_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await CommandHandler.handle(app, message, group=group, member=member, strategy=TempStrategy()):
        await TempMessageSender(result.strategy).send(app, result.message, message, group, member)


class CommandHandler(AbstractHandler):
    __name__ = "CommandHandler"
    __description__ = "测试 Handler"
    __usage__ = "None"
    command_list = ["/contact", "/feedback", "/help"]

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, strategy: StrategyType, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if message.asDisplay().startswith("/"):
            cord = {
                "/contact": CommandHandler.contact,
                "/feedback": CommandHandler.contact,
                "/help": CommandHandler.help,
                "/execute": CommandHandler.execute
            }
            try:
                command, content = message.asDisplay().split(" ", maxsplit=1)
            except ValueError:
                command = message.asDisplay()
                content = None
            if command not in CommandHandler.command_list:
                return None
            return MessageItem(MessageChain.create(
                await cord[command](app, message, strategy, group=group, member=member, friend=friend, content=content)
            ), QuoteSource(strategy))

    @staticmethod
    async def contact(app: Ariadne, message: MessageChain, strategy: StrategyType,
                      group: Union[Group, int] = None, member: Union[Member, int] = None,
                      friend: Union[Friend, int] = None, content: Union[str, None] = None) -> Union[list, None]:
        if type(strategy) not in [GroupStrategy, TempStrategy, FriendStrategy]:
            return None
        if not content:
            return [
                Plain(text=f"未填写内容。")
            ]
        try:
            prefix = None
            strategy_used = "BUG"
            if type(strategy) == FriendStrategy and friend.id != get_config("HostQQ"):
                prefix = f"机器人收到来自好友 <{friend.id}> 的消息："
                strategy_used = "好友"
            elif type(strategy) == TempStrategy and member.id != get_config("HostQQ"):
                prefix = f"机器人收到来自群 <{group.id}> 中成员 <{member.id}> 的临时消息："
                strategy_used = "临时"
            elif type(strategy) == GroupStrategy and member.id != get_config("HostQQ"):
                prefix = f"机器人收到来自群 <{group.id}> 中成员 <{member.id}> 的消息："
                strategy_used = "群聊"
            forward = [Plain(text=prefix), Plain(text=f"\n{content}")]
            for images in message[Image]:
                forward.append(Plain(text=f"\n{images.url}"))
            await app.sendFriendMessage(
                get_config("HostQQ"), MessageChain.create(forward)
            )
            forward_status = True
        except:
            strategy_used = "无"
            forward_status = False
        return [
            Plain(text=f"应用策略：{strategy_used}\n"
                       f"转发状态：{'成功' if forward_status else '失败'}")
        ]

    @staticmethod
    async def help(app: Ariadne, message: MessageChain, strategy: StrategyType,
                   group: Union[Group, int] = None, member: Union[Member, int] = None,
                   friend: Union[Friend, int] = None, content: Union[str, None] = None) -> Union[list, None]:
        if type(strategy) not in [GroupStrategy, TempStrategy, FriendStrategy]:
            return None
        with open(f"{os.getcwd()}/statics/manual.json", "r", encoding="utf-8") as r:
            manual = json.loads(r.read())
        if type(strategy) == GroupStrategy:
            commands = manual["available_command"]["group"]
            env = "群聊"
        elif type(strategy) == TempStrategy:
            commands = manual["available_command"]["temp"]
            env = "临时"
        else:
            commands = manual["available_command"]["friend"]
            env = "好友"
        resp = [Plain(text="[帮助]")]
        if not content:
            resp.append(Plain(text=f"\n{env}环境下可用的指令有："))
            print(commands)
            if len(commands) > 10:
                for command_index in range(10):
                    command = commands[command_index]
                    resp.append(Plain(text=f"\n{command_index + 1}. {command}"))
                resp.append(Plain(text=f'\n----------'))
                resp.append(Plain(text=f"\n第 1 页，共 {math.ceil(len(commands) / 10)} 页"))
                resp.append(Plain(text=f'\n发送 "/help 页数" 翻页'))
            else:
                for command_index in range(len(commands)):
                    command = commands[command_index]
                    resp.append(Plain(text=f"\n{command_index + 1}. {command}"))
            resp.extend([
                Plain(text=f"\n----------"),
                Plain(text=f'\n可发送 "/help 指令名" 查看该指令的介绍与用法。'),
                Plain(text=f'\n注意：由于不同模块触发方式不同，部分模块的实际触发方式请使用 "/help 指令名" 查看。')
            ])
        else:
            try:
                content = int(content)
                if not 0 < content < (int(len(commands) / 10) + 2):
                    if content in (114514, 1919, 1145141919, 1919114514):
                        resp.append(Plain(text="\n没有这么臭的页码。"))
                    elif content == 130:
                        resp.append(Plain(text="\n页数非法噜，珍素 big 胆！"))
                    elif content < 0:
                        resp.append(Plain(text="\n哪来的负数页码。"))
                    else:
                        resp.append(Plain(text=f"\n页数非法。"))
                    return resp
                command_index_dist = content * 10
                command_index_max = len(commands)
                command_index_start = (content - 1) * 10
                if command_index_dist > command_index_max:
                    command_index_dist = command_index_max
                for command_index in range(command_index_start, command_index_dist):
                    command = commands[command_index]
                    resp.append(Plain(text=f"\n{command_index + 1}. {command}"))
                resp.append(Plain(text=f'\n----------'))
                resp.append(Plain(text=f"\n第 {content} 页，共 {(int(len(commands) / 10) + 1)} 页"))
                resp.append(Plain(text=f'\n发送 "/help 页数" 翻页'))
                resp.extend([
                    Plain(text=f"\n----------"),
                    Plain(text=f'\n可发送 "/help 指令名" 查看该指令的介绍与用法。'),
                    Plain(text=f'\n注意：由于不同模块触发方式不同，部分模块的实际触发方式请使用 "/help 指令名" 查看。')
                ])
                return resp
            except (ValueError, TypeError):
                pass
            if content.startswith("/"):
                _, content = content.split("/", maxsplit=1)
            try:
                cord_command = manual['cord'][content]
                resp.extend([
                    Plain(text=f"\n{content} - {manual['manual'][cord_command]['name']}"),
                    Plain(text=f"\n简介：{manual['manual'][cord_command]['disc']}"),
                    Plain(text=f"\n用法：{manual['manual'][cord_command]['usage']}"),
                    Plain(text=f"\n示例：{manual['manual'][cord_command]['example']}"),
                ])
                if manual['manual'][cord_command]['perm'] != '':
                    resp.append(Plain(text=f"\n修改设置所需权限：{manual['manual'][cord_command]['perm']}"))
            except KeyError:
                resp.append(Plain(text=f'\n未查找到指令 "{content}"，请检查您的输入。'))
        return resp

    @staticmethod
    async def execute(app: Ariadne, message: MessageChain, strategy: StrategyType,
                      group: Union[Group, int] = None, member: Union[Member, int] = None,
                      friend: Union[Friend, int] = None, content: Union[str, None] = None) -> Union[list, None]:
        if type(strategy) not in [GroupStrategy, TempStrategy, FriendStrategy]:
            return None
        pass

    @staticmethod
    async def list(app: Ariadne, message: MessageChain, strategy: StrategyType,
                   group: Union[Group, int] = None, member: Union[Member, int] = None,
                   friend: Union[Friend, int] = None, content: Union[str, None] = None) -> Union[list, None]:
        pass
