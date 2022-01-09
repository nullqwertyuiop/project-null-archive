import json
import os
import random
from random import randrange

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema

from SAGIRIBOT.Handler.Handler import AbstractHandler
from SAGIRIBOT.MessageSender.MessageItem import MessageItem
from SAGIRIBOT.MessageSender.MessageSender import GroupMessageSender
from SAGIRIBOT.MessageSender.Strategy import GroupStrategy, QuoteSource
from SAGIRIBOT.ORM.AsyncORM import UserCalledCount
from SAGIRIBOT.decorators import switch, blacklist
from SAGIRIBOT.utils import update_user_call_count_plus1

saya = Saya.current()
channel = Channel.current()
with open(f"{os.getcwd()}/statics/food.json", "r", encoding="utf-8") as r:
    food = json.loads(r.read())


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def jue_jue_zi_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await RandomFoodHandler.handle(app, message, group, member):
        await GroupMessageSender(result.strategy).send(app, result.message, message, group, member)


class RandomFoodHandler(AbstractHandler):
    __name__ = "RandomFoodHandler"
    __description__ = "随机饮食模块"
    __usage__ = "None"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group, member: Member):
        if message.asDisplay() in ("随机早餐", "早餐吃啥", "早上吃啥", "隨機早餐", "早餐吃啥", "早上吃啥"):
            await update_user_call_count_plus1(group, member, UserCalledCount.functions, "functions")
            return MessageItem(MessageChain.create([Plain(text=await RandomFoodHandler.meal("breakfast"))]),
                               QuoteSource(GroupStrategy()))
        elif message.asDisplay() in ("随机午餐", "午餐吃啥", "中午吃啥", "隨機午餐", "午餐吃啥", "中午吃啥"):
            await update_user_call_count_plus1(group, member, UserCalledCount.functions, "functions")
            return MessageItem(MessageChain.create([Plain(text=await RandomFoodHandler.meal("lunch"))]),
                               QuoteSource(GroupStrategy()))
        elif message.asDisplay() in ("随机晚餐", "晚餐吃啥", "晚上吃啥", "隨機晚餐", "晚餐吃啥", "晚上吃啥"):
            await update_user_call_count_plus1(group, member, UserCalledCount.functions, "functions")
            return MessageItem(MessageChain.create([Plain(text=await RandomFoodHandler.meal("dinner"))]),
                               QuoteSource(GroupStrategy()))
        elif message.asDisplay() in ("随机奶茶", "来杯奶茶", "隨機奶茶", "來杯奶茶"):
            await update_user_call_count_plus1(group, member, UserCalledCount.functions, "functions")
            return MessageItem(MessageChain.create([Plain(text=await RandomFoodHandler.tea("milk_tea"))]),
                               QuoteSource(GroupStrategy()))
        elif message.asDisplay() in ("随机果茶", "来杯果茶", "隨機果茶", "來杯果茶"):
            await update_user_call_count_plus1(group, member, UserCalledCount.functions, "functions")
            return MessageItem(MessageChain.create([Plain(text=await RandomFoodHandler.tea("fruit_tea"))]),
                               QuoteSource(GroupStrategy()))
        elif message.asDisplay() in ("随机饮品", "喝点什么", "来杯喝的", "隨機飲品", "喝點什麼", "來杯喝的"):
            await update_user_call_count_plus1(group, member, UserCalledCount.functions, "functions")
            return MessageItem(MessageChain.create([Plain(text=await RandomFoodHandler.tea("random"))]),
                               QuoteSource(GroupStrategy()))

    @staticmethod
    async def meal(which: str):
        main_amount = 1 if which == "breakfast" else 2
        divider = " "
        drink = ""
        pre = ""
        main = ""
        meal = ""
        if randrange(101) < 5:
            return "运气太好了，这餐没得吃！"
        if randrange(2) if which != "lunch" else 1:
            drink = str(random.choice(food[which]["drink"]))
        if randrange(2) if which != "lunch" else 1:
            pre = str(random.choice(food[which]["pre"]))
        if not (drink or pre):
            if randrange(2):
                drink = str(random.choice(food[which]["drink"]))
            else:
                pre = str(random.choice(food[which]["pre"]))
        for i in range(0, main_amount):
            main = main + str(random.choice(food[which]["main"])) + divider
        if which == "breakfast":
            meal = "早餐"
        elif which == "lunch":
            meal = "午餐"
        elif which == "dinner":
            meal = "晚餐"
        result = f"你的随机{meal}是：\n" + drink + divider + main + pre
        return result

    @staticmethod
    async def tea(which: str):
        if randrange(101) < 5:
            return "运气太好了，这杯没得喝！"
        if which == "random":
            which = random.choice(["milk_tea", "fruit_tea"])
        body = random.choice(food[which]["body"])
        addon = ""
        cream = ""
        temperature = random.choice(food[which]["temperature"])
        sugar = random.choice(food[which]["sugar"])
        divider = "加"
        for i in range(0, randrange(1, 4)):
            addon = divider + str(random.choice(food[which]["addon"]))
        if randrange(2):
            cream = divider + str(random.choice(food[which]["cream"]))
        result = f"你的随机{'奶茶' if which == 'milk_tea' else '果茶'}是：\n" + temperature + sugar + addon + cream + body
        return result
