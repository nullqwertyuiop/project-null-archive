import asyncio
import math
import os
import re
import youtube_dl
from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional, Union

import aiohttp
import qrcode
from PIL import Image as IMG
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage, FriendMessage
from graia.ariadne.exception import RemoteException
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Plain
from graia.ariadne.model import Friend, UploadMethod
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
from loguru import logger

from sagiri_bot.core.app_core import AppCore
from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import Normal
from sagiri_bot.utils import BuildImage

saya = Saya.current()
channel = Channel.current()
core: AppCore = AppCore.get_core_instance()
config = core.get_config()

channel.name("TwitterPreview")
channel.author("nullqwertyuiop")
channel.description("推特链接预览")


# @channel.use(ListenerSchema(listening_events=[FriendMessage]))
async def twitter_preview_handler(app: Ariadne, message: MessageChain, friend: Friend):
    if result := await TwitterPreview.handle(app, message, friend=friend):
        await MessageSender(result.strategy).send(app, result.message, message, friend, friend)


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def twitter_preview_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await TwitterPreview.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class TwitterPreview(AbstractHandler):
    __name__ = "TwitterPreview"
    __description__ = ""
    __usage__ = ""
    __disabled = False
    __bearer = config.functions['twitter']['bearer']
    if __bearer == "bearer":
        logger.error("未配置推特 Bearer，请自行申请并配置")
        __disabled = True
    headers = {'Authorization': f'Bearer {__bearer}'}
    session = aiohttp.ClientSession(headers=headers)

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if "t.co" in message.asDisplay() or "twitter.com" in message.asDisplay():
            if not TwitterPreview.__disabled:
                return MessageItem(MessageChain.create(
                    await TwitterPreview.get_tweet(app, message.asDisplay(), group if group else friend)
                ), Normal())
        else:
            return None

    @staticmethod
    async def get_bytes(link: str) -> Optional[bytes]:
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as resp:
                if resp.status == 200:
                    return await resp.read()

    @staticmethod
    async def func(app: Ariadne, resp: dict, target: Union[Group, Friend]):
        font = f"{os.getcwd()}/statics/fonts/NotoSansCJKsc-Medium.ttf"
        canvas_width = 700
        canvas_height = 0

        if avatar := await TwitterPreview.get_bytes(resp["includes"]["users"][0]["profile_image_url"]):
            avatar = BuildImage(200, 100, background=BytesIO(avatar))
        else:
            avatar = BuildImage(200, 100, color=(0, 0, 0))
        avatar.circle_new()
        name = BuildImage(700, 50, font=font, font_size=30, color="white")
        _name_canvas = BuildImage(700 - 150 - 30, 50, font=font, font_size=30, color="white")
        _name = resp["includes"]["users"][0]['name']
        if _name_canvas.check_font_size(_name):
            _name = ""
            for _char in resp["includes"]["users"][0]['name']:
                if _name_canvas.check_font_size(_name + _char + "..."):
                    break
                _name += _char
            _name += "..."
        name.text((0, 0), _name, (0, 0, 0))
        user = BuildImage(700, 150, font=font, font_size=25, color="white")
        await user.apaste(avatar, (30, 25), True)
        await user.apaste(name, (150, 38))
        await user.atext((150, 85), f"@{resp['includes']['users'][0]['username']}", (127, 127, 127))
        canvas_height += user.h

        line_template = BuildImage(canvas_width - 50 * 3, 60, font=font, font_size=40)
        text = resp["data"][0]["text"]
        if "entities" in resp["data"][0].keys():
            for _url in resp["data"][0]["entities"]["urls"]:
                text = text.replace(_url["url"], "").strip()
        text_parts = text.split("\n")
        lines = []
        for index, text_part in enumerate(text_parts):
            line = ""
            for _index, char in enumerate(text_part):
                if not line_template.check_font_size(line):
                    line += char
                    if _index == (len(text_part) - 1):
                        lines.append(line)
                    continue
                lines.append(line)
                line = ""
                line += char
        body_text = None
        if lines != [""]:
            body_text = BuildImage(
                line_template.w + 50, (line_template.h + 5) * len(lines) + 20, font=font, font_size=40)
            for index, line in enumerate(lines):
                line_canvas = BuildImage(
                    line_template.w + 50, line_template.h, font=font, font_size=40)
                await line_canvas.atext((0, 0), line, (0, 0, 0), "by_height")
                await body_text.apaste(line_canvas, (0, (line_template.h + 5) * index - 5))
        canvas_height += body_text.h if body_text else 0

        media = None
        if "media" in resp['includes'].keys():
            media_list = []
            gap = BuildImage(canvas_width - 30 * 2, 30, is_alpha=True)
            offset = 0
            for _index, _media in enumerate(resp['includes']['media']):
                if _media['type'] == 'photo':
                    if photo := await TwitterPreview.get_bytes(_media["url"]):
                        photo = BytesIO(photo)
                        _photo = IMG.open(photo)
                        photo = BuildImage(
                            _photo.width, _photo.height, background=photo)
                        _w = canvas_width - 30 * 2
                        _h = math.ceil(_photo.height * (_w / _photo.width))
                        await photo.aresize(w=_w, h=_h)
                        await photo.acircle_corner(30)
                        if _index != 0:
                            media_list.append(gap)
                        media_list.append(photo)
                if _media['type'] == 'video':
                    if video := await TwitterPreview.get_bytes(_media["preview_image_url"]):
                        video = BytesIO(video)
                        _video = IMG.open(video)
                        while True:
                            try:
                                _vid_url = resp["data"][0]["entities"]["urls"][_index + offset]["expanded_url"]
                                if re.match(
                                        "(?:https?:\/\/)?(?:www\.)?twitter\.com\/[\w\d]+\/status\/(\d+)\/video\/\d+",
                                        _vid_url
                                ):
                                    break
                                offset += 1
                            except KeyError:
                                _vid_url = None
                        if _vid_url:
                            video_bytes = await TwitterPreview.aget_video(_vid_url)
                            if video_bytes:
                                try:
                                    await app.uploadFile(
                                        data=video_bytes[0],
                                        method=UploadMethod.Group,
                                        target=target,
                                        name=video_bytes[1]
                                    )
                                except RemoteException as e:
                                    if "upload check_security fail" in str(e):
                                        await app.sendMessage(
                                            target=target,
                                            message=MessageChain.create([
                                                Plain(text="安全检查失败，无法发送视频文件")
                                            ])
                                        )
                                    else:
                                        await app.sendMessage(
                                            target=target,
                                            message=MessageChain.create([
                                                Plain(text="无法发送视频文件，请检查群文件是否有足够空间或是否允许上传")
                                            ])
                                        )
                                    logger.error(e)
                                except Exception as e:
                                    logger.error(e)
                        video = BuildImage(
                            _video.width, _video.height, background=video)
                        _w = canvas_width - 30 * 2
                        _h = math.ceil(_video.height * (_w / _video.width))
                        await video.aresize(w=_w, h=_h)
                        await video.acircle_corner(30)
                        video_icon = BuildImage(
                            150, 150, is_alpha=True, background=f"{os.getcwd()}/statics/twitter/video.png")
                        await video_icon.acircle_corner(30)
                        await video.apaste(video_icon, alpha=True, center_type="center")
                        if _index != 0:
                            media_list.append(gap)
                        media_list.append(video)
            media = BuildImage(canvas_width - 30 * 2,
                               sum([m.h for m in media_list]))
            _h = 0
            for _media in media_list:
                await media.apaste(_media, (0, _h), True, "by_width")
                _h += _media.h
        canvas_height += media.h if media else 0

        time = BuildImage(
            656, 656, background=f"{os.getcwd()}/statics/twitter/time.png")
        reply = BuildImage(
            656, 656, background=f"{os.getcwd()}/statics/twitter/comment.png")
        retweet = BuildImage(
            656, 656, background=f"{os.getcwd()}/statics/twitter/retweet.png")
        like = BuildImage(
            656, 656, background=f"{os.getcwd()}/statics/twitter/like.png")
        await time.aresize(w=30, h=30)
        await reply.aresize(w=30, h=30)
        await retweet.aresize(w=30, h=30)
        await like.aresize(w=30, h=30)
        gap = BuildImage(700, 25, is_alpha=True)
        icon_images = [time, gap, reply, gap, retweet, gap, like]
        icon_data = [
            (datetime.strptime(
                resp['data'][0]['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ") + timedelta(hours=8)
             ).strftime("%H:%M:%S · %Y年%m月%d日"),
            "",
            resp['data'][0]['public_metrics']['reply_count'],
            "",
            resp['data'][0]['public_metrics']['retweet_count'],
            "",
            resp['data'][0]['public_metrics']['like_count']
        ]
        icons_height = sum([i.h for i in icon_images])
        icons = BuildImage(700, icons_height, font=font, font_size=25, color="white")
        _h = 0
        for index, icon in enumerate(zip(icon_images, icon_data)):
            await icons.apaste(icon[0], (30, _h), True)
            await icons.atext((80, _h - 5), str(icon[1]), (127, 127, 127))
            _h += icon[0].h
        watermark = BuildImage(
            656, 656, background=f"{os.getcwd()}/statics/twitter/watermark.png")
        qr = qrcode.QRCode(border=0)
        qr.add_data(f"https://twitter.com/{resp['includes']['users'][0]['username']}/status/{resp['data'][0]['id']}")
        qr.make(fit=True)
        qr.make_image(fill_color=(127, 127, 127)).resize((140, 140)).save(f"temp-{resp['data'][0]['id']}.png",
                                                                          format="png")
        qr = BuildImage(140, 140, background=f"{os.getcwd()}/temp-{resp['data'][0]['id']}.png")
        os.remove(f"{os.getcwd()}/temp-{resp['data'][0]['id']}.png")
        await qr.aresize(w=140, h=140)
        await watermark.aresize(w=140, h=140)
        canvas_height += 30 + 25 + icons.h + 30
        canvas = BuildImage(canvas_width, canvas_height, color=(255, 255, 255))
        await canvas.apaste(user, (0, 0))
        _h = user.h
        if body_text:
            await canvas.apaste(body_text, (50, _h))
            _h += body_text.h
        if media:
            await canvas.apaste(media, (30, _h), True)
            _h += media.h
        _h += 30
        await canvas.aline((0, _h, 700, _h), (191, 191, 191))
        _h += 25
        await canvas.apaste(icons, (0, _h))
        _h += 55
        await canvas.apaste(watermark, (canvas_width - 140 - 25, _h), True)
        await canvas.apaste(qr, (canvas_width - 165 - 140 - 25, _h), center_type='by_width')
        return [Image(data_bytes=canvas.pic2bytes())]

    @staticmethod
    async def get_tweet(app: Ariadne, param: str, target: Union[Group, Friend]):
        if short_match := re.compile(r"(?:https?:\/\/)?(?:www\.)?(t\.co\/[ -~]+)").search(param):
            param = short_match.group(1)
            if not (param.startswith("http://") or param.startswith("https://")):
                param = "https://" + param
            async with aiohttp.ClientSession(headers=None) as session:
                async with session.get(param) as res:
                    if res.status == 200:
                        param = str(res.url)
                    else:
                        return None
        if match := re.compile(r"(?:https?:\/\/)?(?:www\.)?twitter\.com\/[\w\d]+\/status\/(\d+)").search(param):
            status_id = match.group(1)
        else:
            return None
        async with aiohttp.ClientSession(headers=TwitterPreview.headers) as session:
            async with session.get(
                    f"https://api.twitter.com/2/tweets?ids={status_id}&"
                    f"tweet.fields=text,created_at,public_metrics,entities&"
                    f"expansions=attachments.media_keys,author_id&"
                    f"media.fields=preview_image_url,duration_ms,type,url&"
                    f"user.fields=profile_image_url") as res:
                if res.status == 200:
                    _resp = await res.json()
                    if "error" not in _resp.keys():
                        resp = _resp
                    else:
                        return None
                else:
                    return None
        return await TwitterPreview.func(app, resp, target)

    @staticmethod
    def get_video_info(link: str):
        ydl = youtube_dl.YoutubeDL()
        with ydl:
            result = ydl.extract_info(link, download=False)
        return result

    @staticmethod
    async def aget_video(link: str):
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, TwitterPreview.get_video_info, link)
        if video := await TwitterPreview.get_bytes(info['url']):
            return [video, f"{info['display_id']}.{info['ext']}"]
