import re
import urllib.parse
from io import BytesIO

import qrcode
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage, FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Xml, Plain, Image
from graia.ariadne.model import Friend
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema

from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import Normal, QuoteSource
from sagiri_bot.orm.async_orm import Setting
from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.utils import get_setting

saya = Saya.current()
channel = Channel.current()

channel.name("HelpYouSearch")
channel.author("nullqwertyuiop")
channel.description("自己查")


@channel.use(ListenerSchema(listening_events=[FriendMessage]))
async def help_you_search_handler(app: Ariadne, message: MessageChain, friend: Friend):
    if result := await HelpYouSearch.handle(app, message, friend=friend):
        await MessageSender(result.strategy).send(app, result.message, message, friend, friend)


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def help_you_search_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await HelpYouSearch.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class HelpYouSearch(AbstractHandler):
    __name__ = "HelpYouSearch"
    __description__ = "帮你查查 Handler"
    __usage__ = "None"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if re.match("百度 (.*)", message.asDisplay()):
            if group and member:
                if await get_setting(group.id, Setting.search_helper):
                    reg = re.compile("百度 (.*)")
                    key = reg.search(message.asDisplay()).group(1)
                    key = urllib.parse.quote(key)
                    return MessageItem(MessageChain.create([
                        await HelpYouSearch.baidu(key, "link")]),
                        QuoteSource())
            elif friend:
                reg = re.compile("百度 (.*)")
                key = reg.search(message.asDisplay()).group(1)
                key = urllib.parse.quote(key)
                return MessageItem(MessageChain.create([
                    await HelpYouSearch.baidu(key, "link")]),
                    QuoteSource())
        else:
            return None

    @staticmethod
    async def baidu(key: str, type: str):
        if type == "card":
            return MessageItem(MessageChain.create([
                Xml(xml=f'<?xml version=\'1.0\' encoding=\'UTF-8\' standalone=\'yes\' ?><msg serviceID="146" '
                        f'templateID="1" action="web" brief="百度搜索_{key}" sourceMsgId="0" '
                        f'url="http://www.baidu.com/s?wd={key}" flag="0" adverSign="0" multiMsgFlag="0"><item '
                        f'layout="2" advertiser_id="0" aid="0"><picture cover="" w="0" h="0" '
                        f'/><title>帮你百度</title><summary>{key}</summary></item><source name="Project. Null" icon="" '
                        f'url="" action="app" a_actionData="com.tencent.mtt://www.baidu.com/s?wd={key}" '
                        f'i_actionData="tencent100446242://http://www.baidu.com/s?wd={key}" appid="-1" /></msg>')]),
                Normal())
        elif type == "link":
            return Plain(text=f'http://www.baidu.com/s?wd={key}')
        elif type == "qrcode":
            qrcode_img = qrcode.make(key)
            bytes_io = BytesIO()
            qrcode_img.save(bytes_io)
            return Image(data_bytes=bytes_io.getvalue())
