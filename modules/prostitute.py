import re
import time
from datetime import datetime
from io import BytesIO
from random import randrange

import aiohttp
from PIL import Image as IMG
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
from sqlalchemy import select

from SAGIRIBOT.Handler.Handler import AbstractHandler
from SAGIRIBOT.MessageSender.MessageItem import MessageItem
from SAGIRIBOT.MessageSender.MessageSender import GroupMessageSender
from SAGIRIBOT.MessageSender.Strategy import GroupStrategy, QuoteSource
from SAGIRIBOT.ORM.AsyncORM import orm, Prostitute, SignInReward, Setting
from SAGIRIBOT.decorators import switch, blacklist
from SAGIRIBOT.utils import get_setting
from modules.WalletHandler import WalletHandler

saya = Saya.current()
channel = Channel.current()
exchange_ratio = 250


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def speak_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await ProstituteHandler.handle(app, message, group, member):
        await GroupMessageSender(result.strategy).send(app, result.message, message, group, member)


class ProstituteHandler(AbstractHandler):
    __name__ = "ProstituteHandler"
    __description__ = "卖铺汇总"
    __usage__ = "None"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group, member: Member):
        # if message.asDisplay() in ("#卖铺", "#站街", "#开张", "#打工 卖铺", "#打工 站街", "#打工 开张", "卖铺", "站街", "开张"):
        #     if not await get_setting(group.id, Setting.prostitute):
        #         return None
        #     try:
        #         result = await ProstituteHandler.prostitute(member.id)
        #         return MessageItem(MessageChain.create([
        #             Image(data_bytes=await ProstituteHandler.get_avatar(member.id)),
        #             Plain(text=result)]), QuoteSource(GroupStrategy()))
        #     except AccountMuted:
        #         logger.error(f"Bot 在群 <{group.name}> 被禁言，无法发送！")
        #         return None
        if message.asDisplay() in ("我的β", "我的贝塔"):
            if not await get_setting(group.id, Setting.prostitute):
                return None
            result = await ProstituteHandler.get_beta(group, member)
            return MessageItem(MessageChain.create([
                # Image(data_bytes=await ProstituteHandler.get_avatar(member.id)),
                Plain(text=result)]), QuoteSource(GroupStrategy()))
        elif re.match("转硬币#.*", message.asDisplay()):
            if not await get_setting(group.id, Setting.prostitute):
                return None
            return MessageItem(MessageChain.create([Plain(text="该功能已移除。")]), QuoteSource(GroupStrategy()))
            # try:
            #     _, amount = message.asDisplay().split("#")
            #     member_id = member.id
            #     try:
            #         amount = int(amount)
            #     except:
            #         result = f"用法：\n转硬币#(整数)\n兑换比率：{exchange_ratio}β币 -> 1硬币"
            #         return MessageItem(MessageChain.create([Plain(text=result)]), QuoteSource(GroupStrategy()))
            #     await update_user_call_count_plus1(group, member, UserCalledCount.functions, "functions")
            #     result = await ProstituteHandler.beta_to_coin(member_id, amount)
            #     return MessageItem(MessageChain.create([Plain(text=result)]), QuoteSource(GroupStrategy()))
            # except AccountMuted:
            #     logger.error(f"Bot 在群 <{group.name}> 被禁言，无法发送！")
            #     return None
        elif re.match("转β币#.*", message.asDisplay()):
            if not await get_setting(group.id, Setting.prostitute):
                return None
            return MessageItem(MessageChain.create([Plain(text="该功能已移除。")]), QuoteSource(GroupStrategy()))
            # try:
            #     _, amount = message.asDisplay().split("#")
            #     member_id = member.id
            #     try:
            #         amount = int(amount)
            #     except:
            #         result = f"用法：\n转β币#(整数)\n兑换比率：1硬币 -> {exchange_ratio}β币"
            #         return MessageItem(MessageChain.create([Plain(text=result)]), QuoteSource(GroupStrategy()))
            #     await update_user_call_count_plus1(group, member, UserCalledCount.functions, "functions")
            #     result = await ProstituteHandler.coin_to_beta(member_id, amount)
            #     return MessageItem(MessageChain.create([Plain(text=result)]), QuoteSource(GroupStrategy()))
            # except AccountMuted:
            #     logger.error(f"Bot 在群 <{group.name}> 被禁言，无法发送！")
            #     return None
        # elif re.match("自身种族#.*", message.asDisplay()):
        #     _, race = message.asDisplay().split("#")
        #     if race == "人类":
        #         result = await ProstituteHandler.set_race(member.id, "self", "human")
        #         return MessageItem(MessageChain.create([Plain(text=result)]), QuoteSource(GroupStrategy()))
        #     elif race == "兽人":
        #         result = await ProstituteHandler.set_race(member.id, "self", "anthro")
        #         return MessageItem(MessageChain.create([Plain(text=result)]), QuoteSource(GroupStrategy()))
        # elif re.match("客人种族#.*", message.asDisplay()):
        #     _, race =message.asDisplay().split("#")
        #     if race == "人类":
        #         result = await ProstituteHandler.set_race(member.id, "client", "human")
        #         return MessageItem(MessageChain.create([Plain(text=result)]), QuoteSource(GroupStrategy()))
        #     elif race == "兽人":
        #         result = await ProstituteHandler.set_race(member.id, "client", "anthro")
        #         return MessageItem(MessageChain.create([Plain(text=result)]), QuoteSource(GroupStrategy()))

    @staticmethod
    async def prostitute(member_id: int):
        fetch = await orm.fetchall(
            select(
                Prostitute.client,
                Prostitute.last_date,
                Prostitute.pay
            ).where(Prostitute.qq == member_id))
        if not fetch:
            clients = 0
            date = 0
            pay = 0
        else:
            clients = int(fetch[0][0])
            date = int(fetch[0][1])
            pay = int(fetch[0][2])
        current_date = int(datetime.today().strftime('%Y%m%d'))
        if date == current_date:
            text = f"你今天已经开张过了，小心β烂掉！\n现共接客： {clients} 人，\n现有工资： {pay} β币"
            return text
        else:
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            arrest = randrange(101)
            today_clients = randrange(16)
            clients = clients + today_clients
            today_pay = 0
            for i in range(0, today_clients):
                today_pay = today_pay + (randrange(10) + 1) * 50
            pay = pay + today_pay
            if arrest <= 25:
                luck = randrange(2)
                if luck != 1:
                    lost = (randrange(3) + 1) * 1000
                    pay = pay - lost
                    try:
                        await orm.insert_or_update(
                            Prostitute,
                            [Prostitute.qq == member_id],
                            {"qq": member_id,
                             "client": clients,
                             "pay": pay,
                             "last_date": current_date}
                        )
                        if today_clients == 0:
                            text = f"尽管你今天没接到客人，你还是被逮住了，被罚了 {lost} 块\n卖铺时间：{current_time}\n" \
                                   f"现共接客： {clients} 人，\n现有工资 {pay} β币"
                        elif today_clients >= 10:
                            text = f"你今天接到了 {today_clients} 客人，得了 {today_pay} β币，但是你自信放光芒，" \
                                   f"别人顺着光芒来把你逮住了，罚了你 {lost} 块\n卖铺时间：{current_time}\n" \
                                   f"现共接客： {clients} 人，\n现有工资 {pay} β币"
                        else:
                            text = f"你在接客的时候被逮住了，尽管你已经接了 {today_clients} 个客人，得了 {today_pay} β币，" \
                                   f"你还是被罚了 {lost} 块\n卖铺时间：{current_time}\n现共接客： {clients} 人，\n" \
                                   f"现有工资 {pay} β币"
                        return text
                    except:
                        text = "卖铺出错，请联系管理员。"
                        return text
                else:
                    bonus_client = (randrange(5) + 1)
                    clients = clients + bonus_client
                    bonus = 0
                    for j in range(0, bonus_client):
                        bonus = bonus + (randrange(3) + 1) * 100
                    today_pay = today_pay + bonus
                    pay = pay + bonus
                    try:
                        await orm.insert_or_update(
                            Prostitute,
                            [Prostitute.qq == member_id],
                            {"qq": member_id,
                             "client": clients,
                             "pay": pay,
                             "last_date": current_date}
                        )
                        if today_clients == 0:
                            text = f"尽管你今天没接到客，你还是被逮住了，但是你以独特的骚劲儿令逮捕你的人瞠目结舌，" \
                                   f"你又接了 {bonus_client} 个，工资 {today_pay} β币\n" \
                                   f"卖铺时间：{current_time}\n现共接客： {clients} 人，\n" \
                                   f"现有工资 {pay} β币"
                        else:
                            text = f"你在接客的时候被逮住了，但是你以独特的骚劲儿令逮捕你的人瞠目结舌，" \
                                   f"你在接了 {today_clients} 个客人后又接了 {bonus_client} 个，" \
                                   f"工资 {today_pay} β币\n卖铺时间：{current_time}\n现共接客： {clients} 人，\n" \
                                   f"现有工资 {pay} β币"
                        return text
                    except:
                        text = "卖铺出错，请联系管理员。"
                        return text
            else:
                try:
                    await orm.insert_or_update(
                        Prostitute,
                        [Prostitute.qq == member_id],
                        {"qq": member_id,
                         "client": clients,
                         "pay": pay,
                         "last_date": current_date})
                    if today_clients == 0:
                        text = f"可惜，今天你没有接到客人，\n卖铺时间：{current_time}\n现共接客： {clients} 人，\n" \
                               f"现有工资 {pay} β币"
                    elif today_clients >= 10:
                        text = f"你独领风骚，这条街的客户全来了你这，你今天接客 {today_clients} 人，\n工资 {today_pay} β币\n" \
                               f"卖铺时间：{current_time}\n现共接客 {clients} 人，\n现有工资： {pay} β币"
                    else:
                        text = f"卖铺成功！\n本次开张接到 {today_clients} 个客人，获得工资 {today_pay} β币\n" \
                               f"卖铺时间：{current_time}\n现共接客 {clients} 人，\n现有工资 {pay} β币"
                    return text
                except:
                    text = "卖铺出错，请联系管理员。"
                    return text

    @staticmethod
    async def get_avatar(uin: int):
        url = f'http://q1.qlogo.cn/g?b=qq&nk={str(uin)}&s=640'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url) as resp:
                img_content = await resp.read()
        img_content = IMG.open(BytesIO(img_content)).convert("RGB").resize((640, 640), IMG.ANTIALIAS)
        output = BytesIO()
        img_content.save(output, format='jpeg')
        return output.getvalue()

    @staticmethod
    async def get_beta(group: Group, member: Member):
        fetch = await orm.fetchall(
            select(
                Prostitute.client
            ).where(Prostitute.qq == member.id, Prostitute.group_id == group.id))
        wallet = await WalletHandler.get_balance(group, member)
        wallet = wallet if wallet else 0
        client = int(fetch[0][0]) if fetch else 0
        text = f"你现在一共有 {wallet} 硬币，\n一共接了 {client} 个客人。"
        return text

    @staticmethod
    async def beta_to_coin(uin: int, amount: int):
        if amount <= 0:
            text = "这是转了个什么东西？"
            return text
        else:
            fetch = await orm.fetchall(select(Prostitute.pay).where(Prostitute.qq == uin))
            if not fetch:
                text = "没有β币也想转硬币，珍素大胆！"
                return text
            else:
                beta = fetch[0][0]
                if (beta - amount * exchange_ratio) < 0:
                    text = "就这点β币也想转硬币，珍素大胆！"
                    return text
                else:
                    try:
                        fetch_coin = await orm.fetchall(
                            select(
                                SignInReward.coin
                            ).where(SignInReward.qq == uin))
                        if not fetch_coin:
                            coins = 0
                        else:
                            coins = int(fetch_coin[0][0])
                        current_beta = beta - amount * exchange_ratio
                        current_coin = coins + amount
                        await orm.insert_or_update(
                            SignInReward,
                            [SignInReward.qq == uin],
                            {"qq": uin,
                             "coin": current_coin})
                        await orm.insert_or_update(
                            Prostitute,
                            [Prostitute.qq == uin],
                            {"qq": uin,
                             "pay": current_beta})
                        text = f"转换成功！\n现有硬币：{current_coin} 个\n现有工资：{current_beta} β币"
                        return text
                    except:
                        text = "转换错误，请联系管理员。"
                        return text

    @staticmethod
    async def coin_to_beta(uin: int, amount: int):
        if amount <= 0:
            text = "这是转了个什么东西？"
            return text
        else:
            fetch = await orm.fetchall(select(SignInReward.coin).where(SignInReward.qq == uin))
            if not fetch:
                text = "没有硬币也想转β币，珍素大胆！"
                return text
            else:
                coin = fetch[0][0]
                if (coin - amount) < 0:
                    text = "就这点硬币也想转β币，珍素大胆！"
                    return text
                else:
                    try:
                        fetch_beta = await orm.fetchall(
                            select(
                                Prostitute.pay
                            ).where(Prostitute.qq == uin))
                        if not fetch_beta:
                            beta = 0
                        else:
                            beta = int(fetch_beta[0][0])
                        current_beta = beta + amount * exchange_ratio
                        current_coin = coin - amount
                        await orm.insert_or_update(
                            Prostitute,
                            [Prostitute.qq == uin],
                            {"qq": uin,
                             "pay": current_beta})
                        await orm.insert_or_update(
                            SignInReward,
                            [SignInReward.qq == uin],
                            {"qq": uin,
                             "coin": current_coin})
                        text = f"转换成功！\n现有工资：{current_beta} β币\n现有硬币：{current_coin} 个"
                        return text
                    except:
                        text = "转换错误，请联系管理员。"
                        return text

    # @staticmethod
    # async def set_race(uin: int, type: str, race: str):
    #     if (type == "self") & (race == "human"):
    #         await orm.insert_or_update(
    #             Prostitute,
    #             [Prostitute.qq == uin],
    #             {"qq": uin,
    #              "pay": current_beta})
    #         text = ""
    #         return text
    #     elif (type == "self") & (race == "anthro"):
    #         text = ""
    #         return text
    #     elif (type == "client") & (race == "human"):
    #         text = ""
    #         return text
    #     elif (type == "client") & (race == "anthro"):
    #         text = ""
    #         return text
    #     else:
    #         text = "更变种族出错，请联系机器人管理员。"
    #         return text
    #