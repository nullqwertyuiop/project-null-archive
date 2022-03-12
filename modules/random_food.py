import json
import os
import random
from random import randrange

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.ariadne.message.parser.twilight import Twilight, RegexMatch
from graia.ariadne.model import Friend
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema

from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import QuoteSource
from sagiri_bot.orm.async_orm import UserCalledCount
from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.utils import update_user_call_count_plus, HelpPage, HelpPageElement

saya = Saya.current()
channel = Channel.current()

channel.name("RandomFood")
channel.author("nullqwertyuiop")
channel.description("随机餐点")


with open(f"{os.getcwd()}/statics/food.json", "r", encoding="utf-8") as r:
    food = json.loads(r.read())

twilight = Twilight(
    [
        RegexMatch(r"(随|隨)(机|機)((早|午|晚)餐)|((奶|果)茶)")
    ]
)


@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[twilight]
    )
)
async def random_food_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await RandomFood.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class RandomFood(AbstractHandler):
    __name__ = "RandomFood"
    __description__ = "随机饮食模块"
    __usage__ = "None"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if message.asDisplay() in ("随机早餐", "早餐吃啥", "早上吃啥", "隨機早餐", "早餐吃啥", "早上吃啥"):
            if member and group:
                await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
            return MessageItem(MessageChain.create([Plain(text=await RandomFood.meal("breakfast"))]),
                               QuoteSource())
        elif message.asDisplay() in ("随机午餐", "午餐吃啥", "中午吃啥", "隨機午餐", "午餐吃啥", "中午吃啥"):
            if member and group:
                await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
            return MessageItem(MessageChain.create([Plain(text=await RandomFood.meal("lunch"))]),
                               QuoteSource())
        elif message.asDisplay() in ("随机晚餐", "晚餐吃啥", "晚上吃啥", "隨機晚餐", "晚餐吃啥", "晚上吃啥"):
            if member and group:
                await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
            return MessageItem(MessageChain.create([Plain(text=await RandomFood.meal("dinner"))]),
                               QuoteSource())
        elif message.asDisplay() in ("随机奶茶", "来杯奶茶", "隨機奶茶", "來杯奶茶"):
            if member and group:
                await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
            return MessageItem(MessageChain.create([Plain(text=await RandomFood.tea("milk_tea"))]),
                               QuoteSource())
        elif message.asDisplay() in ("随机果茶", "来杯果茶", "隨機果茶", "來杯果茶"):
            if member and group:
                await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
            return MessageItem(MessageChain.create([Plain(text=await RandomFood.tea("fruit_tea"))]),
                               QuoteSource())
        elif message.asDisplay() in ("随机饮品", "喝点什么", "来杯喝的", "隨機飲品", "喝點什麼", "來杯喝的"):
            if member and group:
                await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
            return MessageItem(MessageChain.create([Plain(text=await RandomFood.tea("random"))]),
                               QuoteSource())

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


class RandomFoodHelp(HelpPage):
    __description__ = "随机餐饮"
    __trigger__ = "随机早餐/午餐/晚餐/奶茶/果茶"
    __category__ = "utility"
    __switch__ = None
    __icon__ = "food"

    def __init__(self, group: Group = None, member: Member = None, friend: Friend = None):
        super().__init__()
        self.__help__ = None
        self.group = group
        self.member = member
        self.friend = friend

    async def compose(self):
        self.__help__ = [
            HelpPageElement(icon=self.__icon__, text="随机餐饮", is_title=True),
            HelpPageElement(text="随机从菜单抽取菜名/饮品"),
            HelpPageElement(icon="check-all", text="已全局开启"),
            HelpPageElement(icon="alert", text="本项目不提供点菜/订餐服务"),
            HelpPageElement(icon="lightbulb-on", text="使用示例：\n"
                                                      "发送\"随机早餐\"或者\"随机午餐\"或者\"随机晚餐\""
                                                      "或者\"随机奶茶\"或者\"随机果茶\"即可")
        ]
        super().__init__(self.__help__)
        return await super().compose()
