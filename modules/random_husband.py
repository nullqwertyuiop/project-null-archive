import math
import re
from datetime import datetime
import os
import random

from io import BytesIO
from PIL import Image as IMG
from random import randrange
import aiohttp
from graia.saya import Saya, Channel
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.ariadne.message.element import Plain, Image
from graia.ariadne.event.message import Group, Member, GroupMessage
from sqlalchemy import select

from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.orm.async_orm import orm, RandomHusband, Setting, UserCalledCount
from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.message_sender.strategy import QuoteSource
from sagiri_bot.utils import update_user_call_count_plus, get_setting
from modules.WalletHandler import WalletHandler

saya = Saya.current()
channel = Channel.current()


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def template_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await RandomHusbandHandler.handle(app, message, group, member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class RandomHusbandHandler(AbstractHandler):
    __name__ = "RandomHusbandHandler"
    __description__ = "随机老公"
    __usage__ = "在群中发送随机老公即可"
    furry_pool = os.listdir(f"{os.getcwd()}/statics/random_husband/furry/")
    for index in range(len(furry_pool)):
        furry_pool[index] = f"{os.getcwd()}/statics/random_husband/furry/" + furry_pool[index]
    human_pool = os.listdir(f"{os.getcwd()}/statics/random_husband/human/")
    for index in range(len(human_pool)):
        human_pool[index] = f"{os.getcwd()}/statics/random_husband/human/" + human_pool[index]
    mixed_pool = furry_pool + human_pool

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group, member: Member):
        if message.asDisplay() in ("随机老公", "隨機老公"):
            if not await get_setting(group.id, Setting.random_husband):
                return MessageItem(MessageChain.create([Plain(text=f"随机老公模块已被禁用。")]),
                                   QuoteSource())
            await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
            return MessageItem(MessageChain.create(await RandomHusbandHandler.husband(member, group, "mixed")),
                               QuoteSource())
        elif message.asDisplay() in ("随机兽人老公", "隨機獸人老公"):
            if not await get_setting(group.id, Setting.random_husband):
                return MessageItem(MessageChain.create([Plain(text=f"随机老公模块已被禁用。")]),
                                   QuoteSource())
            await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
            return MessageItem(MessageChain.create(await RandomHusbandHandler.husband(member, group, "furry")),
                               QuoteSource())
        elif message.asDisplay() in ("随机人类老公", "隨機人類老公"):
            if not await get_setting(group.id, Setting.random_husband):
                return MessageItem(MessageChain.create([Plain(text=f"随机老公模块已被禁用。")]),
                                   QuoteSource())
            await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
            return MessageItem(MessageChain.create(await RandomHusbandHandler.husband(member, group, "human")),
                               QuoteSource())
        elif message.asDisplay() in ("十连老公", "十連老公"):
            if not await get_setting(group.id, Setting.ten_husband):
                return MessageItem(MessageChain.create([Plain(text=f"十连老公模块已被禁用。")]),
                                   QuoteSource())
            await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
            return MessageItem(MessageChain.create(await RandomHusbandHandler.get_ten(member, group, "mixed")),
                               QuoteSource())
        elif message.asDisplay() in ("十连兽人老公", "十連獸人老公"):
            if not await get_setting(group.id, Setting.ten_husband):
                return MessageItem(MessageChain.create([Plain(text=f"十连老公模块已被禁用。")]),
                                   QuoteSource())
            await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
            return MessageItem(MessageChain.create(await RandomHusbandHandler.get_ten(member, group, "furry")),
                               QuoteSource())
        elif message.asDisplay() in ("十连人类老公", "十連人類老公"):
            if not await get_setting(group.id, Setting.ten_husband):
                return MessageItem(MessageChain.create([Plain(text=f"十连老公模块已被禁用。")]),
                                   QuoteSource())
            await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
            return MessageItem(MessageChain.create(await RandomHusbandHandler.get_ten(member, group, "human")),
                               QuoteSource())
        elif re.match("\d+(?: )?(?:连|連)(獸人|兽人|人类|人類)?老公", message.asDisplay()):
            times = re.compile("(\d+)(?: )?(?:连|連)(獸人|兽人|人类|人類)?老公").search(message.asDisplay()).group(1)
            times = int(times)
            if times > 100:
                return MessageItem(MessageChain.create([Plain(text=f"不要贪心。")]),
                                   QuoteSource())
            if pool := re.compile("(\d+)(?: )?(?:连|連)(獸人|兽人|人类|人類)?老公").search(message.asDisplay()).group(2):
                pool_cord = {
                    "兽人": "furry",
                    "獸人": "furry",
                    "人类": "human",
                    "人類": "human"
                }
                pool = pool_cord[pool]
            else:
                pool = "mixed"
            return MessageItem(MessageChain.create(
                await RandomHusbandHandler.get_custom(member, group, pool, times)),
                               QuoteSource())
        else:
            return None

    @staticmethod
    async def husband(member: Member, group: Group, pool: str):
        if randrange(101) <= 2:
            return [Plain(text="老公竟是你自己！"),
                    Image(data_bytes=await RandomHusbandHandler.get_avatar(member.id, 100)),
                    Plain(text="开玩笑的，可以重新抽了。")]
        fetch = await orm.fetchall(
            select(
                RandomHusband.last_date,
                RandomHusband.last_file
            ).where(RandomHusband.qq == member.id,
                    RandomHusband.group == group.id,
                    RandomHusband.last_date == int(datetime.today().strftime('%Y%m%d'))))
        if fetch:
            try:
                husband = IMG.open(f"{os.getcwd()}/statics/random_husband/{fetch[0][1]}")
                husband = husband.resize((95 + randrange(11), 95 + randrange(11)))
                output = BytesIO()
                husband.save(output, format='png')
                text = "你今天已经抽过老公了！\n你今天抽到的是："
                return [Plain(text=text), Image(data_bytes=output.getvalue()), Plain(text=fetch[0][1].split("/")[-1])]
            except FileNotFoundError:
                return [Plain(text=f"出错，请联系机器人管理员。\n开玩笑的，你老公估摸着是被我删了。")]
        try:
            if pool == "mixed":
                choices = RandomHusbandHandler.mixed_pool
            elif pool == "human":
                choices = RandomHusbandHandler.human_pool
            else:
                choices = RandomHusbandHandler.furry_pool
            choice = random.sample(choices, 1)[0]
            husband = IMG.open(choice)
            file_name = choice.split("/")[-2:]
            f_name = file_name[0] + "/" + file_name[1]
            husband = husband.resize((95 + randrange(11), 95 + randrange(11)))
            await orm.insert_or_update(
                RandomHusband,
                [RandomHusband.qq == member.id, RandomHusband.group == group.id],
                {"group": group.id,
                 "qq": member.id,
                 "last_date": int(datetime.today().strftime('%Y%m%d')),
                 "last_file": f_name}
            )
            output = BytesIO()
            husband.save(output, format='png')
            return [Image(data_bytes=output.getvalue())]
        except Exception as e:
            return [Plain(text=f"出错，请联系机器人管理员。\n{e}")]

    @staticmethod
    async def get_avatar(uin: int, size: int):
        url = f'http://q1.qlogo.cn/g?b=qq&nk={str(uin)}&s=640'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url) as resp:
                img_content = await resp.read()
        img_content = IMG.open(BytesIO(img_content)).convert("RGB").resize((size, size), IMG.ANTIALIAS)
        output = BytesIO()
        img_content.save(output, format='jpeg')
        return output.getvalue()

    @staticmethod
    async def get_ten(member: Member, group: Group, pool: str):
        fetch = await orm.fetchall(
            select(
                Setting.ten_husband_cost,
                Setting.ten_husband_limit
            ).where(Setting.group_id == group.id))
        amount = 1000 if not fetch else fetch[0][0]
        limit = -1 if not fetch else fetch[0][1]
        if limit < -1:
            return [Plain(text=f"抽取次数限制非法({limit} 次)。")]
        fetch_user = await orm.fetchall(
            select(
                RandomHusband.ten_husband_times,
                RandomHusband.ten_husband_last_date
            ).where(RandomHusband.qq == member.id, RandomHusband.group == group.id)
        )
        ten_husband_times = 0 if not fetch_user else fetch_user[0][0]
        last_date = 0 if not fetch_user else fetch_user[0][1]
        today = int(datetime.today().strftime('%Y%m%d'))
        if last_date != today:
            ten_husband_times = 0
            await orm.insert_or_update(
                RandomHusband,
                [RandomHusband.qq == member.id, RandomHusband.group == group.id],
                {"qq": member.id,
                 "group": group.id,
                 "ten_husband_times": 0}
            )
        if ten_husband_times >= limit != -1:
            return [Plain(text=f"超出本群单日抽取限制 ({limit} 次)。")]
        else:
            url = f'http://q1.qlogo.cn/g?b=qq&nk={str(member.id)}&s=640'
            async with aiohttp.ClientSession() as session:
                async with session.get(url=url) as resp:
                    img_content = await resp.read()
            member_avatar = IMG.open(BytesIO(img_content)).convert("RGB").resize((100, 100), IMG.ANTIALIAS)
            wallet = await WalletHandler.get_balance(group, member)
            if wallet - amount < 0:
                return [Plain(text=f"硬币少于 {amount}，无法抽取十连！")]
            else:
                if pool == "mixed":
                    choices = RandomHusbandHandler.mixed_pool
                elif pool == "human":
                    choices = RandomHusbandHandler.human_pool
                else:
                    choices = RandomHusbandHandler.furry_pool
                result = IMG.new("RGBA", (340, 450), (0, 0, 0, 0))
                location = [(10, 10), (120, 10), (230, 10), (10, 120), (120, 120), (230, 120), (10, 230), (120, 230),
                            (230, 230), (120, 340)]
                extra = 0
                for i in range(0, 10):
                    choice = random.sample(choices, 1)[0]
                    husband = IMG.open(choice).resize((100, 100), IMG.ANTIALIAS)
                    if randrange(101) <= 2 and limit != -1:
                        husband = member_avatar
                        extra += 1
                    result.paste(husband, location[i])
                result.show()
                output = BytesIO()
                result.save(output, format='png')
                await orm.insert_or_update(
                    RandomHusband,
                    [RandomHusband.qq == member.id, RandomHusband.group == group.id],
                    {"qq": member.id,
                     "group": group.id,
                     "ten_husband_last_date": today,
                     "ten_husband_times": ten_husband_times + 1 - extra}
                )
                await WalletHandler.charge(group, member, amount, "十连老公")
                if limit == -1:
                    return [Image(data_bytes=output.getvalue()),
                            Plain(text=f"本次抽取耗费 {amount} 硬币，\n你现在一共有 {wallet - amount} 硬币。")]
                elif extra != 0 and limit != -1:
                    return [Image(data_bytes=output.getvalue()),
                            Plain(text=f"本次抽取耗费 {amount} 硬币，\n你现在一共有 {wallet - amount} 硬币。\n"),
                            Plain(text=f"本次抽取额外获得抽取次数 {extra} 次。\n"),
                            Plain(text=f"你今日在本群还剩抽取次数 {limit - ten_husband_times - 1 + extra} 次。")]
                else:
                    return [Image(data_bytes=output.getvalue()),
                            Plain(text=f"本次抽取耗费 {amount} 硬币，\n你现在一共有 {wallet - amount} 硬币。\n"),
                            Plain(text=f"你今日在本群还剩抽取次数 {limit - ten_husband_times - 1} 次。")]

    @staticmethod
    async def get_custom(member: Member, group: Group, pool: str, times: int):
        fetch = await orm.fetchall(
            select(
                Setting.ten_husband_cost,
                Setting.ten_husband_limit
            ).where(Setting.group_id == group.id))
        amount = 1000 if not fetch else fetch[0][0]
        amount = math.ceil(amount * (times / 10))
        limit = -1 if not fetch else fetch[0][1]
        if limit < -1:
            return [Plain(text=f"抽取次数限制非法({limit} 次)。")]
        fetch_user = await orm.fetchall(
            select(
                RandomHusband.ten_husband_times,
                RandomHusband.ten_husband_last_date
            ).where(RandomHusband.qq == member.id, RandomHusband.group == group.id)
        )
        ten_husband_times = 0 if not fetch_user else fetch_user[0][0]
        last_date = 0 if not fetch_user else fetch_user[0][1]
        today = int(datetime.today().strftime('%Y%m%d'))
        if last_date != today:
            ten_husband_times = 0
            await orm.insert_or_update(
                RandomHusband,
                [RandomHusband.qq == member.id, RandomHusband.group == group.id],
                {"qq": member.id,
                 "group": group.id,
                 "ten_husband_times": 0}
            )
        if ten_husband_times >= limit != -1:
            return [Plain(text=f"超出本群单日抽取限制 ({limit} 次)。")]
        else:
            url = f'http://q1.qlogo.cn/g?b=qq&nk={str(member.id)}&s=640'
            async with aiohttp.ClientSession() as session:
                async with session.get(url=url) as resp:
                    img_content = await resp.read()
            member_avatar = IMG.open(BytesIO(img_content)).convert("RGB").resize((100, 100), IMG.ANTIALIAS)
            wallet = await WalletHandler.get_balance(group, member)
            if wallet - amount < 0:
                return [Plain(text=f"硬币少于 {amount}，无法抽取十连！")]
            else:
                if pool == "mixed":
                    choices = RandomHusbandHandler.mixed_pool
                elif pool == "human":
                    choices = RandomHusbandHandler.human_pool
                else:
                    choices = RandomHusbandHandler.furry_pool
                gap_size = 10
                size = 100
                extra = 0
                x_cap = math.ceil(math.sqrt(times))
                y_cap = math.ceil(times / x_cap)
                result = IMG.new("RGBA",
                                 (gap_size + x_cap * (size + gap_size),
                                  gap_size + y_cap * (size + gap_size)),
                                 (0, 0, 0, 0))
                i = 0
                for y in range(0, y_cap):
                    for x in range(0, x_cap):
                        if i == times:
                            break
                        choice = random.sample(choices, 1)[0]
                        husband = IMG.open(choice).resize((size, size), IMG.ANTIALIAS)
                        if randrange(math.ceil(100 * times / 10) + 1) <= 2 and limit != -1:
                            husband = member_avatar
                            extra += 1
                        result.paste(husband, (gap_size + x * (size + gap_size), gap_size + y * (size + gap_size)))
                        i += 1
                del i
                output = BytesIO()
                result.save(output, format='png')
                await orm.insert_or_update(
                    RandomHusband,
                    [RandomHusband.qq == member.id, RandomHusband.group == group.id],
                    {"qq": member.id,
                     "group": group.id,
                     "ten_husband_last_date": today,
                     "ten_husband_times": ten_husband_times + 1 - extra}
                )
                await WalletHandler.charge(group, member, amount, "十连老公")
                if limit == -1:
                    return [Image(data_bytes=output.getvalue()),
                            Plain(text=f"本次抽取耗费 {amount} 硬币，\n你现在一共有 {wallet - amount} 硬币。")]
                elif extra != 0 and limit != -1:
                    return [Image(data_bytes=output.getvalue()),
                            Plain(text=f"本次抽取耗费 {amount} 硬币，\n你现在一共有 {wallet - amount} 硬币。\n"),
                            Plain(text=f"本次抽取额外获得抽取次数 {extra} 次。\n"),
                            Plain(text=f"你今日在本群还剩抽取次数 {limit - ten_husband_times - 1 + extra} 次。")]
                else:
                    return [Image(data_bytes=output.getvalue()),
                            Plain(text=f"本次抽取耗费 {amount} 硬币，\n你现在一共有 {wallet - amount} 硬币。\n"),
                            Plain(text=f"你今日在本群还剩抽取次数 {limit - ten_husband_times - 1} 次。")]