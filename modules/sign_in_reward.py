import time
from io import BytesIO
from random import randrange

import aiohttp
from PIL import Image as IMG
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.ariadne.model import Friend
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
from sqlalchemy import select

from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import QuoteSource
from sagiri_bot.orm.async_orm import orm, SignInReward, Setting, UserCalledCount
from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.utils import get_setting, update_user_call_count_plus
from modules.wallet import Wallet

saya = Saya.current()
channel = Channel.current()

channel.name("SignInReward")
channel.author("nullqwertyuiop")
channel.description("签到")


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def sign_in_reward_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await SignInRewardHandler.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class SignInRewardHandler(AbstractHandler):
    __name__ = "SignInRewardHandler"
    __description__ = "签到获取奖励"
    __usage__ = "None"

    # @staticmethod
    # def get_match_element(message: MessageChain) -> list:
    #     return [element for element in message.__root__ if isinstance(element, At)]

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if message.asDisplay() in ("签到", "簽到"):
            if not await get_setting(group.id, Setting.sign_in):
                return None
            await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
            result = await SignInRewardHandler.sign_in(group, member)
            return MessageItem(MessageChain.create([
                # Image(data_bytes=await SignInRewardHandler.get_avatar(member.id)),
                Plain(text=result)]), QuoteSource())

    @staticmethod
    async def sign_in(group: Group, member: Member):
        fetch = await orm.fetchall(
            select(
                SignInReward.last_date,
                SignInReward.streak
            ).where(SignInReward.qq == member.id, SignInReward.group_id == group.id)
        )
        mig_merge = False
        if not fetch:
            fetch = await orm.fetchall(
                select(
                    SignInReward.coin,
                    SignInReward.last_date,
                    SignInReward.streak
                ).where(SignInReward.qq == member.id, SignInReward.group_id == 0)
            )
            if fetch:
                await Wallet.update(group, member, fetch[0][0], "签到模块迁移")
                await orm.insert_or_update(
                    SignInReward,
                    [SignInReward.qq == member.id, SignInReward.group_id == group.id],
                    {"qq": member.id,
                     "group_id": -1,
                     "coin": fetch[0][0],
                     "last_date": int(fetch[0][1]),
                     "streak": int(fetch[0][2])
                     }
                )
                await orm.delete(
                    SignInReward,
                    [SignInReward.qq == member.id, SignInReward.group_id == 0]
                )
                mig_merge = True
                last_date = int(fetch[0][1])
                streak = int(fetch[0][2])
            else:
                last_date = 0
                streak = 0
        else:
            last_date = int(fetch[0][0])
            streak = int(fetch[0][1])
        wallet = await Wallet.get_balance(group, member)
        coins = wallet if wallet else 0
        current_date = int(time.localtime().tm_yday)
        extra = False
        if last_date == current_date and not (extra := await SignInRewardHandler.extra_check(member.id)):
            if mig_merge:
                await orm.insert_or_update(
                    SignInReward,
                    [SignInReward.qq == member.id, SignInReward.group_id == group.id],
                    {"qq": member.id,
                     "group_id": group.id,
                     "coin": coins,
                     "last_date": current_date,
                     "streak": streak})
            text = f"你今天已经签到过了！\n现有硬币： {coins} 个。"
            return text
        else:
            today_coins = 2500 + randrange(6) * 500
            coins = coins + today_coins
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            if last_date == (current_date - 1) and not extra:
                streak = streak + 1
            elif (last_date - current_date == 364 or last_date - current_date == 365) and not extra:
                streak = streak + 1
            elif extra:
                streak = streak
            else:
                streak = 1
            try:
                await orm.insert_or_update(
                    SignInReward,
                    [SignInReward.qq == member.id, SignInReward.group_id == group.id],
                    {"qq": member.id,
                     "group_id": group.id,
                     "coin": coins,
                     "last_date": current_date,
                     "streak": streak})
                await Wallet.update(group, member, today_coins, "签到")
                text = f"签到成功！\n获得硬币：{today_coins} 个，\n现有硬币：{coins} 个，\n签到时间：{current_time}，\n" \
                       f"连续签到：{streak} 天"
                return text
            except:
                text = "签到出错，请联系管理员。"
                return text

    @staticmethod
    async def get_wallet(member_id: int):
        fetch = await orm.fetchall(
            select(
                SignInReward.coin
            ).where(SignInReward.qq == member_id))
        if not fetch:
            coins = 0
        else:
            coins = int(fetch[0][0])
        text = f"你现在一共有硬币 {coins} 个。"
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
    async def extra_check(member: int):
        fetch = await orm.fetchall(
            select(
                SignInReward.extra,
                SignInReward.last_date
            ).where(SignInReward.qq == member))
        if not fetch:
            fetch = [[0, 0]]
        if fetch[0][0] == 0:
            return False
        else:
            await orm.insert_or_update(
                SignInReward,
                [SignInReward.qq == member],
                {"qq": member,
                 "extra": 0})
            return True
