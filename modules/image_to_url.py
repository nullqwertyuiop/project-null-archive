import os
import re
from io import BytesIO
from typing import Union

from PIL import Image as IMG
from graia.ariadne.app import Ariadne, Friend
from graia.ariadne.event.message import Group, Member, GroupMessage, FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain, Image
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema

from SAGIRIBOT.Handler.Handler import AbstractHandler
from SAGIRIBOT.MessageSender.MessageItem import MessageItem
from SAGIRIBOT.MessageSender.MessageSender import GroupMessageSender, FriendMessageSender
from SAGIRIBOT.MessageSender.Strategy import GroupStrategy, QuoteSource, FriendStrategy, StrategyType
from SAGIRIBOT.decorators import switch, blacklist

saya = Saya.current()
channel = Channel.current()


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def image_to_url_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await ImageToURLHandler.handle(app, message, group=group, member=member, strategy=GroupStrategy()):
        await GroupMessageSender(result.strategy).send(app, result.message, message, group, member)


@channel.use(ListenerSchema(listening_events=[FriendMessage]))
async def image_to_url_handler(app: Ariadne, message: MessageChain, friend: Friend):
    if result := await ImageToURLHandler.handle(app, message, friend=friend, strategy=FriendStrategy()):
        await FriendMessageSender(result.strategy).send(app, result.message, message, friend)


class ImageToURLHandler(AbstractHandler):
    __name__ = "ImageToURLHandler"
    __description__ = "图片转URL Handler"
    __usage__ = "None"
    func_switch = {}

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, strategy: StrategyType, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if friend:
            if message.asDisplay() in ("开启图片转链接", "开启图床"):
                if friend.id in ImageToURLHandler.func_switch.keys():
                    if ImageToURLHandler.func_switch[friend.id]['status']:
                        return MessageItem(MessageChain.create([Plain(text="已开启图床，无需重复开启。")]),
                                           QuoteSource(FriendStrategy()))
                    else:
                        ImageToURLHandler.func_switch[friend.id]['status'] = True
                        return MessageItem(MessageChain.create([Plain(text="已开启图床。")]),
                                           QuoteSource(FriendStrategy()))
                ImageToURLHandler.func_switch.update(
                    {friend.id:
                        {"status": True}}
                )
                return MessageItem(MessageChain.create([Plain(text="已开启图床。")]),
                                   QuoteSource(FriendStrategy()))
            elif message.asDisplay() in ("关闭图片转链接", "关闭图床"):
                if friend.id in ImageToURLHandler.func_switch.keys():
                    if ImageToURLHandler.func_switch[friend.id]['status']:
                        ImageToURLHandler.func_switch[friend.id]['status'] = False
                        return MessageItem(MessageChain.create([Plain(text="已关闭图床。")]),
                                           QuoteSource(FriendStrategy()))
                    else:
                        return MessageItem(MessageChain.create([Plain(text="已关闭图床，无需重复关闭。")]),
                                           QuoteSource(FriendStrategy()))
                return MessageItem(MessageChain.create([Plain(text="未开启图床。")]), QuoteSource(FriendStrategy()))
            if message.has(Image):
                if friend.id in ImageToURLHandler.func_switch:
                    if ImageToURLHandler.func_switch[friend.id]['status']:
                        return MessageItem(MessageChain.create(
                            await ImageToURLHandler.get_image(message.get(Image), friend)
                        ), QuoteSource(strategy))
        else:
            return None

    @staticmethod
    async def get_image(images: list, user: Union[Member, Friend], webroot: str = None):
        if not os.path.isdir('/www/wwwroot/cdn.nullqwertyuiop.me/cdn/'):
            os.mkdir('/www/wwwroot/cdn.nullqwertyuiop.me/cdn/')
        if not webroot:
            webroot = '/www/wwwroot/cdn.nullqwertyuiop.me/cdn/'
        chain = [Plain(text=f"图床链接：")]
        log_file = open(f"{webroot}log.log", "a+")
        for image in images:
            # async with aiohttp.ClientSession() as session:
            #     async with session.get(url=image.url) as resp:
            #         img_content = await resp.read()
            # img_suffix = image.imageId.split('.').pop()
            img_suffix = re.compile('"imageId": "{.*}.(.{1,5})"').search(image.asPersistentString()).group(1)
            img_suffix = img_suffix if img_suffix != 'mirai' else 'png'
            img = IMG.open(BytesIO(await image.get_bytes()))
            save_path = os.path.join(webroot, f"{image.uuid}.{img_suffix}")
            img.save(save_path)
            chain.append(
                Plain(text=f"\n{webroot.split('/', maxsplit=3)[-1]}{image.uuid}.{img_suffix}")
            )
            log_file.write(f"{user.id}: {image.uuid}.{img_suffix}\n")
        log_file.close()
        return chain
