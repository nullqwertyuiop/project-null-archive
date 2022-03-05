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
from sagiri_bot.utils import group_setting, HelpPage, HelpPageElement

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
                if await group_setting.get_setting(group.id, Setting.search_helper):
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


class HelpYouSearchHelp(HelpPage):
    __description__ = "帮你百度"
    __trigger__ = "百度 内容"
    __category__ = 'utility'
    __switch__ = Setting.search_helper
    __icon__ = "magnify"

    def __init__(self, group: Group = None, member: Member = None, friend: Friend = None):
        super().__init__()
        self.__help__ = None
        self.group = group
        self.member = member
        self.friend = friend

    async def compose(self):
        if self.group or self.member:
            if not await group_setting.get_setting(self.group.id, Setting.search_helper):
                status = HelpPageElement(icon="toggle-switch-off", text="已关闭")
            else:
                status = HelpPageElement(icon="toggle-switch", text="已开启")
        else:
            status = HelpPageElement(icon="check-all", text="已全局开启")
        self.__help__ = [
            HelpPageElement(icon=self.__icon__, text="帮你百度", is_title=True),
            HelpPageElement(text="根据请求生成一个访问百度的链接"),
            status,
            HelpPageElement(icon="pound-box", text="更改设置需要管理员权限\n"
                                                   "发送\"可以帮忙百度\"或者\"不可以帮忙百度\"即可更改开关"),
            HelpPageElement(icon="lightbulb-on", text="使用示例：\n发送\"百度 需要百度的内容\"即可")
        ]
        super().__init__(self.__help__)
        return await super().compose()
