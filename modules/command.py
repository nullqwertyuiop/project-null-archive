import json
import math
import os
from typing import Union

from graia.ariadne.app import Ariadne, Friend
from graia.ariadne.event.message import Group, Member, FriendMessage, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain, Image
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
core: AppCore = AppCore.get_core_instance()
config = core.get_config()

channel.name("Command")
channel.author("nullqwertyuiop")
channel.description("瞎**乱写的指令功能")


@channel.use(ListenerSchema(listening_events=[FriendMessage]))
async def command_handler(app: Ariadne, message: MessageChain, friend: Friend):
    if result := await Command.handle(app, message, friend=friend):
        await MessageSender(result.strategy).send(app, result.message, message, friend, friend)


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def command_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await Command.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class Command(AbstractHandler):
    __name__ = "Command"
    __description__ = "测试 Handler"
    __usage__ = "None"
    command_list = ["/contact", "/feedback", "/help"]

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if message.asDisplay().startswith("/"):
            cord = {
                "/contact": Command.contact,
                "/feedback": Command.contact,
                "/help": Command.help
            }
            try:
                command, content = message.asDisplay().split(" ", maxsplit=1)
            except ValueError:
                command = message.asDisplay()
                content = None
            if command not in Command.command_list:
                return None
            return MessageItem(MessageChain.create(
                await cord[command](app, message, group=group, member=member, friend=friend, content=content)
            ), QuoteSource())

    @staticmethod
    async def contact(app: Ariadne, message: MessageChain, group: Union[Group, int] = None,
                      member: Union[Member, int] = None, friend: Union[Friend, int] = None,
                      content: Union[str, None] = None) -> Union[list, None]:
        if not content:
            return [
                Plain(text=f"未填写内容。")
            ]
        try:
            prefix = None
            strategy_used = "BUG"
            if friend and friend.id != config.host_qq:
                prefix = f"机器人收到来自好友 <{friend.id}> 的消息："
                strategy_used = "好友"
            elif member and group and member.id != config.host_qq:
                prefix = f"机器人收到来自群 <{group.id}> 中成员 <{member.id}> 的消息："
                strategy_used = "群聊"
            forward = [Plain(text=prefix), Plain(text=f"\n{content}")]
            for images in message[Image]:
                forward.append(Plain(text=f"\n{images.url}"))
            await app.sendFriendMessage(
                config.host_qq, MessageChain.create(forward)
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
    async def help(app: Ariadne, message: MessageChain, group: Union[Group, int] = None,
                   member: Union[Member, int] = None, friend: Union[Friend, int] = None,
                   content: Union[str, None] = None) -> Union[list, None]:
        return [
            Plain(text="本功能触发词已改为 \".help\"，请通过新触发词使用。"),
        ]
        with open(f"{os.getcwd()}/statics/manual.json", "r", encoding="utf-8") as r:
            manual = json.loads(r.read())
        if member and group:
            commands = manual["available_command"]["group"]
            env = "群聊"
        elif friend:
            commands = manual["available_command"]["friend"]
            env = "好友"
        else:
            return None
        resp = [
            Plain(text="**帮助功能将进行重大改动，本帮助页暂时停止更新**\n"),
            Plain(text="[帮助]")
        ]
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
