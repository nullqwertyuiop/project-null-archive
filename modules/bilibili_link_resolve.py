import json
import re
import time

import aiohttp
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage, FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain, Image, Xml
from graia.ariadne.model import Friend
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema

from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import QuoteSource
from sagiri_bot.orm.async_orm import Setting
from sagiri_bot.decorators import switch, blacklist
# from sagiri_bot.static_datas import bilibili_partition_dict
from sagiri_bot.utils import sec_format, group_setting, HelpPage, HelpPageElement
from modules.config import Config

saya = Saya.current()
channel = Channel.current()

channel.name("BilibiliLinkResolve")
channel.author("nullqwertyuiop")
channel.description("B站链接解析")


@channel.use(ListenerSchema(listening_events=[FriendMessage]))
async def bilibili_link_resolve_handler(app: Ariadne, message: MessageChain, friend: Friend):
    if result := await BilibiliLinkResolve.handle(app, message, friend=friend):
        await MessageSender(result.strategy).send(app, result.message, message, friend, friend)


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def bilibili_link_resolve_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await BilibiliLinkResolve.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class BilibiliLinkResolve(AbstractHandler):
    __name__ = "BilibiliLinkResolve"
    __description__ = "一个可以解析BiliBili小程序的Handler"
    __usage__ = "当群中有人分享时自动触发"
    fallback_config = "%封面%\n【标题】%标题%\n【UP主】%up%\n【播放量】%播放量%\n【点赞量】%点赞量%\n【简介】%简介%"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if match := re.findall("(?:http:|https:\/\/)?(?:[^.]+\.)?bilibili\.com\/video\/(?:BV|bv)([\w\d]{10})",
                               message.asDisplay()):
            if member and group:
                if not await group_setting.get_setting(group.id, Setting.bilibili_app_parse):
                    return None
            bv = "bv" + match[0]
            av = BilibiliLinkResolve.bv_to_av(bv)
            info = await BilibiliLinkResolve.get_info(av)
            return MessageItem(
                await BilibiliLinkResolve.generate_messagechain(info, group),
                QuoteSource()
            )
        elif match := re.findall("(?:http:|https:\/\/)?(?:[^.]+\.)?bilibili\.com\/video\/(?:AV|av)([\d]+)",
                                 message.asDisplay()):
            if member and group:
                if not await group_setting.get_setting(group.id, Setting.bilibili_app_parse):
                    return None
            av = match[0]
            info = await BilibiliLinkResolve.get_info(av)
            return MessageItem(
                await BilibiliLinkResolve.generate_messagechain(info, group),
                QuoteSource()
            )
        elif match := re.findall("((?:http:|https:\/\/)?(?:[^.]+\.)?b23\.tv\/[\w\d]+)", message.asDisplay()):
            if member and group:
                if not await group_setting.get_setting(group.id, Setting.bilibili_app_parse):
                    return None
            match = match[0]
            if not (match.startswith("http://") or match.startswith("https://")):
                match = "https://" + match
            async with aiohttp.ClientSession(headers=None) as session:
                async with session.get(match) as res:
                    if res.status == 200:
                        link = str(res.url)
            if match := re.findall("(?:http:|https:\/\/)?(?:[^.]+\.)?bilibili\.com\/video\/(?:BV|bv)([\w\d]{10})",
                                   link):
                bv = "bv" + match[0]
                av = BilibiliLinkResolve.bv_to_av(bv)
                info = await BilibiliLinkResolve.get_info(av)
                return MessageItem(
                    await BilibiliLinkResolve.generate_messagechain(info, group),
                    QuoteSource()
                )
            elif match := re.findall("(?:http:|https:\/\/)?(?:[^.]+\.)?bilibili\.com\/video\/(?:AV|av)([\d]+)",
                                     link):
                av = match[0]
                info = await BilibiliLinkResolve.get_info(av)
                return MessageItem(
                    await BilibiliLinkResolve.generate_messagechain(info, group),
                    QuoteSource()
                )
        elif xml := message.get(Xml):
            xml = xml[0].xml
            if match := re.findall("(?:http:|https:\/\/)?(?:[^.]+\.)?bilibili\.com\/video\/(?:BV|bv)([\w\d]{10})",
                                   message.asDisplay()):
                if member and group:
                    if not await group_setting.get_setting(group.id, Setting.bilibili_app_parse):
                        return None
                bv = "bv" + match[0]
                av = BilibiliLinkResolve.bv_to_av(bv)
                info = await BilibiliLinkResolve.get_info(av)
                return MessageItem(
                    await BilibiliLinkResolve.generate_messagechain(info, group),
                    QuoteSource()
                )
            elif match := re.findall("(?:http:|https:\/\/)?(?:[^.]+\.)?bilibili\.com\/video\/(?:AV|av)([\d]+)",
                                     message.asDisplay()):
                if member and group:
                    if not await group_setting.get_setting(group.id, Setting.bilibili_app_parse):
                        return None
                av = match[0]
                info = await BilibiliLinkResolve.get_info(av)
                return MessageItem(
                    await BilibiliLinkResolve.generate_messagechain(info, group),
                    QuoteSource()
                )
            elif url := re.compile(".*url=\"((http:|https:\/\/)?[^.]+\.bilibili\.com\/video\/(BV|bv).*)\" .*").search(
                    xml):
                if member and group:
                    if not await group_setting.get_setting(group.id, Setting.bilibili_app_parse):
                        return None
                url = url.group(1).split(" ", maxsplit=1)[0]
                bv = url.split("?")[0].split("/")[-1]
                av = BilibiliLinkResolve.bv_to_av(bv)
                info = await BilibiliLinkResolve.get_info(av)
                return MessageItem(
                    await BilibiliLinkResolve.generate_messagechain(info, group),
                    QuoteSource()
                )
            elif match := re.findall("((?:http:|https:\/\/)?(?:[^.]+\.)?b23\.tv\/[\w\d]+)", message.asDisplay()):
                if member and group:
                    if not await group_setting.get_setting(group.id, Setting.bilibili_app_parse):
                        return None
                match = match[0]
                if not (match.startswith("http://") or match.startswith("https://")):
                    match = "https://" + match
                async with aiohttp.ClientSession(headers=None) as session:
                    async with session.get(match) as res:
                        if res.status == 200:
                            link = str(res.url)
                if match := re.findall("(?:http:|https:\/\/)?(?:[^.]+\.)?bilibili\.com\/video\/(?:BV|bv)([\w\d]{10})",
                                       link):
                    bv = "bv" + match[0]
                    av = BilibiliLinkResolve.bv_to_av(bv)
                    info = await BilibiliLinkResolve.get_info(av)
                    return MessageItem(
                        await BilibiliLinkResolve.generate_messagechain(info, group),
                        QuoteSource()
                    )
                elif match := re.findall("(?:http:|https:\/\/)?(?:[^.]+\.)?bilibili\.com\/video\/(?:AV|av)([\d]+)",
                                         link):
                    av = match[0]
                    info = await BilibiliLinkResolve.get_info(av)
                    return MessageItem(
                        await BilibiliLinkResolve.generate_messagechain(info, group),
                        QuoteSource()
                    )
        else:
            return None

    @staticmethod
    async def get_info(av: int):
        bilibili_video_api_url = f"http://api.bilibili.com/x/web-interface/view?aid={av}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url=bilibili_video_api_url) as resp:
                result = (await resp.read()).decode('utf-8')
        result = json.loads(result)
        return result

    @staticmethod
    def bv_to_av(bv: str) -> int:
        table = 'fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF'
        tr = {}
        for i in range(58):
            tr[table[i]] = i
        s = [11, 10, 3, 8, 4, 6]
        xor = 177451812
        add = 8728348608
        r = 0
        for i in range(6):
            r += tr[bv[s[i]]] * 58 ** i
        return (r - add) ^ xor

    @staticmethod
    def av_to_bv(av: int) -> str:
        table = 'fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF'
        tr = {}
        for i in range(58):
            tr[table[i]] = i
        s = [11, 10, 3, 8, 4, 6]
        xor = 177451812
        add = 8728348608
        av = (av ^ xor) + add
        r = list('BV1  4 1 7  ')
        for i in range(6):
            r[s[i]] = table[av // 58 ** i % 58]
        return ''.join(r)

    @staticmethod
    async def generate_messagechain(info: dict, group: Group = None) -> MessageChain:
        if group:
            try:
                config = Config.group_config[group.id]["bilibili_link_resolve"]
            except KeyError:
                config = BilibiliLinkResolve.fallback_config
        else:
            config = BilibiliLinkResolve.fallback_config
        data = info["data"]
        chain_list = []

        async def replace_variable(text: str) -> str:
            try:
                text = text.replace("%标题%", str(data['title']))
                text = text.replace("%分区%",
                                    # str(bilibili_partition_dict[str(data['tid'])]['name'])
                                    str(data['tid'])
                                    )
                text = text.replace("%视频类型%", '原创' if data['copyright'] == 1 else '转载')
                text = text.replace("%投稿时间%", str(time.strftime('%Y-%m-%d', time.localtime(int(data['pubdate'])))))
                text = text.replace("%视频长度%", str(sec_format(data['duration'])))
                text = text.replace("%up%", str(data['owner']['name']))
                text = text.replace("%播放量%", str(data['stat']['view']))
                text = text.replace("%弹幕量%", str(data['stat']['danmaku']))
                text = text.replace("%评论量%", str(data['stat']['reply']))
                text = text.replace("%点赞量%", str(data['stat']['like']))
                text = text.replace("%投币量%", str(data['stat']['coin']))
                text = text.replace("%收藏量%", str(data['stat']['favorite']))
                text = text.replace("%转发量%", str(data['stat']['share']))
                text = text.replace("%简介%", str(data['desc'])).replace("\\n", "\n")
                text = text.replace("%av号%", "av" + str(data['aid']))
                text = text.replace("%bv号%", str(data['bvid']))
                text = text.replace("%链接%", f"https://www.bilibili.com/video/av{str(data['aid'])}")
            except Exception as err:
                print(err)
            return text

        try:
            if "%封面%" in config:
                first = True if config.startswith("%封面%") else False
                parsed_config = config.split("%封面%")
                img_url = data['pic']
                async with aiohttp.ClientSession() as session:
                    async with session.get(url=img_url) as resp:
                        img_content = await resp.read()
                cover = Image(data_bytes=img_content)
                chain_list.append(cover if first else None)
                for item in parsed_config[1:]:
                    chain_list.append(Plain(text=await replace_variable(item)))
            else:
                chain_list = [Plain(text=await replace_variable(config))]
        except Exception as e:
            return MessageChain.create([Plain(text="解析失败，请联系机器人管理员。"),
                                        Plain(text=str(e))])
        return MessageChain.create(chain_list)


class BilibiliLinkResolveHelp(HelpPage):
    __description__ = "B 站链接解析"
    __trigger__ = "发送链接自动解析"
    __category__ = "utility"
    __switch__ = Setting.bilibili_app_parse
    __icon__ = "link"

    def __init__(self, group: Group = None, member: Member = None, friend: Friend = None):
        super().__init__()
        self.__help__ = None
        self.group = group
        self.member = member
        self.friend = friend

    async def compose(self):
        if self.group or self.member:
            if not await group_setting.get_setting(self.group.id, self.__switch__):
                status = HelpPageElement(icon="toggle-switch-off", text="已关闭")
            else:
                status = HelpPageElement(icon="toggle-switch", text="已开启")
        else:
            status = HelpPageElement(icon="check-all", text="已全局开启")
        self.__help__ = [
            HelpPageElement(icon=self.__icon__, text="B 站链接解析", is_title=True),
            HelpPageElement(text="识别消息中的 B 站链接并自动解析该链接"),
            status,
            HelpPageElement(icon="pound-box", text="更改设置需要权限不记得多少级"),
            HelpPageElement(icon="lightbulb-on", text="使用示例：\n"
                                                      "直接发送 B 站链接即可"),
        ]
        super().__init__(self.__help__)
        return await super().compose()
