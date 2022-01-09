from datetime import datetime
import os
import json
import random
from pathlib import Path
from graia.saya import Saya, Channel
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.ariadne.message.element import Plain, Image
from sqlalchemy import select

from SAGIRIBOT.MessageSender.MessageSender import GroupMessageSender
from graia.ariadne.event.message import Group, Member, GroupMessage

from SAGIRIBOT.ORM.AsyncORM import orm, Setting, UsageRecord
from SAGIRIBOT.decorators import switch, blacklist, frequency_limit_require_weight_free
from SAGIRIBOT.Handler.Handler import AbstractHandler
from SAGIRIBOT.MessageSender.MessageItem import MessageItem
from SAGIRIBOT.MessageSender.Strategy import GroupStrategy, QuoteSource
from SAGIRIBOT.utils import update_user_call_count_plus1, UserCalledCount

saya = Saya.current()
channel = Channel.current()


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def tarot_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await TarotHandler.handle(app, message, group, member):
        await GroupMessageSender(result.strategy).send(app, result.message, message, group, member)


class TarotHandler(AbstractHandler):
    __name__ = "TarotHandler"
    __description__ = "可以抽塔罗牌的Handler"
    __usage__ = "None"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group, member: Member):
        if message.asDisplay() == "塔罗牌":
            await update_user_call_count_plus1(group, member, UserCalledCount.functions, "functions")
            return await TarotHandler.get_tarot(member, group)
        else:
            return None

    @staticmethod
    async def get_tarot(member: Member, group: Group):
        current_date = int(datetime.today().strftime('%Y%m%d'))
        if limit := await orm.fetchall(
                select(
                    Setting.tarot
                ).where(Setting.group_id == group.id)):
            limit = limit[0][0]
        else:
            limit = -1
        if usage := await orm.fetchall(
                select(
                    UsageRecord.tarot
                ).where(
                    UsageRecord.group == group.id,
                    UsageRecord.qq == member.id,
                    UsageRecord.last_date == current_date
                )):
            usage = usage[0][0]
        else:
            usage = 0
        if usage >= limit != -1:
            return MessageItem(MessageChain.create([
                Plain(text=f"超出本群单日抽取限制 ({limit} 次)。")
            ]), QuoteSource())
        card, filename = await TarotHandler.get_random_tarot()
        dir = random.choice(['normal', 'reverse'])
        type = '正位' if dir == 'normal' else '逆位'
        content = f"{card['name']} ({card['name-en']}) {type}\n牌意：{card['meaning'][dir]}"
        elements = []
        img_path = f"{os.getcwd()}/statics/tarot/{dir}/{filename + '.jpg'}"
        if filename and os.path.exists(img_path):
            elements.append(Image(path=img_path))
        elements.append(Plain(text=content))
        await orm.insert_or_update(
            UsageRecord,
            [UsageRecord.qq == member.id, UsageRecord.group == group.id],
            {"qq": member.id,
             "group": group.id,
             "tarot": usage + 1,
             "last_date": current_date})
        return MessageItem(MessageChain.create(elements), QuoteSource())

    @staticmethod
    @frequency_limit_require_weight_free(1)
    async def get_random_tarot():
        path = f"{os.getcwd()}/statics/tarot/tarot.json"
        with open(path, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
        kinds = ['major', 'pentacles', 'wands', 'cups', 'swords']
        cards = []
        for kind in kinds:
            cards.extend(data[kind])
        card = random.choice(cards)
        filename = ''
        for kind in kinds:
            if card in data[kind]:
                filename = '{}{:02d}'.format(kind, card['num'])
                break
        return card, filename
