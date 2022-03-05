import os
import re
from io import BytesIO
from typing import Union

import aiohttp
from PIL import Image as IMG, ImageDraw, ImageFilter
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage, FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Image
from graia.ariadne.model import Friend
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema

from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import Normal
from sagiri_bot.utils import update_user_call_count_plus, UserCalledCount, HelpPage, HelpPageElement

saya = Saya.current()
channel = Channel.current()

channel.name("PNAvatarFunPic")
channel.author("nullqwertyuiop")
channel.description("头像处理")


@channel.use(ListenerSchema(listening_events=[FriendMessage]))
async def pn_avatar_fun_pic_handler(app: Ariadne, message: MessageChain, friend: Friend):
    if result := await PNAvatarFunPicHandler.handle(app, message, friend=friend):
        await MessageSender(result.strategy).send(app, result.message, message, friend, friend)


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def pn_avatar_fun_pic_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await PNAvatarFunPicHandler.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class PNAvatarFunPicHandler(AbstractHandler):
    __name__ = "PNAvatarFunPicHandler"
    __description__ = "一个可以生成头像相关趣味图的Handler"
    __usage__ = "在群中发送 `摸 @目标` 即可"

    @staticmethod
    def get_match_element(message: MessageChain) -> list:
        return [element for element in message.__root__ if isinstance(element, Image) or isinstance(element, At)]

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        message_text = message.asDisplay()
        if message_text.startswith("完美"):
            match_elements = PNAvatarFunPicHandler.get_match_element(message)
            if len(match_elements) >= 1:
                if member and group:
                    await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
                element = match_elements[0]
                return MessageItem(MessageChain.create([
                    await PNAvatarFunPicHandler.perfect(element.target if isinstance(element, At) else element.url)]
                ), Normal())
            elif re.match(r"完美 [0-9]+", message_text):
                if member and group:
                    await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
                return MessageItem(MessageChain.create([
                    await PNAvatarFunPicHandler.perfect(int(message_text[3:]))]
                ), Normal())
        elif message_text.startswith("3p"):
            match_elements = PNAvatarFunPicHandler.get_match_element(message)
            if len(match_elements) == 2:
                if member and group:
                    await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
                element1 = match_elements[0]
                element2 = match_elements[1]
                return MessageItem(MessageChain.create([await PNAvatarFunPicHandler.three_p([
                    element1.target if isinstance(element1, At) else element1.url,
                    member.id if member else friend.id,
                    element2.target if isinstance(element2, At) else element2.url
                ])]
                                                       ), Normal())
            elif len(match_elements) > 2:
                if member and group:
                    await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
                element1 = match_elements[0]
                element2 = match_elements[1]
                element3 = match_elements[2]
                return MessageItem(MessageChain.create([await PNAvatarFunPicHandler.three_p([
                    element1.target if isinstance(element1, At) else element1.url,
                    element2.target if isinstance(element2, At) else element2.url,
                    element3.target if isinstance(element3, At) else element3.url
                ])]
                                                       ), Normal())
            elif re.match(r"3p \d+ \d+(?: \d+)?", message_text):
                if member and group:
                    await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
                split = message_text[3:].split(" ")
                if len(split) == 2:
                    left = split[0]
                    middle = member.id if member else friend.id
                    right = split[1]
                elif len(split) == 3:
                    left = split[0]
                    middle = split[1]
                    right = split[2]
                else:
                    return None
                return MessageItem(MessageChain.create([
                    await PNAvatarFunPicHandler.three_p([int(left), int(middle), int(right)])]
                ), Normal())
        else:
            return None

    @staticmethod
    async def get_pil_avatar(image: Union[int, str]):
        if isinstance(image, int):
            url = f'http://q1.qlogo.cn/g?b=qq&nk={str(image)}&s=640'
        else:
            url = image
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url) as resp:
                img_content = await resp.read()
        return IMG.open(BytesIO(img_content)).convert("RGBA")

    @staticmethod
    async def get_circle_avatar(image: Union[int, str]):
        avatar = await PNAvatarFunPicHandler.get_pil_avatar(image)
        mask = IMG.new('L', avatar.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, avatar.size), fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(0))
        avatar.putalpha(mask)
        return avatar

    @staticmethod
    async def perfect(image: Union[int, str]) -> Image:
        avatar = await PNAvatarFunPicHandler.get_pil_avatar(image)
        perfect = IMG.open(f'{os.getcwd()}/statics/perfect.jpg')
        avatar = avatar.resize((190, 190), IMG.ANTIALIAS)
        perfect.paste(avatar, (206, 75))
        output = BytesIO()
        perfect.save(output, format='jpeg')
        return Image(data_bytes=output.getvalue())

    @staticmethod
    async def three_p(image: list) -> Image:
        left = await PNAvatarFunPicHandler.get_circle_avatar(image[0])
        mid = await PNAvatarFunPicHandler.get_circle_avatar(image[1])
        right = await PNAvatarFunPicHandler.get_circle_avatar(image[2])
        back = IMG.open(f'{os.getcwd()}/statics/3p.jpg')
        back.paste(left.resize((100, 100)), (120, 5), mask=left.resize((100, 100)))
        back.paste(mid.resize((100, 100)), (225, 30), mask=mid.resize((100, 100)))
        back.paste(right.resize((100, 100)), (350, 10), mask=right.resize((100, 100)))
        back.paste(mid.resize((240, 240)), (170, 310), mask=mid.resize((240, 240)))
        output = BytesIO()
        back.save(output, format='jpeg')
        return Image(data_bytes=output.getvalue())

    @staticmethod
    async def bear(image) -> Image:
        avatar = await PNAvatarFunPicHandler.get_circle_avatar(image)
        back = IMG.open(f'{os.getcwd()}/statics/bear.jpg')
        back.paste(avatar.resize((175, 175)), (285, 210), mask=avatar.resize((175, 175)))
        output = BytesIO()
        back.save(output, format='jpeg')
        return Image(data_bytes=output.getvalue())


class AvatarFunHelp(HelpPage):
    __description__ = "头像相关处理"
    __trigger__ = "亲/摸/贴/撕/完美/精神支柱 @目标"
    __category__ = "entertainment"
    __switch__ = None
    __icon__ = "account-circle"

    def __init__(self, group: Group = None, member: Member = None, friend: Friend = None):
        super().__init__()
        self.__help__ = None
        self.group = group
        self.member = member
        self.friend = friend

    async def compose(self):
        self.__help__ = [
            HelpPageElement(icon=self.__icon__, text="头像相关处理", is_title=True),
            HelpPageElement(text="根据请求生成对目标头像的趣味图像，支持使用 @ 或者图片"),
            HelpPageElement(icon="check-all", text="已全局开启"),
            HelpPageElement(icon="numeric-1-circle", text="支持 1 个目标的功能：\n"
                                                          "亲，摸，贴，撕，完美，精神支柱"),
            HelpPageElement(icon="numeric-2-circle", text="支持 2 个目标的功能：\n"
                                                          "亲，贴，3p"),
            HelpPageElement(icon="numeric-3-circle", text="支持 3 个目标的功能：\n"
                                                          "3p"),
            HelpPageElement(icon="lightbulb-on", text="使用示例：\n发送\"亲 [图片] @目标\"即可")
        ]
        super().__init__(self.__help__)
        return await super().compose()
