import asyncio
import threading
import time
import aiohttp
from graia.ariadne.message.parser.twilight import Twilight, Sparkle, FullMatch
from graia.ariadne.model import Friend
from loguru import logger

from graia.saya import Saya, Channel
from graia.ariadne.app import Ariadne
from graia.ariadne.exception import AccountMuted
from graia.broadcast.interrupt.waiter import Waiter
from graia.ariadne.message.chain import MessageChain
from graia.broadcast.interrupt import InterruptControl
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.ariadne.message.element import Source, Plain, At, Image
from graia.ariadne.event.message import Group, Member, GroupMessage, FriendMessage
from sqlalchemy import select

from modules.wallet import Wallet
from sagiri_bot.utils import group_setting, HelpPage, HelpPageElement
from sagiri_bot.core.app_core import AppCore
from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.message_sender.strategy import Normal, QuoteSource
from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.utils import update_user_call_count_plus
from sagiri_bot.orm.async_orm import Setting, UserCalledCount, orm, SignInReward
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender

saya = Saya.current()
channel = Channel.current()

channel.name("ImageSearch")
channel.author("SAGIRI-kawaii")
channel.description("一个可以以图搜图的插件，在群中发送 `搜图` 后，等待回应在30s内发送图片即可（多张图片只会搜索第一张）")

core = AppCore.get_core_instance()
bcc = core.get_bcc()
config = core.get_config()
proxy = config.proxy if config.proxy != "proxy" else ''


@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[Twilight(Sparkle([FullMatch("搜图")]))]
    )
)
async def image_searcher(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await ImageSearch.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class ImageSearch(AbstractHandler):
    """ 图片搜素Handler(saucenao) """
    __name__ = "ImageSearcher"
    __description__ = "一个可以以图搜图的插件"
    __usage__ = "在群中发送 `搜图` 后，等待回应在30s内发送图片即可（多张图片只会搜索第一张）"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if message.asDisplay() in ("搜图", "以图搜图", "搜圖", "以圖搜圖"):
            if member and group:
                await update_user_call_count_plus(group, member, UserCalledCount.search, "search")
                if not await group_setting.get_setting(group.id, Setting.img_search):
                    return MessageItem(MessageChain.create([
                        Plain(text='该功能已关闭，请阅读文档或者使用 "/contact" 联系机器人管理员开启。')
                    ]), Normal())
                try:
                    cost = await orm.fetchall(
                        select(
                            Setting.img_search_cost
                        ).where(Setting.group_id == group.id))
                    img_search_cost = 500 if not cost else cost[0][0]
                    wallet = await Wallet.get_balance(group, member)
                    if wallet - img_search_cost < 0:
                        return MessageItem(MessageChain.create([Plain(text=f"你没有足够多的硬币，搜图消耗 {img_search_cost} 枚硬币。")]),
                                           QuoteSource())
                    await app.sendGroupMessage(group, MessageChain.create([
                        At(member.id), Plain(f" 请在30秒内发送要搜索的图片。\n搜图消耗：{img_search_cost} 枚硬币。")
                    ]))
                except AccountMuted:
                    logger.error(f"Bot 在群 <{group.name}> 被禁言，无法发送！")
                    return None

                image_get = None
                message_received = None

                @Waiter.create_using_function([GroupMessage])
                def waiter(
                        event: GroupMessage, waiter_group: Group,
                        waiter_member: Member, waiter_message: MessageChain
                ):
                    nonlocal image_get
                    nonlocal message_received
                    if time.time() - start_time < 30:
                        if all([
                            waiter_group.id == group.id,
                            waiter_member.id == member.id,
                            len(waiter_message[Image]) == len(waiter_message.__root__) - 1
                        ]):
                            image_get = True
                            message_received = waiter_message
                            return event
                    else:
                        logger.warning("等待用户超时！ImageSearchHandler进程推出！")
                        return event

                inc = InterruptControl(bcc)
                start_time = time.time()
                await inc.wait(waiter)
                if image_get:
                    logger.success("收到用户图片，启动搜索进程！")
                    try:
                        await Wallet.charge(group, member, img_search_cost, "搜图")
                        await app.sendGroupMessage(
                            group,
                            await ImageSearch.search_image(message_received[Image][0], group),
                            quote=message_received[Source][0]
                        )
                    except AccountMuted:
                        logger.error(f"Bot 在群 <{group.name}> 被禁言，无法发送！")
                        pass

                return None
            else:
                return None
        else:
            return None

    @staticmethod
    async def search_image(img: Image, group: Group) -> MessageChain:
        # picture url
        pic_url = img.url

        url3 = f"https://saucenao.com/search.php?api_key={config.functions.get('saucenao_api_key')}&db=999" \
               f"&output_type=2&testmode=1&numres=10&url={pic_url} "

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
            async with session.get(url=url3, proxy=proxy) as resp:
                json_data = await resp.json()

        if json_data["header"]["status"] == -1:
            return MessageChain.create([
                Plain(text=f"错误：{json_data['header']['message']}")
            ])

        if json_data["header"]["status"] == -2:
            return MessageChain.create([
                Plain(text=f"错误：24小时内搜索次数到达上限。")
            ])

        if not json_data["results"]:
            return MessageChain.create([
                Plain(text="没有搜索到结果。")
            ])

        result = json_data["results"][0]
        header = result["header"]
        data = result["data"]
        long_remaining = json_data["header"]["long_remaining"]

        if await group_setting.get_setting(group.id, Setting.trusted):
            async with aiohttp.ClientSession() as session:
                async with session.get(url=header["thumbnail"], proxy=proxy) as resp:
                    img_content = await resp.read()

        similarity = header["similarity"]
        similarity_limit = float(await group_setting.get_setting(group.id, Setting.img_search_similarity))
        if float(similarity) < similarity_limit:
            return MessageChain.create([
                Plain(text=f"没有搜索到高于本群相似度阈值的图片。\n本群相似度阈值为 {similarity_limit}%。\n服务器 24 小时内可再搜索 {long_remaining} 次")
            ])
        data_str = f"搜索到如下结果：\n相似度：{similarity}%\n"
        for key in data.keys():
            if isinstance(data[key], list):
                data_str += (f"{key}:\n    " + "\n".join(data[key]) + "\n")
            else:
                data_str += f"{key}:\n    {data[key]}\n"
        if await group_setting.get_setting(group.id, Setting.trusted):
            return MessageChain.create([
                Image(data_bytes=img_content),
                Plain(text=f"\n{data_str}\n服务器 24 小时内可再搜索 {long_remaining} 次")
            ])
        else:
            return MessageChain.create([Plain(text=f"{data_str}\n服务器 24 小时内可再搜索 {long_remaining} 次")
                                        ])

    @staticmethod
    async def check_or_update_coin(member: Member, group: Group, check: bool):
        cost = await orm.fetchall(
            select(
                Setting.img_search_cost
            ).where(Setting.group_id == group.id))
        img_search_cost = 2 if not cost else cost[0][0]
        fetch = await orm.fetchall(
            select(SignInReward.coin
                   ).where(SignInReward.qq == member.id))
        if not fetch:
            fetch = [[0]]
        if check:
            if fetch[0][0] - img_search_cost < 0:
                return False
            return True
        if not check:
            await orm.insert_or_update(
                SignInReward,
                [SignInReward.qq == member.id],
                {
                    "qq": member.id,
                    "coin": fetch[0][0] - img_search_cost
                }
            )
            return None


class ImageSearchHelp(HelpPage):
    __description__ = "搜图"
    __trigger__ = "搜图"
    __category__ = 'utility'
    __icon__ = "image-search"

    def __init__(self, group: Group = None, member: Member = None, friend: Friend = None):
        super().__init__()
        self.__help__ = None
        self.group = group
        self.member = member
        self.friend = friend

    async def compose(self):
        if self.group or self.member:
            if not await group_setting.get_setting(self.group.id, Setting.img_search):
                status = HelpPageElement(icon="toggle-switch-off", text="已关闭")
            else:
                status = HelpPageElement(icon="toggle-switch", text="已开启")
        else:
            status = HelpPageElement(icon="close", text="暂不支持")
        self.__help__ = [
            HelpPageElement(icon=self.__icon__, text="搜图", is_title=True),
            HelpPageElement(text="查找给定图片的来源"),
            status,
            HelpPageElement(icon="cash", text="使用搜图需要消耗一定硬币数"),
            HelpPageElement(icon="alert", text="搜索所得结果相似度低于设定值时将被丢弃，此时仍会消耗硬币数"),
            HelpPageElement(icon="pound-box", text="更改设置需要管理员权限\n"
                                                   "发送\"打开搜图开关\"或者\"关闭搜图开关\"即可更改开关"),
            HelpPageElement(icon="lightbulb-on", text="使用示例：\n发送\"搜图\"，随后发送需要搜索的图片即可"),
            HelpPageElement(icon="api", text="本功能依赖 SauceNAO API，使用时请注意次数限制\n"
                                             "我的意思是，不要再用这个搜一些乱七八糟的表情包了")
        ]
        super().__init__(self.__help__)
        return await super().compose()
