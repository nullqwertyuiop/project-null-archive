import json
import os
import random
from datetime import datetime
from io import BytesIO
from random import randrange

from PIL import Image as IMG
from PIL import ImageFont, ImageDraw
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain, Image
from graia.ariadne.model import MemberPerm
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
from sqlalchemy import select

from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import QuoteSource
from sagiri_bot.orm.async_orm import orm, Setting, LiveAHeroSimulator, UserCalledCount, GachaSimulatorRecord
from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.utils import update_user_call_count_plus, get_setting, user_permission_require
from modules.WalletHandler import WalletHandler

saya = Saya.current()
channel = Channel.current()
card_location = [(219, 367), (72, 500), (219, 500), (367, 500), (72, 632), (219, 632), (367, 632), (72, 763),
                 (219, 763), (367, 763)]
frame_location = [(213, 361), (66, 494), (213, 494), (361, 494), (66, 626), (213, 626), (361, 626), (66, 757),
                  (213, 757), (361, 757)]
star_location = [(220, 453), (73, 586), (220, 586), (367, 586), (73, 718), (220, 718), (367, 718), (73, 849),
                 (220, 849), (367, 849)]
sk_base_location = [(213, 360), (66, 493), (213, 493), (361, 493), (66, 625), (213, 625), (361, 625),
                    (66, 757), (213, 757)]
sk_mask_location = [(214, 361), (67, 494), (214, 494), (362, 494), (67, 626), (214, 626), (362, 626),
                    (67, 758), (214, 758)]
sk_frame_location = [(213, 360), (66, 493), (213, 493), (361, 493), (66, 625), (213, 625), (361, 625),
                     (66, 757), (213, 757)]
sk_four_stars_location = [(236, 453), (86, 585), (236, 585), (381, 585), (86, 717), (236, 717), (381, 717),
                          (86, 849), (236, 849)]
sk_three_stars_location = [(242, 453), (95, 585), (242, 585), (390, 585), (95, 717), (242, 717), (390, 717),
                           (95, 849), (242, 849)]
try:
    three_stars = os.listdir(f"{os.getcwd()}/statics/lah/3/")
    for i in range(len(three_stars)):
        three_stars[i] = "/3/" + three_stars[i]
    four_stars = os.listdir(f"{os.getcwd()}/statics/lah/4/")
    for i in range(len(four_stars)):
        four_stars[i] = "/4/" + four_stars[i]
    five_stars = os.listdir(f"{os.getcwd()}/statics/lah/5/")
    for i in range(len(five_stars)):
        five_stars[i] = "/5/" + five_stars[i]
    three_sk = os.listdir(f"{os.getcwd()}/statics/lah/3_sk/")
    for i in range(len(three_sk)):
        three_sk[i] = "/3_sk/" + three_sk[i]
    four_sk = os.listdir(f"{os.getcwd()}/statics/lah/4_sk/")
    for i in range(len(four_sk)):
        four_sk[i] = "/4_sk/" + four_sk[i]
    three_sk_limited = os.listdir(f"{os.getcwd()}/statics/lah/3_sk_limited/")
    for i in range(len(three_sk_limited)):
        three_sk_limited[i] = "/3_sk_limited/" + three_sk_limited[i]
    four_sk_limited = os.listdir(f"{os.getcwd()}/statics/lah/4_sk_limited/")
    for i in range(len(four_sk_limited)):
        four_sk_limited[i] = "/4_sk_limited/" + four_sk_limited[i]
    three_stars_limited = os.listdir(f"{os.getcwd()}/statics/lah/3_limited/")
    for i in range(len(three_stars_limited)):
        three_stars_limited[i] = "/3_limited/" + three_stars_limited[i]
    four_stars_limited = os.listdir(f"{os.getcwd()}/statics/lah/4_limited/")
    for i in range(len(four_stars_limited)):
        four_stars_limited[i] = "/4_limited/" + four_stars_limited[i]
    five_stars_limited = os.listdir(f"{os.getcwd()}/statics/lah/5_limited/")
    for i in range(len(five_stars_limited)):
        five_stars_limited[i] = "/5_limited/" + five_stars_limited[i]
    four_stars_up = os.listdir(f"{os.getcwd()}/statics/lah/4_up/")
    for i in range(len(four_stars_up)):
        four_stars_up[i] = "/4_up/" + four_stars_up[i]
    four_sk_up = os.listdir(f"{os.getcwd()}/statics/lah/4_sk_up/")
    for i in range(len(four_sk_up)):
        four_sk_up[i] = "/4_sk_up/" + four_sk_up[i]
    five_stars_up = os.listdir(f"{os.getcwd()}/statics/lah/5_up/")
    for i in range(len(five_stars_up)):
        five_stars_up[i] = "/5_up/" + five_stars_up[i]
    with open(f"{os.getcwd()}/statics/lah/hero.json", "r", encoding="utf-8") as r:
        hero_data = json.loads(r.read())
except FileNotFoundError as err:
    print(err)


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def template_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await LiveAHeroSimulatorHandler.handle(app, message, group, member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class LiveAHeroSimulatorHandler(AbstractHandler):
    __name__ = "LiveAHeroSimulatorHandler"
    __description__ = "Live A Hero 抽卡模拟器"
    __usage__ = "lah抽卡"
    peach_mode = {}

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group, member: Member):
        if message.asDisplay() in (
                "LAH模拟抽卡", "LAH 模拟抽卡", "lah模拟抽卡", "lah 模拟抽卡", "LAH模擬抽卡", "LAH 模擬抽卡", "lah模擬抽卡", "lah 模擬抽卡"
        ):
            if not await get_setting(group.id, Setting.gacha_simulator):
                return MessageItem(
                    MessageChain.create([Plain(text=f"模拟抽卡功能已被禁用。")]),
                    QuoteSource()
                )
            await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
            return MessageItem(
                MessageChain.create(await LiveAHeroSimulatorHandler.get_simulation(member, group, limited=False)),
                QuoteSource())
        elif message.asDisplay() in (
                "LAH抽卡总结", "LAH 抽卡总结", "lah抽卡总结", "lah 抽卡总结", "LAH抽卡總結", "LAH 抽卡總結", "lah抽卡總結", "lah 抽卡總結"
        ):
            if not await get_setting(group.id, Setting.gacha_simulator):
                return MessageItem(
                    MessageChain.create([Plain(text=f"模拟抽卡功能已被禁用。")]),
                    QuoteSource()
                )
            await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
            return MessageItem(MessageChain.create(await LiveAHeroSimulatorHandler.get_summary(member, group)),
                               QuoteSource())
        elif message.asDisplay() in (
                "LAH模拟限定抽卡", "LAH 模拟限定抽卡", "lah模拟限定抽卡", "lah 模拟限定抽卡", "LAH模擬限定抽卡", "LAH 模擬限定抽卡", "lah模擬限定抽卡",
                "lah 模擬限定抽卡"):
            if not await get_setting(group.id, Setting.gacha_simulator):
                return MessageItem(
                    MessageChain.create([Plain(text=f"模拟抽卡功能已被禁用。")]),
                    QuoteSource()
                )
            # await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
            # return MessageItem(MessageChain.create(await LiveAHeroSimulatorHandler.get_simulation(member, group, limited=True)),
            #                   QuoteSource())
            return MessageItem(MessageChain.create([Plain(text=f"限定卡池已关闭。")]), QuoteSource())
        elif message.asDisplay() in (
                "LAH模拟UP抽卡", "LAH 模拟 UP 抽卡", "lah模拟up抽卡", "lah 模拟 up 抽卡", "LAH模擬UP抽卡", "LAH 模擬UP抽卡", "lah模擬up抽卡",
                "lah 模擬 up 抽卡"):
            if not await get_setting(group.id, Setting.gacha_simulator):
                return MessageItem(
                    MessageChain.create([Plain(text=f"模拟抽卡功能已被禁用。")]),
                    QuoteSource()
                )
            # await update_user_call_count_plus(group, member, UserCalledCount.functions, "functions")
            # return MessageItem(
            #     MessageChain.create(await LiveAHeroSimulatorHandler.get_simulation(member, group, up=True)),
            #     QuoteSource()
            # )
            return MessageItem(MessageChain.create([Plain(text=f"UP 卡池已关闭。")]), QuoteSource())
        elif message.asDisplay().startswith("吃桃模式#"):
            if member.permission == MemberPerm.Member and not await user_permission_require(group, member, 2):
                return MessageItem(MessageChain.create([Plain(text=f"权限不足。")]), QuoteSource())
            _, times = message.asDisplay().split("#")
            try:
                times = int(times)
                if times < 0:
                    return MessageItem(MessageChain.create([Plain(text=f"参数有误。")]), QuoteSource())
            except ValueError:
                return MessageItem(MessageChain.create([Plain(text=f"参数有误。")]), QuoteSource())
            LiveAHeroSimulatorHandler.peach_mode.update({group.id: times})
            return MessageItem(MessageChain.create([Plain(text=f"抽卡吃桃模式已启用 {times} 次。")]), QuoteSource())
        else:
            return None

    @staticmethod
    async def get_simulation(member: Member, group: Group, limited: bool = False, up: bool = False):
        fetch = await orm.fetchall(
            select(
                Setting.lah_simulation_cost,
                Setting.lah_simulation_limit
            ).where(Setting.group_id == group.id))
        amount = 1000 if not fetch else fetch[0][0]
        limit = -1 if not fetch else fetch[0][1]
        wallet = await WalletHandler.get_balance(group, member)
        if limit < -1:
            return [Plain(text=f"抽取次数限制非法({limit} 次)。")]
        fetch_user = await orm.fetchall(
            select(
                LiveAHeroSimulator.simulate_times,
                LiveAHeroSimulator.last_date,
                LiveAHeroSimulator.free_tokens,
                LiveAHeroSimulator.three_stars_hero,
                LiveAHeroSimulator.four_stars_hero,
                LiveAHeroSimulator.five_stars_hero,
                LiveAHeroSimulator.three_stars_sk,
                LiveAHeroSimulator.four_stars_sk,
                LiveAHeroSimulator.total_times
            ).where(LiveAHeroSimulator.qq == member.id, LiveAHeroSimulator.group == group.id)
        )
        simulate_times = 0 if not fetch_user else fetch_user[0][0]
        last_date = 0 if not fetch_user else fetch_user[0][1]
        free_tokens = 0 if not fetch_user else fetch_user[0][2]
        three_stars_hero = 0 if not fetch_user else fetch_user[0][3]
        four_stars_hero = 0 if not fetch_user else fetch_user[0][4]
        five_stars_hero = 0 if not fetch_user else fetch_user[0][5]
        three_stars_sk = 0 if not fetch_user else fetch_user[0][6]
        four_stars_sk = 0 if not fetch_user else fetch_user[0][7]
        total_times = 0 if not fetch_user else fetch_user[0][8]
        today = int(datetime.today().strftime('%Y%m%d'))
        if last_date != today:
            simulate_times = 0
            await orm.insert_or_update(
                LiveAHeroSimulator,
                [LiveAHeroSimulator.qq == member.id, LiveAHeroSimulator.group == group.id],
                {"qq": member.id,
                 "group": group.id,
                 "simulate_times": 0}
            )
        if simulate_times >= limit != -1:
            return [Plain(text=f"超出本群单日抽取限制 ({limit} 次)。")]
        else:
            if free_tokens != 0:
                used_token = True
            else:
                used_token = False
                if wallet - amount < 0:
                    return [Plain(text=f"硬币少于 {amount}，无法抽取十连！")]
            limited_times = 0
            up_times = 0
            peach_enabled = False
            result = IMG.open("statics/lah/back_new.png")
            frame_5 = IMG.open("statics/lah/frame_5.png").resize((108, 108), IMG.ANTIALIAS)
            frame_4 = IMG.open("statics/lah/frame_4.png").resize((108, 108), IMG.ANTIALIAS)
            frame_3 = IMG.open("statics/lah/frame_3.png").resize((108, 108), IMG.ANTIALIAS)
            sk_mask = IMG.open("statics/lah/sk_mask.png").resize((104, 103), IMG.ANTIALIAS)
            star = IMG.open("statics/lah/star.png").resize((12, 12), IMG.ANTIALIAS)
            star_grey = IMG.open("statics/lah/star_grey.png").resize((12, 12), IMG.ANTIALIAS)
            star_sk_3 = IMG.open("statics/lah/star_sk_3.png").resize((51, 16), IMG.ANTIALIAS)
            star_sk_4 = IMG.open("statics/lah/star_sk_4.png").resize((68, 16), IMG.ANTIALIAS)
            frame_sk_4 = IMG.open("statics/lah/frame_sk_4.png").resize((106, 107), IMG.ANTIALIAS)
            frame_sk_3 = IMG.open("statics/lah/frame_sk_3.png").resize((106, 107), IMG.ANTIALIAS)
            draw = ImageDraw.Draw(result)
            gacha_record = {
                "group_id": group.id,
                "member_id": member.id,
                "gacha": "lah",
                "is_ten": True,
                "time": datetime.now(),
                "a": "",
                "b": "",
                "c": "",
                "d": "",
                "e": "",
                "f": "",
                "g": "",
                "h": "",
                "i": "",
                "j": "",
            }
            for i_lah in range(0, 10):
                luck = randrange(100) + 1
                if group.id in LiveAHeroSimulatorHandler.peach_mode.keys():
                    if LiveAHeroSimulatorHandler.peach_mode[group.id] > 0:
                        peach_enabled = True
                        luck = 0
                        for peach_times in range(0, 10):
                            luck = max(luck, randrange(100) + 1)
                if i_lah <= 8:
                    if luck <= 35:
                        pool = three_stars
                        frame_to_use = frame_3
                        star_amount = 3
                        is_hero = True
                        three_stars_hero += 1
                    elif 35 < luck <= 80:
                        if limited:
                            if (randrange(100) + 1) <= 80 and three_sk_limited:
                                pool = three_sk_limited
                                limited_times += 1
                            else:
                                pool = three_sk
                        else:
                            pool = three_sk
                        frame_to_use = frame_sk_3
                        star_amount = 3
                        is_hero = False
                        three_stars_sk += 1
                    elif 80 < luck <= 88:
                        if limited:
                            if (randrange(100) + 1) <= 80 and four_stars_limited:
                                pool = four_stars_limited
                                limited_times += 1
                            else:
                                pool = four_stars
                        elif up:
                            if (randrange(100) + 1) <= 50 and four_stars_up:
                                pool = four_stars_up
                                up_times += 1
                            else:
                                pool = four_stars
                        else:
                            pool = four_stars
                        frame_to_use = frame_4
                        star_amount = 4
                        is_hero = True
                        four_stars_hero += 1
                    elif 88 < luck <= 98:
                        if limited:
                            if (randrange(100) + 1) <= 80 and four_sk_limited:
                                pool = four_sk_limited
                                limited_times += 1
                            else:
                                pool = four_sk
                        elif up:
                            if (randrange(100) + 1) <= 50 and four_sk_up:
                                pool = four_sk_up
                                up_times += 1
                            else:
                                pool = four_sk
                        else:
                            pool = four_sk
                        frame_to_use = frame_sk_4
                        star_amount = 4
                        is_hero = False
                        four_stars_sk += 1
                    else:
                        if limited:
                            if (randrange(100) + 1) <= 60 and five_stars_limited:
                                pool = five_stars_limited
                                limited_times += 1
                            else:
                                pool = five_stars
                        elif up:
                            if (randrange(100) + 1) <= 50 and five_stars_up:
                                pool = five_stars_up
                                up_times += 1
                            else:
                                pool = five_stars
                        else:
                            pool = five_stars
                        frame_to_use = frame_5
                        star_amount = 5
                        is_hero = True
                        five_stars_hero += 1
                else:
                    if luck <= 96:
                        if limited:
                            if (randrange(100) + 1) <= 80 and four_stars_limited:
                                pool = four_stars_limited
                                limited_times += 1
                            else:
                                pool = four_stars
                        elif up:
                            if (randrange(100) + 1) <= 50 and four_stars_up:
                                pool = four_stars_up
                                up_times += 1
                            else:
                                pool = four_stars
                        else:
                            pool = four_stars
                        frame_to_use = frame_4
                        star_amount = 4
                        is_hero = True
                        four_stars_hero += 1
                    else:
                        if limited:
                            if (randrange(100) + 1) <= 60 and five_stars_limited:
                                pool = five_stars_limited
                                limited_times += 1
                            else:
                                pool = five_stars
                        elif up:
                            if (randrange(100) + 1) <= 50 and five_stars_up:
                                pool = five_stars_up
                                up_times += 1
                            else:
                                pool = five_stars
                        else:
                            pool = five_stars
                        frame_to_use = frame_5
                        star_amount = 5
                        is_hero = True
                        five_stars_hero += 1
                choice = random.sample(pool, 1)[0]
                gacha_record[list(gacha_record.keys())[i_lah + 5]] = choice
                choice_unprocessed = choice.split("/")[2]
                if is_hero:
                    frame_back = IMG.open(
                        os.getcwd() + f"/statics/lah/back_{hero_data[choice_unprocessed]}.png"
                    ).resize((110, 110), IMG.ANTIALIAS)
                    hero_element = IMG.open(
                        os.getcwd() + f"/statics/lah/element_{hero_data[choice_unprocessed]}.png"
                    ).resize((16, 16), IMG.ANTIALIAS)
                    chosen = IMG.open(os.getcwd() + "/statics/lah" + choice).resize((96, 96), IMG.ANTIALIAS)
                    result.paste(frame_back, frame_location[i_lah], mask=frame_back)
                    result.paste(chosen, card_location[i_lah], mask=chosen)
                    result.paste(frame_to_use, frame_location[i_lah], mask=frame_to_use)
                    draw.rectangle((
                        (frame_location[i_lah][0] + 4),
                        (frame_location[i_lah][1] + 4),
                        (frame_location[i_lah][0] + 23),
                        (frame_location[i_lah][1] + 23)
                    ), fill=(255, 255, 255))
                    result.paste(hero_element, (frame_location[i_lah][0] + 6, frame_location[i_lah][1] + 6),
                                 mask=hero_element)
                    star_x = star_location[i_lah][0]
                    star_y = star_location[i_lah][1]
                    for j_lah in range(0, 6):
                        if j_lah < star_amount:
                            result.paste(star, (star_x, star_y), mask=star)
                        else:
                            result.paste(star_grey, (star_x, star_y), mask=star_grey)
                        star_x += 12
                else:
                    frame_back = IMG.open(
                        os.getcwd() + f"/statics/lah/back_sk_{star_amount}.png"
                    ).resize((108, 109), IMG.ANTIALIAS)
                    chosen = IMG.open(os.getcwd() + "/statics/lah" + choice).resize((104, 103), IMG.ANTIALIAS)
                    sidekick = IMG.new("RGBA", (104, 103), (255, 255, 255, 0))
                    sidekick.paste(chosen, (0, 0), mask=sk_mask)
                    result.paste(frame_back, sk_base_location[i_lah], mask=frame_back)
                    result.paste(sidekick, sk_mask_location[i_lah], mask=sidekick)
                    result.paste(frame_to_use, sk_frame_location[i_lah], mask=frame_to_use)
                    star_x = sk_three_stars_location[i_lah][0] if star_amount == 3 else sk_four_stars_location[i_lah][0]
                    star_y = sk_three_stars_location[i_lah][1] if star_amount == 3 else sk_four_stars_location[i_lah][1]
                    result.paste(
                        star_sk_3 if star_amount == 3 else star_sk_4,
                        (star_x, star_y),
                        mask=star_sk_3 if star_amount == 3 else star_sk_4
                    )
            font_size = [10, 12, 12, 14]
            font_position = [[(316, 1016), "rs"], [(490, 185), "rs"], [(490, 156), "rs"], [(38, 168), "mm"]]
            font_color = [[(0, 0, 0), (255, 255, 255)], [None, (0, 0, 0)], [None, (0, 0, 0)], [None, (255, 255, 255)]]
            if len(str(amount)) > 9:
                font_text1 = "超级贵"
            else:
                font_text1 = str(amount) if free_tokens - 1 <= 0 else "Free"
            if len(str(wallet)) > 9:
                font_text2 = "超多币"
            else:
                font_text2 = str(wallet)
            if len(str(free_tokens)) > 9:
                font_text3 = "超多次"
            else:
                font_text3 = str(free_tokens)
            if len(str(limit)) > 3:
                font_text4 = "多"
            else:
                font_text4 = str(limit - 1) if limit != -1 else "inf"
            font_text = [font_text1, font_text2, font_text3, font_text4]
            for font_index in range(len(font_position)):
                font = ImageFont.truetype(
                    f"{os.getcwd()}/statics/fonts/ArialEnUnicodeBold.ttf",
                    font_size[font_index])
                offset = 1
                if type(font_color[font_index][0]) == tuple:
                    for offset_x in range(offset * -1, offset + 1):
                        for offset_y in range(offset * -1, offset + 1):
                            draw.text((font_position[font_index][0][0] + offset_x,
                                       font_position[font_index][0][1] + offset_y), font_text[font_index],
                                      font_color[font_index][0][0], anchor=font_position[font_index][1], font=font)
                draw.text((font_position[font_index][0][0], font_position[font_index][0][1]), font_text[font_index],
                          font_color[font_index][1], anchor=font_position[font_index][1], font=font)
            if peach_enabled:
                peach_watermark = IMG.open(f"{os.getcwd()}/statics/lah/peach.png")
                result.paste(peach_watermark, (360, 300), peach_watermark)
            output = BytesIO()
            result.save(output, format='png')
            await WalletHandler.charge(group, member, amount, "Live a Hero 模拟抽卡")
            if not peach_enabled:
                await orm.insert_or_update(
                    LiveAHeroSimulator,
                    [LiveAHeroSimulator.qq == member.id, LiveAHeroSimulator.group == group.id],
                    {"qq": member.id,
                     "group": group.id,
                     "last_date": today,
                     "simulate_times": simulate_times + 1,
                     "free_tokens": (free_tokens - 1) if free_tokens - 1 > 0 else 0,
                     "three_stars_hero": three_stars_hero,
                     "four_stars_hero": four_stars_hero,
                     "five_stars_hero": five_stars_hero,
                     "three_stars_sk": three_stars_sk,
                     "four_stars_sk": four_stars_sk,
                     "total_times": total_times + 1}
                )
                await orm.add(
                    GachaSimulatorRecord,
                    gacha_record
                )
            else:
                LiveAHeroSimulatorHandler.peach_mode[group.id] = LiveAHeroSimulatorHandler.peach_mode[group.id] - 1
            return_list = [Image(data_bytes=output.getvalue())]
            return return_list

    @staticmethod
    async def get_summary(member: Member, group: Group):
        fetch_user = await orm.fetchall(
            select(
                LiveAHeroSimulator.three_stars_hero,
                LiveAHeroSimulator.four_stars_hero,
                LiveAHeroSimulator.five_stars_hero,
                LiveAHeroSimulator.three_stars_sk,
                LiveAHeroSimulator.four_stars_sk,
                LiveAHeroSimulator.total_times
            ).where(LiveAHeroSimulator.qq == member.id, LiveAHeroSimulator.group == group.id)
        )
        if not fetch_user:
            return [Plain(text=f"没有你的 LAH 模拟抽卡记录。")]
        three_s_h = fetch_user[0][0]
        four_s_h = fetch_user[0][1]
        five_s_h = fetch_user[0][2]
        three_s_sk = fetch_user[0][3]
        four_s_sk = fetch_user[0][4]
        total_times = fetch_user[0][5]
        three_s_h_per = round((three_s_h / total_times * 10), 2)
        four_s_h_per = round((four_s_h / total_times * 10), 2)
        five_s_h_per = round((five_s_h / total_times * 10), 2)
        three_s_sk_per = round((three_s_sk / total_times * 10), 2)
        four_s_sk_per = round((100 - three_s_h_per - four_s_h_per - five_s_h_per - three_s_sk_per), 2)
        return [Plain(text=f"你的 LAH 模拟抽卡总结如下：\n"
                           f"三星英雄数：{three_s_h} ({three_s_h_per}%)\n"
                           f"四星英雄数：{four_s_h} ({four_s_h_per}%)\n"
                           f"五星英雄数：{five_s_h} ({five_s_h_per}%)\n"
                           f"三星助手数：{three_s_sk} ({three_s_sk_per}%)\n"
                           f"四星助手数：{four_s_sk} ({four_s_sk_per}%)\n"
                           f"总抽取次数：{total_times * 10}")]