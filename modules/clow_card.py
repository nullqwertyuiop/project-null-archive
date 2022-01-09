import json
import os
import random
from datetime import datetime
from io import BytesIO

from PIL import Image as IMG
from graia.ariadne.app import Ariadne, Friend
from graia.ariadne.event.message import Group, Member, GroupMessage, FriendMessage, TempMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain, Image
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
from sqlalchemy import select

from SAGIRIBOT.Handler.Handler import AbstractHandler
from SAGIRIBOT.MessageSender.MessageItem import MessageItem
from SAGIRIBOT.MessageSender.MessageSender import GroupMessageSender, FriendMessageSender, TempMessageSender
from SAGIRIBOT.MessageSender.Strategy import GroupStrategy, QuoteSource, StrategyType, TempStrategy, FriendStrategy
from SAGIRIBOT.ORM.AsyncORM import orm, Setting, UsageRecord
from SAGIRIBOT.decorators import switch, blacklist
from SAGIRIBOT.utils import update_user_call_count_plus1, UserCalledCount

saya = Saya.current()
channel = Channel.current()


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def clow_card_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await ClowCardHandler.handle(app, message, strategy=GroupStrategy(), group=group, member=member, event="GroupMessage"):
        await GroupMessageSender(result.strategy).send(app, result.message, message, group, member)


@channel.use(ListenerSchema(listening_events=[FriendMessage]))
async def clow_card_handler(app: Ariadne, message: MessageChain, friend: Friend):
    if result := await ClowCardHandler.handle(app, message, strategy=FriendStrategy(), friend=friend, event="FriendMessage"):
        await FriendMessageSender(result.strategy).send(app, result.message, message, friend)


@channel.use(ListenerSchema(listening_events=[TempMessage]))
async def clow_card_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await ClowCardHandler.handle(app, message, strategy=TempStrategy(), group=group, member=member, event="TempMessage"):
        await TempMessageSender(result.strategy).send(app, result.message, message, group, member)


class ClowCardHandler(AbstractHandler):
    __name__ = "ClowCardHandler"
    __description__ = "可以抽库洛牌的Handler"
    __usage__ = "None"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, strategy: StrategyType, group: Group = None,
                     member: Member = None, friend: Friend = None, event: str = None):
        if message.asDisplay() in ("库洛牌", "庫洛牌"):
            if group and member:
                await update_user_call_count_plus1(group, member, UserCalledCount.functions, "functions")
                resp = await ClowCardHandler.get_card(member=member, group=group, pool="clow", event=event)
            else:
                resp = await ClowCardHandler.get_card(friend=friend, pool="clow", event=event)
        elif message.asDisplay() in ("小樱牌", "小櫻牌"):
            if group and member:
                await update_user_call_count_plus1(group, member, UserCalledCount.functions, "functions")
                resp = await ClowCardHandler.get_card(member=member, group=group, pool="sakura", event=event)
            else:
                resp = await ClowCardHandler.get_card(friend=friend, pool="sakura", event=event)
        elif message.asDisplay() == "透明牌":
            if group and member:
                await update_user_call_count_plus1(group, member, UserCalledCount.functions, "functions")
                resp = await ClowCardHandler.get_card(member=member, group=group, pool="clear", event=event)
            else:
                resp = await ClowCardHandler.get_card(friend=friend, pool="clear", event=event)
        else:
            return None
        if strategy == TempStrategy():
            resp.pop(0)
        return MessageItem(
            MessageChain.create(resp), QuoteSource(strategy))

    @staticmethod
    async def get_card(member: Member = None, group: Group = None, friend: Friend = None, pool: str = "clow", event: str = None):
        cord = {
            "clow": UsageRecord.clow_card,
            "sakura": UsageRecord.clow_card,
            "clear": UsageRecord.clear_card
        }
        cord_usage = {
            "clow": "clow_card",
            "sakura": "clow_card",
            "clear": "clear_card"
        }
        current_date = int(datetime.today().strftime('%Y%m%d'))
        usage = 0
        if group and member:
            if limit := await orm.fetchall(
                    select(
                        Setting.tarot
                    ).where(Setting.group_id == group.id)):
                limit = limit[0][0]
            else:
                limit = -1
            if usage := await orm.fetchall(
                    select(
                        cord[pool]
                    ).where(
                        UsageRecord.group == group.id,
                        UsageRecord.qq == member.id,
                        UsageRecord.last_date == current_date)):
                usage = usage[0][0]
            else:
                usage = 0
            if usage >= limit != -1:
                return [Plain(text=f"超出本群单日抽取限制 ({limit} 次)。")]
        path = f"{os.getcwd()}/statics/clow_cards/clow_cards.json"
        with open(path, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
        card_list = os.listdir(f"{os.getcwd()}/statics/clow_cards/{pool}_cards")
        choice = random.choice(card_list)
        img_path = f"{os.getcwd()}/statics/clow_cards/{pool}_cards/{choice}"
        chosen = IMG.open(img_path).resize((815, 1800), IMG.ANTIALIAS)
        output = BytesIO()
        chosen.save(output, format='png')
        resp = [Image(data_bytes=output.getvalue())]
        if pool in ("clow", "sakura"):
            resp.append(Plain(text=f"卡牌：{data['clow'][choice]['name_jpn']} - {data['clow'][choice]['name_eng']}"))
            resp.append(Plain(text=f"\n简介：{data['clow'][choice]['disc']}")) if data['clow'][choice]['disc'] else None
            resp.append(Plain(text=f"\n象征：{data['clow'][choice]['meaning']}")) if data['clow'][choice][
                'meaning'] else None
            resp.append(Plain(text=f"\n对应：{data['clow'][choice]['poker']}")) if data['clow'][choice]['poker'] else None
        if group and member:
            await orm.insert_or_update(
                UsageRecord,
                [UsageRecord.qq == member.id, UsageRecord.group == group.id],
                {"qq": member.id,
                 "group": group.id,
                 cord_usage[pool]: usage + 1,
                 "last_date": current_date})
        return resp
