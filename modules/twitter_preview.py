import asyncio
import math
import os
import re
from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional, Union

import aiohttp
import qrcode
import youtube_dl
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
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.utils import BuildImage, HelpPage, HelpPageElement
from statics.emoji.emoji import emoji_list

saya = Saya.current()
channel = Channel.current()
core: AppCore = AppCore.get_core_instance()
config = core.get_config()
proxy = config.proxy if config.proxy != "proxy" else ''

channel.name("TwitterPreview")
channel.author("nullqwertyuiop")
channel.description("推特链接预览")


@channel.use(ListenerSchema(listening_events=[FriendMessage]))
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
    __headers = {'Authorization': f'Bearer {__bearer}'}

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if "t.co" in message.asDisplay() or "twitter.com" in message.asDisplay():
            if not TwitterPreview.__disabled:
                await TwitterPreview.get_tweet(app, message.asDisplay(), group if group else friend)
                return None
        else:
            return None

    @staticmethod
    async def get_bytes(link: str) -> Optional[bytes]:
        async with aiohttp.ClientSession() as session:
            async with session.get(link, proxy=proxy) as resp:
                if resp.status == 200:
                    return await resp.read()

    @staticmethod
    async def func(app: Ariadne, resp: dict, target: Union[Group, Friend] = None, manual: bool = True):
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
        _name_emoji = []
        _name = ""
        if _name_canvas.check_font_size(TwitterPreview.replace_emoji(resp["includes"]["users"][0]['name'])):
            for _char in resp["includes"]["users"][0]['name']:
                if TwitterPreview.is_emoji(_char):
                    _name_emoji.append((_name_canvas.font.getsize(
                        _name)[0], _name_canvas.font.getsize("　")[0], ord(_char)))
                    _char = "　"
                if _name_canvas.check_font_size(_name + _char + "..."):
                    break
                _name += _char
            _name += "..."
        else:
            for _char in resp["includes"]["users"][0]['name']:
                if TwitterPreview.is_emoji(_char):
                    _name_emoji.append((_name_canvas.font.getsize(
                        _name)[0], _name_canvas.font.getsize("　")[0], ord(_char)))
                    _char = "　"
                _name += _char
        await name.atext((0, 0), _name, (0, 0, 0))
        for _emoji in _name_emoji:
            file = f"{os.getcwd()}/statics/emoji/{_emoji[2]}.png"
            if os.path.exists(file):
                emoji = IMG.open(file).convert("RGBA")
            else:
                continue
            location = (_emoji[0], 5)
            size = min(_name_canvas.font.getsize("　"))
            emoji = emoji.resize((size, size), IMG.ANTIALIAS)
            name.markImg.paste(emoji, (location), mask=emoji)
        user = BuildImage(700, 150, font=font, font_size=25, color="white")
        await user.apaste(avatar, (30, 25), True)
        await user.apaste(name, (150, 38))
        await user.atext((150, 85), f"@{resp['includes']['users'][0]['username']}", (127, 127, 127))
        canvas_height += user.h

        line_template = BuildImage(canvas_width - 50 * 3, 60, font=font, font_size=40)
        text = resp["data"][0]["text"]
        if "entities" in resp["data"][0].keys():
            if "urls" in resp["data"][0]["entities"].keys():
                for _url in resp["data"][0]["entities"]["urls"]:
                    text = text.replace(_url["url"], "").strip()
        text_parts = text.split("\n")
        lines = []
        _lines_emoji = [[]]
        for index, text_part in enumerate(text_parts):
            line = ""
            for _index, char in enumerate(text_part):
                while len(_lines_emoji) < len(lines):
                    _lines_emoji.append([])
                emoji = False
                _emoji = None
                if TwitterPreview.is_emoji(char):
                    emoji = True
                    _emoji = ord(char)
                    char = "　"
                if not line_template.check_font_size(line):
                    if _index == (len(text_part) - 1):
                        if emoji:
                            _lines_emoji[len(lines)].append(
                                (
                                    line_template.font.getsize(line)[0],
                                    line_template.font.getsize("　")[0],
                                    _emoji
                                )
                            )
                        line += char
                        lines.append(line)
                        _lines_emoji.append([])
                        continue
                    if emoji:
                        _lines_emoji[len(lines)].append(
                            (
                                line_template.font.getsize(line)[0],
                                line_template.font.getsize("　")[0],
                                _emoji
                            )
                        )
                    line += char
                    continue
                _lines_emoji.append([])
                if emoji:
                    _lines_emoji[-1].append(
                        (
                            line_template.font.getsize(line)[0],
                            line_template.font.getsize("　")[0],
                            _emoji
                        )
                    )
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
                for _emoji in _lines_emoji[index]:
                    if _emoji:
                        file = f"{os.getcwd()}/statics/emoji/{_emoji[2]}.png"
                        if os.path.exists(file):
                            emoji = IMG.open(file).convert("RGBA")
                        else:
                            continue
                        location = (_emoji[0], 10)
                        size = min(line_canvas.font.getsize("　"))
                        emoji = emoji.resize((size, size), IMG.ANTIALIAS)
                        line_canvas.markImg.paste(emoji, location, mask=emoji)
                await line_canvas.atext((0, 0), line, (0, 0, 0), "by_height")
                await body_text.apaste(line_canvas, (0, (line_template.h + 5) * index - 5))
        canvas_height += body_text.h if body_text else 0

        media = None
        media_bytes = None
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
                            media_bytes = await TwitterPreview.aget_video(_vid_url)
                        video = BuildImage(
                            _video.width, _video.height, background=video)
                        _w = canvas_width - 30 * 2
                        _h = math.ceil(_video.height * (_w / _video.width))
                        await video.aresize(w=_w, h=_h)
                        await video.acircle_corner(30)
                        video_icon = BuildImage(
                            150, 150, is_alpha=True, background=f"{os.getcwd()}/statics/twitter/video.png")
                        await video.apaste(video_icon, alpha=True, center_type="center")
                        if _index != 0:
                            media_list.append(gap)
                        media_list.append(video)
                if _media['type'] == 'animated_gif':
                    if gif := await TwitterPreview.get_bytes(_media["preview_image_url"]):
                        gif = BytesIO(gif)
                        _gif = IMG.open(gif)
                        while True:
                            try:
                                _gif_url = resp["data"][0]["entities"]["urls"][_index + offset]["expanded_url"]
                                if re.match(
                                        "(?:https?:\/\/)?(?:www\.)?twitter\.com\/[\w\d]+\/status\/(\d+)\/photo\/\d+",
                                        _gif_url
                                ):
                                    break
                                offset += 1
                            except KeyError:
                                _gif_url = None
                        if _gif_url:
                            media_bytes = (await TwitterPreview.aget_video(_gif_url)) if manual else None
                        gif = BuildImage(
                            _gif.width, _gif.height, background=gif)
                        _w = canvas_width - 30 * 2
                        _h = math.ceil(_gif.height * (_w / _gif.width))
                        await gif.aresize(w=_w, h=_h)
                        await gif.acircle_corner(30)
                        gif_icon = BuildImage(
                            150, 150, is_alpha=True, background=f"{os.getcwd()}/statics/twitter/gif.png")
                        await gif.apaste(gif_icon, alpha=True, center_type="center")
                        if _index != 0:
                            media_list.append(gap)
                        media_list.append(gif)
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

        if not manual:
            return canvas
        else:
            await app.sendMessage(target, MessageChain.create([
                Image(data_bytes=canvas.pic2bytes())
            ]))
            if media_bytes:
                msg = None
                no_caching = False
                try:
                    await app.uploadFile(
                        data=media_bytes[0],
                        method=UploadMethod.Group if isinstance(target, Group) else UploadMethod.Friend,
                        target=target,
                        name=media_bytes[1]
                    )
                    no_caching = True
                except RemoteException as e:
                    if "upload check_security fail" in str(e):
                        msg = [Plain(text="安全检查失败，无法发送媒体文件")]
                    else:
                        msg = [Plain(text="无法发送媒体文件，请检查群文件是否有足够空间或是否允许上传")]
                    logger.error(e)
                except NotImplementedError:
                    msg = [Plain(text="暂不支持在此上传媒体文件")]
                except Exception as e:
                    msg = [Plain(text="因遭遇其他错误无法发送媒体文件")]
                    logger.error(e)
                finally:
                    if not no_caching:
                        if link := TwitterPreview.store_media(media_bytes):
                            msg.append(Plain(text=f"\n媒体文件已缓存至 {link}"))
                    if msg:
                        await app.sendMessage(
                            target=target,
                            message=MessageChain.create(msg)
                        )

    @staticmethod
    def store_media(media_bytes: list):
        try:
            hashed = hash(media_bytes[0])
            if not os.path.isdir(f'/www/wwwroot/cdn.nullqwertyuiop.me/cache'):
                os.mkdir(f'/www/wwwroot/cdn.nullqwertyuiop.me/cache')
            if not os.path.isdir(f'/www/wwwroot/cdn.nullqwertyuiop.me/cache/{hashed}'):
                os.mkdir(f'/www/wwwroot/cdn.nullqwertyuiop.me/cache/{hashed}')
            webroot = f'/www/wwwroot/cdn.nullqwertyuiop.me/cache/{hashed}/'
            web = f'cdn.nullqwertyuiop.me/cache/{hashed}/'
            with open(webroot + media_bytes[1], 'wb') as f:
                f.write(media_bytes[0])
                return web + media_bytes[1]
        except Exception as e:
            logger.error(e)
            return None

    @staticmethod
    async def get_tweet(app: Ariadne, message: str, target: Union[Group, Friend] = None, manual: bool = True):
        if manual:
            requested_url = []
            if short_match := re.findall(r"(?:https?:\/\/)?(?:www\.)?(t\.co\/[a-zA-Z0-9_.-]{10})", message):
                for short_link in short_match:
                    if not (short_link.startswith("http://") or short_link.startswith("https://")):
                        short_link = "https://" + short_link
                    async with aiohttp.ClientSession(headers=None) as session:
                        async with session.get(short_link, proxy=proxy) as res:
                            if res.status == 200:
                                link = str(res.url)
                                if re.match(r"(?:https?:\/\/)?(?:www\.)?twitter\.com\/[\w\d]+\/status\/\d+", link):
                                    requested_url.append(link)
                                else:
                                    continue
                            else:
                                continue
            if match := re.findall(r"(?:https?:\/\/)?(?:www\.)?twitter\.com\/[\w\d]+\/status\/\d+", message):
                for link in match:
                    requested_url.append(link)
            if not requested_url:
                return None
            if len(requested_url) > 1:
                await app.sendMessage(target, MessageChain.create([
                    Plain(text=f"收到 {len(requested_url)} 条推特链接，开始解析。")
                ]))
            for link in requested_url:
                if match := re.compile(r"(?:https?:\/\/)?(?:www\.)?twitter\.com\/[\w\d]+\/status\/(\d+)").search(link):
                    status_id = match.group(1)
                else:
                    continue
                async with aiohttp.ClientSession(headers=TwitterPreview.__headers) as session:
                    async with session.get(
                            f"https://api.twitter.com/2/tweets?ids={status_id}"
                            f"&tweet.fields=text,created_at,public_metrics,entities"
                            f"&expansions=attachments.media_keys,author_id"
                            f"&media.fields=preview_image_url,duration_ms,type,url"
                            f"&user.fields=profile_image_url",
                            proxy=proxy
                    ) as res:
                        if res.status == 200:
                            _resp = await res.json()
                            if "errors" in _resp.keys():
                                await app.sendMessage(target, MessageChain.create([
                                    Plain(text=f"尝试取得 {link} 内容时出错")
                                ]))
                                continue
                            resp = _resp
                        else:
                            await app.sendMessage(target, MessageChain.create([
                                Plain(text=f"尝试取得 {link} 内容时出错，错误代码为 {res.status}")
                            ]))
                            continue
                await TwitterPreview.func(app, resp, target)
        else:
            if match := re.compile(r"(?:https?:\/\/)?(?:www\.)?twitter\.com\/[\w\d]+\/status\/(\d+)").search(message):
                status_id = match.group(1)
            else:
                return None
            async with aiohttp.ClientSession(headers=TwitterPreview.__headers) as session:
                async with session.get(
                        f"https://api.twitter.com/2/tweets?ids={status_id}"
                        f"&tweet.fields=text,created_at,public_metrics,entities"
                        f"&expansions=attachments.media_keys,author_id"
                        f"&media.fields=preview_image_url,duration_ms,type,url"
                        f"&user.fields=profile_image_url",
                        proxy=proxy
                ) as res:
                    if res.status == 200:
                        _resp = await res.json()
                        if "errors" in _resp.keys():
                            return None
                        resp = _resp
                    else:
                        return None
            return await TwitterPreview.func(app, resp, target, manual=False)

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

    @staticmethod
    def is_emoji(char):
        if char in emoji_list:
            return True
        else:
            return False

    @staticmethod
    def replace_emoji(string):
        result = ""
        for char in string:
            if TwitterPreview.is_emoji(char):
                result += "　"
            else:
                result += char
        return result


class TwitterPreviewHelp(HelpPage):
    __description__ = "推特链接解析"
    __trigger__ = "发送链接自动解析"
    __category__ = "utility"
    __switch__ = None
    __icon__ = "twitter"

    def __init__(self, group: Group = None, member: Member = None, friend: Friend = None):
        super().__init__()
        self.__help__ = None
        self.group = group
        self.member = member
        self.friend = friend

    async def compose(self):
        self.__help__ = [
            HelpPageElement(icon=self.__icon__, text="推特链接解析", is_title=True),
            HelpPageElement(text="识别消息中的推特链接并自动生成该链接对应推文的预览图"),
            HelpPageElement(icon="check-all", text="已全局开启"),
            HelpPageElement(icon="alert", text="暂不支持手动关闭"),
            HelpPageElement(icon="alert-circle", text="请勿使用本功能渲染不适合的内容，否则将永久撤回本功能使用权限"),
            HelpPageElement(icon="lightbulb-on", text="使用示例：\n直接发送链接即可"),
            HelpPageElement(icon="api", text="本功能依赖 Twitter v2 API，使用时请注意频率限制")
        ]
        super().__init__(self.__help__)
        return await super().compose()
