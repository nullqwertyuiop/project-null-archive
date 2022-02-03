import json
import os
import random
from datetime import datetime
from io import BytesIO

from PIL import Image as IMG
from graia.ariadne.app import Ariadne, Friend
from graia.ariadne.event.message import Group, Member, GroupMessage, FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain, Image
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
from sqlalchemy import select

from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import QuoteSource
from sagiri_bot.orm.async_orm import orm, Setting, UsageRecord
from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.utils import update_user_call_count_plus, UserCalledCount

saya = Saya.current()
channel = Channel.current()

channel.name("ClowCard")
channel.author("nullqwertyuiop")
channel.description("库洛牌、小樱牌、透明牌")


@channel.use(ListenerSchema(listening_events=[FriendMessage]))
async def clow_card_handler(app: Ariadne, message: MessageChain, friend: Friend):
    if result := await ClowCard.handle(app, message, friend=friend):
        await MessageSender(result.strategy).send(app, result.message, message, friend, friend)


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def clow_card_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await ClowCard.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class ClowCard(AbstractHandler):
    __name__ = "ClowCard"
    __description__ = "可以抽库洛牌的Handler"
    __usage__ = "None"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if message.asDisplay() in ("库洛牌", "庫洛牌"):
            if group and member:
                await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
                resp = await ClowCard.get_card(member=member, group=group, pool="clow")
            else:
                resp = await ClowCard.get_card(friend=friend, pool="clow")
        elif message.asDisplay() in ("小樱牌", "小櫻牌"):
            if group and member:
                await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
                resp = await ClowCard.get_card(member=member, group=group, pool="sakura")
            else:
                resp = await ClowCard.get_card(friend=friend, pool="sakura")
        elif message.asDisplay() == "透明牌":
            if group and member:
                await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
                resp = await ClowCard.get_card(member=member, group=group, pool="clear")
            else:
                resp = await ClowCard.get_card(friend=friend, pool="clear")
        else:
            return None
        return MessageItem(
            MessageChain.create(resp), QuoteSource())

    @staticmethod
    async def get_card(member: Member = None, group: Group = None, friend: Friend = None, pool: str = "clow"):
        # cord = {
        #     "clow": UsageRecord.clow_card,
        #     "sakura": UsageRecord.clow_card,
        #     "clear": UsageRecord.clear_card
        # }
        # cord_usage = {
        #     "clow": "clow_card",
        #     "sakura": "clow_card",
        #     "clear": "clear_card"
        # }
        # current_date = int(datetime.today().strftime('%Y%m%d'))
        # usage = 0
        # if group and member:
        #     if limit := await orm.fetchall(
        #             select(
        #                 Setting.tarot
        #             ).where(Setting.group_id == group.id)):
        #         limit = limit[0][0]
        #     else:
        #         limit = -1
        #     if usage := await orm.fetchall(
        #             select(
        #                 cord[pool]
        #             ).where(
        #                 UsageRecord.group == group.id,
        #                 UsageRecord.qq == member.id,
        #                 UsageRecord.last_date == current_date)):
        #         usage = usage[0][0]
        #     else:
        #         usage = 0
        #     if usage >= limit != -1:
        #         return [Plain(text=f"超出本群单日抽取限制 ({limit} 次)。")]
        path = f"{os.getcwd()}/statics/clow_cards/clow_cards.json"
        with open(path, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
        card_list = os.listdir(f"{os.getcwd()}/statics/clow_cards/{pool}_cards")
        random.seed(int(datetime.today().strftime('%Y%m%d')
                        + str(member.id if member else friend.id)
                        + str(group.id if group else 0)))
        choice = random.choice(card_list)
        random.seed()
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
        # if group and member:
        #     await orm.insert_or_update(
        #         UsageRecord,
        #         [UsageRecord.qq == member.id, UsageRecord.group == group.id],
        #         {"qq": member.id,
        #          "group": group.id,
        #          cord_usage[pool]: usage + 1,
        #          "last_date": current_date})
        return resp
