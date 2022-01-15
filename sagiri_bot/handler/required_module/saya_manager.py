import os
import re
from typing import List, Dict, Optional, Union

from graia.ariadne.model import Friend
from graia.saya import Saya, Channel
from graia.ariadne.app import Ariadne
from graia.ariadne.message.element import Plain
from graia.broadcast.interrupt.waiter import Waiter
from graia.ariadne.message.chain import MessageChain
from graia.broadcast.interrupt import InterruptControl
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.ariadne.event.message import Group, Member, GroupMessage, FriendMessage

from sagiri_bot.core.app_core import AppCore
from sagiri_bot.utils import user_permission_require
from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.strategy import QuoteSource
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender

saya = Saya.current()
channel = Channel.current()

channel.name("SayaManager")
channel.author("SAGIRI-kawaii")
channel.description(
    "插件管理插件"
    "发送 `已加载插件` 查看已加载插件\n"
    "发送 `插件详情 [编号|名称]` 可查看插件详情\n"
    "发送 `[加载|重载|卸载]插件 [编号|名称]` 可加载/重载/卸载插件"
)

core = AppCore.get_core_instance()
inc = InterruptControl(core.get_bcc())


@channel.use(ListenerSchema(listening_events=[FriendMessage]))
async def saya_manager(app: Ariadne, message: MessageChain, friend: Friend):
    if result := await SayaManager.handle(app, message, friend=friend):
        await MessageSender(result.strategy).send(app, result.message, message, friend, friend)


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def saya_manager(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await SayaManager.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class SayaManager(AbstractHandler):
    __name__ = "SayaManager"
    __description__ = "插件管理"
    __usage__ = "发送 `已加载插件` 查看已加载插件\n" \
                "发送 `插件详情 [编号|名称]` 可查看插件详情\n" \
                "发送 `[加载|重载|卸载]插件 [编号|名称]` 可加载/重载/卸载插件"

    @staticmethod
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None) -> MessageItem:
        if message.asDisplay().strip() == "已加载插件":
            loaded_channels = SayaManager.get_loaded_channels()
            keys = list(loaded_channels.keys())
            keys.sort()
            return MessageItem(
                MessageChain.create([
                    Plain(text="目前加载插件：\n")
                ] + [
                    Plain(text=f"{i + 1}. {loaded_channels[keys[i]]._name}\n")
                    for i in range(len(keys))
                ] + [
                    Plain(text="发送 `插件详情 [编号|名称]` 可查看插件详情")
                ]),
                QuoteSource()
            )
        elif message.asDisplay().startswith("插件详情 "):
            target = message.asDisplay()[5:].strip()
            loaded_channels = SayaManager.get_loaded_channels()
            keys = list(loaded_channels.keys())
            if target.isdigit():
                keys.sort()
                if not 0 <= int(target) - 1 < len(keys):
                    return MessageItem(MessageChain.create([Plain(text="错误的编号！请检查后再发送！")]), QuoteSource())
                channel = loaded_channels[keys[int(target) - 1]]
                channel_path = keys[int(target) - 1]
            else:
                for lchannel in loaded_channels.keys():
                    if loaded_channels[lchannel]._name == target:
                        channel = loaded_channels[lchannel]
                        channel_path = lchannel
                        break
                else:
                    return MessageItem(MessageChain.create([Plain(text="错误的名称！请检查后再发送！")]), QuoteSource())
            return MessageItem(
                MessageChain.create([
                    Plain(text=f"插件名称：{channel._name}\n"),
                    Plain(text=f"插件作者：{'、'.join(channel._author)}\n"),
                    Plain(text=f"插件描述：{channel._description}\n"),
                    Plain(text=f"插件包名：{channel_path}")
                ]),
                QuoteSource()
            )
        elif message.asDisplay().startswith("未加载插件"):
            if not user_permission_require(group, member, 3):
                return MessageItem(MessageChain.create([Plain(text="爬，权限不足")]), QuoteSource())
            unloaded_channels = SayaManager.get_unloaded_channels()
            unloaded_channels.sort()
            return MessageItem(
                MessageChain.create([
                    Plain(text="目前未加载插件：\n")
                ] + [
                    Plain(text=f"{i + 1}. {unloaded_channels[i]}\n")
                    for i in range(len(unloaded_channels))
                ] + [
                    Plain(text="发送 `[加载|卸载|重载]插件 [编号|名称]` 可加载/卸载/重载插件\n")
                ]),
                QuoteSource()
            )
        elif message.asDisplay().startswith("加载插件 "):
            if not user_permission_require(group, member, 3):
                return MessageItem(MessageChain.create([Plain(text="爬，权限不足")]), QuoteSource())
            target = message.asDisplay()[5:].strip()
            unloaded_channels = SayaManager.get_unloaded_channels()
            if target.isdigit():
                unloaded_channels.sort()
                if not 0 <= int(target) - 1 < len(unloaded_channels):
                    return MessageItem(MessageChain.create([Plain(text="错误的编号！请检查后再发送！")]), QuoteSource())
                channel = unloaded_channels[int(target) - 1]
            else:
                for ulchannel in unloaded_channels:
                    if ulchannel == target:
                        channel = ulchannel
                        break
                else:
                    return MessageItem(MessageChain.create([Plain(text="错误的名称！请检查后再发送！")]), QuoteSource())

            await app.sendMessage(group, MessageChain.create([Plain(text=f"你确定要加载插件 `{channel}` 吗？（是/否）")]))

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
                return MessageItem(MessageChain.create([Plain(text="非预期回复，进程退出")]), QuoteSource())
            elif result == "是":
                result = SayaManager.load_channel(channel)
                if result:
                    return MessageItem(MessageChain.create([Plain(text=f"发生错误：{result[channel]}")]), QuoteSource())
                else:
                    return MessageItem(MessageChain.create([Plain(text="加载成功")]), QuoteSource())
            else:
                return MessageItem(MessageChain.create([Plain(text="进程退出")]), QuoteSource())
        elif re.match(r"[卸重]载插件", message.asDisplay()):
            if not user_permission_require(group, member, 3):
                return MessageItem(MessageChain.create([Plain(text="爬，权限不足")]), QuoteSource())
            load_type = "reload" if message.asDisplay()[0] == "重" else "unload"
            target = message.asDisplay()[5:].strip()
            loaded_channels = SayaManager.get_loaded_channels()
            keys = list(loaded_channels.keys())
            keys.sort()
            if target.isdigit():
                if not 0 <= int(target) - 1 < len(keys):
                    return MessageItem(MessageChain.create([Plain(text="错误的编号！请检查后再发送！")]), QuoteSource())
                channel = loaded_channels[keys[int(target) - 1]]
                channel_path = keys[int(target) - 1]
            else:
                for lchannel in loaded_channels.keys():
                    if loaded_channels[lchannel]._name == target:
                        channel = loaded_channels[lchannel]
                        channel_path = lchannel
                        break
                else:
                    return MessageItem(MessageChain.create([Plain(text="错误的名称！请检查后再发送！")]), QuoteSource())

            await app.sendMessage(group, MessageChain.create([Plain(text=f"你确定要{message.asDisplay()[0]}载插件 `{channel._name}` 吗？（是/否）")]))

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
                return MessageItem(MessageChain.create([Plain(text="非预期回复，进程退出")]), QuoteSource())
            elif result == "是":
                result = SayaManager.unload_channel(channel_path) if load_type == "unload" else SayaManager.reload_channel(channel_path)
                if result:
                    return MessageItem(MessageChain.create([Plain(text=f"发生错误：{result[channel_path]}")]), QuoteSource())
                else:
                    return MessageItem(MessageChain.create([Plain(text=f"{message.asDisplay()[0]}载成功")]), QuoteSource())
            else:
                return MessageItem(MessageChain.create([Plain(text="进程退出")]), QuoteSource())

    @staticmethod
    def get_loaded_channels() -> Dict[str, Channel]:
        return saya.channels

    @staticmethod
    def get_all_channels() -> List[str]:
        ignore = ["__init__.py", "__pycache__"]
        dirs = ["modules", "sagiri_bot/handler/required_module", "sagiri_bot/handler/handlers"]
        modules = []
        for path in dirs:
            for module in os.listdir(path):
                if module in ignore:
                    continue
                if os.path.isdir(module):
                    modules.append(f"{path.replace('/', '.')}.{module}")
                else:
                    modules.append(f"{path.replace('/', '.')}.{module.split('.')[0]}")
        return modules

    @staticmethod
    def get_unloaded_channels() -> List[str]:
        loaded_channels = SayaManager.get_loaded_channels()
        all_channels = SayaManager.get_all_channels()
        return [channel for channel in all_channels if channel not in loaded_channels]

    @staticmethod
    def get_channel(name: str) -> Optional[Channel]:
        return SayaManager.get_loaded_channels().get(name)

    @staticmethod
    def load_channel(modules: Union[str, List[str]]) -> Dict[str, Exception]:
        ignore = ["__init__.py", "__pycache__"]
        exceptions = {}
        if isinstance(modules, str):
            modules = [modules]
        with saya.module_context():
            for module in modules:
                if module in ignore:
                    continue
                try:
                    saya.require(module)
                except Exception as e:
                    exceptions[module] = e
        return exceptions

    @staticmethod
    def unload_channel(modules: Union[str, List[str]]) -> Dict[str, Exception]:
        exceptions = {}
        if isinstance(modules, str):
            modules = [modules]
        loaded_channels = SayaManager.get_loaded_channels()
        channels_to_unload = {module: loaded_channels[module] for module in modules if module in loaded_channels}
        with saya.module_context():
            for channel in channels_to_unload.keys():
                try:
                    saya.uninstall_channel(channels_to_unload[channel])
                except Exception as e:
                    exceptions[channel] = e
        return exceptions

    @staticmethod
    def reload_channel(modules: Union[str, List[str]]) -> Dict[str, Exception]:
        exceptions = {}
        if isinstance(modules, str):
            modules = [modules]
        loaded_channels = SayaManager.get_loaded_channels()
        channels_to_reload = {module: loaded_channels[module] for module in modules if module in loaded_channels}
        with saya.module_context():
            for channel in channels_to_reload.keys():
                try:
                    saya.reload_channel(channels_to_reload[channel])
                except Exception as e:
                    exceptions[channel] = e
        return exceptions
