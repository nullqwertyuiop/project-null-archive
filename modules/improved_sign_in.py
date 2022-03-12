import random
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
from graia.ariadne.message.parser.twilight import Twilight, UnionMatch
from graia.ariadne.model import Friend
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
from sqlalchemy import select

from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import QuoteSource
from sagiri_bot.orm.async_orm import orm, MigrateProstitute, Setting, Prostitute
from sagiri_bot.decorators import switch, blacklist
from sagiri_bot.utils import group_setting, HelpPage, HelpPageElement
from modules.wallet import Wallet

saya = Saya.current()
channel = Channel.current()

channel.name("ImprovedSignIn")
channel.author("nullqwertyuiop")
channel.description("猜")

race_list = {
    "人类": "human",
    "human": "human",
    "Human": "human",
    "兽人": "kemono",
    "kemono": "kemono",
    "Kemono": "kemono",
    "福瑞": "kemono",
    "毛茸茸": "kemono",
    "furry": "kemono",
    "Furry": "kemono",
    "胶液": "latex",
    "胶兽": "latex",
    "latex": "latex",
    "Latex": "latex",
}
subject_list = {
    "self": "self",
    "自己": "self",
    "自身": "self",
    "client": "client",
    "客人": "client",
    "客户": "client"
}
available_race_list = ["人类", "兽人"]
available_subject_list = ["自己", "客人"]
human_human_pay = 50
human_kemono_pay = 500
human_latex_pay = 0
kemono_human_pay = 100
kemono_kemono_pay = 100
kemono_latex_pay = 0
latex_pay = 0
extra_pay_ratio = 2
arrest_text = {"none": [
    "你打算挑战自我，在局子门口接客，不出意外的是，你被逮了。",
    "尽管你今天非常努力，但是你还是没接到客人，还被逮住了。",
    "你发大水把客人全冲走了，逮捕你的人逆流而上把你逮了。",
    "你今天刚开张，就被举报了，不出意外的是，你被逮了。"
],
    "common": [
        "你今天在接客的时候被逮住了。",
        "你今天在接客的时候被钓鱼执法逮住了。"
    ],
    "many": [
        "你今天接了很多客人，自信放光芒，别人顺着光芒来把你逮住了。",
        "你今天格外的骚气，接了很多客人，可惜便衣客人把你逮了。"
    ]}

twilight = Twilight(
    [
        UnionMatch("卖铺", "站街", "开张", "賣鋪", "站街", "開張", "站街排行榜")
    ]
)


@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[twilight]
    )
)
async def improved_sign_in_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await ImprovedSignIn.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class ImprovedSignIn(AbstractHandler):
    __name__ = "ImprovedSignIn"
    __description__ = "卖铺汇总"
    __usage__ = "None"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if message.asDisplay() in ("卖铺", "站街", "开张", "賣鋪", "站街", "開張"):
            if not await group_setting.get_setting(group.id, Setting.prostitute):
                return None
            return MessageItem(MessageChain.create([
                # Image(data_bytes=await ImprovedSignIn.get_avatar(member.id)),
                Plain(text=await ImprovedSignIn.prostitute_legacy(group, member))]),
                QuoteSource())
        elif message.asDisplay() == "站街排行榜":
            return await ImprovedSignIn.prostitute_toplist(app, group, member)
        # elif message.asDisplay() in ("卖铺测试", "站街测试", "开张测试"):
        #     if not await group_setting.get_setting(group.id, Setting.prostitute):
        #         return None
        #     if not await user_permission_require(group, member, 4):
        #         return MessageItem(MessageChain.create([Plain(text="权限不足，无法进行该测试，可申请加入测试计划。")]),
        #                            QuoteSource())
        #     result = []
        #     # if migrate_result := await ImprovedSignIn.migrate_check(member):
        #     #     result.extend(migrate_result)
        #     result.extend(await ImprovedSignIn.prostitute(member, group))
        #     return MessageItem(MessageChain.create(result), QuoteSource())
        # elif re.match("更改物种#.*#.*", message.asDisplay() or re.match("更改物種#.*#.*", message.asDisplay())):
        #     if not await group_setting.get_setting(group.id, Setting.prostitute):
        #         return None
        #     try:
        #         _, subject, race = message.asDisplay().split("#")
        #         result = [await ImprovedSignIn.update_race(member, group, subject, race)]
        #         return MessageItem(MessageChain.create(result), QuoteSource())
        #     except AccountMuted:
        #         logger.error(f"Bot 在群 <{group.name}> 被禁言，无法发送！")
        #         return None

    @staticmethod
    async def sign_in(member: Member, group: Group):
        pass

    @staticmethod
    async def migrate_check(member: Member):
        migrate_check = await orm.fetchall(
            select(
                Prostitute.migrate
            ).where(Prostitute.qq == member.id))
        if not (migrate_check or migrate_check[0][0]):
            return None
        else:
            return Plain(text='请尽快迁移站街模块数据。\n迁移方法：发送 "迁移站街"')

    @staticmethod
    async def prostitute(member: Member, group: Group):
        result = []
        prefix = []
        suffix = []
        fetch = await orm.fetchall(
            select(
                MigrateProstitute.self_race_edit,
                MigrateProstitute.last_date,
                MigrateProstitute.self_race,
                MigrateProstitute.client_race,
                MigrateProstitute.pay,
                MigrateProstitute.client,
                MigrateProstitute.frequency,
                MigrateProstitute.limit_date,
                MigrateProstitute.history_total
            ).where(MigrateProstitute.qq == member.id, MigrateProstitute.group == group.id))
        if not fetch:
            try:
                await orm.insert_or_update(
                    MigrateProstitute,
                    [MigrateProstitute.qq == member.id, MigrateProstitute.group == group.id],
                    {
                        "group": group.id,
                        "qq": member.id,
                        "client": 0,
                        "last_date": 0,
                        "pay": 0,
                        "self_race": "human",
                        "client_race": "human",
                        "frequency": 0,
                        "self_race_edit": -1,
                        "limit_date": 0,
                        "history_total": 0
                    }
                )
                prefix.append(Plain(text='初始化成功，已填入默认数据。\n可发送 "更改物种#对象#物种" 更改物种。'))
                return result
            except:
                prefix.append(Plain(text="初始化失败，请联系机器人管理员。"))
                return result
        if fetch[0][0] != 1:
            prefix.append(Plain(text='未选择自身物种，此处使用默认物种 "人类"\n可发送 "更改物种#对象#物种" 更改物种'))
        if len(prefix):
            result.extend(prefix)
            result.append(Plain(text="----------"))
        # result.append(Image(data_bytes=await ImprovedSignIn.get_avatar(member.id)))
        client = fetch[0][2]
        last_date = fetch[0][3]
        pay = fetch[0][4]
        self_race = fetch[0][5]
        client_race = fetch[0][6]
        frequency = fetch[0][7]
        limit = fetch[0][8]
        if limit >= int(datetime.today().strftime('%Y%m%d')):
            result.append(Plain(text="你被橄榄的β还没恢复，没办法接客！"))
            return result
        if self_race == "human":
            if frequency == 1 and last_date == datetime.today().strftime('%Y%m%d'):
                result.append(Plain(text=f"你今天已经开张过了，小心β烂掉！\n现共接客： {client} 人，\n现有工资： {pay} 硬币"))
                return result
            if client_race == "human":
                luck = randrange(101)
                today_client = randrange(16)
                client = client + today_client
                today_pay = 0
                for i in range(0, today_client):
                    today_pay = today_pay + (randrange(10) + 1) * human_human_pay
                pay = pay + today_pay
                if luck <= 25:
                    luck = randrange(101)
                    if luck <= 50:
                        pay = pay - (randrange(3) + 1) * 1000
                        suffix.append(await ImprovedSignIn.arrest_common(today_client))
                    elif 55 >= luck > 50:
                        pay = pay - 1300
                        suffix.append(await ImprovedSignIn.arrest_zhouyinting(member, group))
                    elif 100 >= luck > 55:
                        pass
            elif client_race == "kemono":
                return Plain(text=f"[没写完的{self_race}+{client_race}部分]")
            elif client_race == "latex":
                return Plain(text=f"[没写完的{self_race}+{client_race}部分]")
        elif self_race == "kemono":
            return Plain(text=f"[没写完的{self_race}+{client_race}部分]")
        elif self_race == "latex":
            return Plain(text=f"[没写完的{self_race}+{client_race}部分]")
        if len(suffix):
            result.append(Plain(text="----------"))
            result.append(Plain(text="本次站街触发事件如下："))
            result.extend(suffix)
        return result

    @staticmethod
    async def prostitute_human():
        pass

    @staticmethod
    async def arrest_common(today_clients: int):
        if today_clients == 0:
            text = random.choice(arrest_text["none"])
        elif today_clients >= 10:
            text = random.choice(arrest_text["many"])
        else:
            text = random.choice(arrest_text["common"])
        return Plain(text=text)

    @staticmethod
    async def extra_common(today_client: int):
        return Plain(text="")

    @staticmethod
    async def arrest_zhouyinting(member: Member, group: Group):
        # 被正直清纯女高中生阴婷告发
        # return Plain(text="正义的女高中生小阴见不得任何淫乱之事，你被小阴带来的警察们带回派出所拘留，罚款1300β\n【获得debuff：阴婷的凝视，连续三天被捕概率提升25%且头像变为阴婷。】")
        return Plain(text="正义的女高中生小阴见不得任何淫乱之事，你被小阴带来的警察们带回派出所拘留，罚款1300β\n【获得 debuff: null。】")

    @staticmethod
    async def wrecked_beta_furry(member: Member, group: Group, luck: int, client_type: str):
        # 贝塔损伤，Furry
        kind_list = ["虎", "狼", "犬", "狐狸", "鸟"]
        return Plain(
            text=f"你接待的最后一位顾客是名健硕的{random.choice(kind_list)}兽人，他那超出规格的毛茸茸大几把把你捅得够呛，你爽得魂飞天外，但是β也撕裂了。【获得 debuff: β损伤，第二天不能再接客。】")

    @staticmethod
    async def prostitute_legacy(group: Group, member: Member):
        fetch = await orm.fetchall(
            select(
                Prostitute.client,
                Prostitute.last_date
            ).where(Prostitute.qq == member.id, Prostitute.group_id == group.id))
        mig_merge = False
        if not fetch:
            fetch = await orm.fetchall(
                select(
                    Prostitute.client,
                    Prostitute.last_date,
                    Prostitute.pay
                ).where(Prostitute.qq == member.id, Prostitute.group_id == 0))
            if fetch:
                await Wallet.update(group, member, fetch[0][2], "站街模块迁移")
                await orm.insert_or_update(
                    Prostitute,
                    [Prostitute.qq == member.id],
                    {"qq": member.id,
                     "group_id": -1,
                     "client": fetch[0][0],
                     "pay": fetch[0][2],
                     "last_date": fetch[0][1]
                     }
                )
                await orm.delete(
                    Prostitute,
                    [Prostitute.qq == member.id, Prostitute.group_id == 0]
                )
                mig_merge = True
                clients = int(fetch[0][0])
                date = int(fetch[0][1])
            else:
                clients = 0
                date = 0
        else:
            clients = int(fetch[0][0])
            date = int(fetch[0][1])
        wallet = await Wallet.get_balance(group, member)
        pay = wallet if wallet else 0
        current_date = int(datetime.today().strftime('%Y%m%d'))
        if date == current_date:
            if mig_merge:
                await orm.insert_or_update(
                    Prostitute,
                    [Prostitute.qq == member.id, Prostitute.group_id == group.id],
                    {"qq": member.id,
                     "group_id": group.id,
                     "client": clients,
                     "pay": pay,
                     "last_date": current_date}
                )
            text = f"你今天已经开张过了，小心β烂掉！\n现共接客： {clients} 人，\n现有工资： {pay} 硬币"
            return text
        else:
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            arrest = randrange(101)
            today_clients = randrange(11)
            clients = clients + today_clients
            today_pay = 0
            for i in range(0, today_clients):
                today_pay = today_pay + (randrange(20) + 1) * 50
            pay = pay + today_pay
            if arrest <= 25:
                luck = randrange(2)
                if luck != 1:
                    lost = (randrange(3) + 1) * 1000
                    pay = pay - lost
                    try:
                        await orm.insert_or_update(
                            Prostitute,
                            [Prostitute.qq == member.id, Prostitute.group_id == group.id],
                            {"qq": member.id,
                             "group_id": group.id,
                             "client": clients,
                             "pay": pay,
                             "last_date": current_date}
                        )
                        await Wallet.update(group, member, (today_pay - lost), "站街")
                        if today_clients == 0:
                            text = f"尽管你今天没接到客人，你还是被逮住了，被罚了 {lost} 块\n卖铺时间：{current_time}\n" \
                                   f"现共接客： {clients} 人，\n现有工资 {pay} 硬币"
                        elif today_clients >= 10:
                            text = f"你今天接到了 {today_clients} 客人，得了 {today_pay} 硬币，但是你自信放光芒，" \
                                   f"别人顺着光芒来把你逮住了，罚了你 {lost} 块\n卖铺时间：{current_time}\n" \
                                   f"现共接客： {clients} 人，\n现有工资 {pay} 硬币"
                        else:
                            text = f"你在接客的时候被逮住了，尽管你已经接了 {today_clients} 个客人，得了 {today_pay} 硬币，" \
                                   f"你还是被罚了 {lost} 块\n卖铺时间：{current_time}\n现共接客： {clients} 人，\n" \
                                   f"现有工资 {pay} 硬币"
                        return text
                    except:
                        text = "卖铺出错，请联系管理员。"
                        return text
                else:
                    bonus_client = (randrange(3) + 1)
                    clients = clients + bonus_client
                    bonus = 0
                    for j in range(0, bonus_client):
                        bonus = bonus + (randrange(5) + 1) * 250
                    today_pay = today_pay + bonus
                    pay = pay + bonus
                    try:
                        await orm.insert_or_update(
                            Prostitute,
                            [Prostitute.qq == member.id, Prostitute.group_id == group.id],
                            {"qq": member.id,
                             "group_id": group.id,
                             "client": clients,
                             "pay": pay,
                             "last_date": current_date}
                        )
                        await Wallet.update(group, member, today_pay, "站街")
                        if today_clients == 0:
                            text = f"尽管你今天没接到客，你还是被逮住了，但是你以独特的骚劲儿令逮捕你的人瞠目结舌，" \
                                   f"你又接了 {bonus_client} 个，工资 {today_pay} 硬币\n" \
                                   f"卖铺时间：{current_time}\n现共接客： {clients} 人，\n" \
                                   f"现有工资 {pay} 硬币"
                        else:
                            text = f"你在接客的时候被逮住了，但是你以独特的骚劲儿令逮捕你的人瞠目结舌，" \
                                   f"你在接了 {today_clients} 个客人后又接了 {bonus_client} 个，" \
                                   f"工资 {today_pay} 硬币\n卖铺时间：{current_time}\n现共接客： {clients} 人，\n" \
                                   f"现有工资 {pay} 硬币"
                        return text
                    except:
                        text = "卖铺出错，请联系管理员。"
                        return text
            else:
                try:
                    await orm.insert_or_update(
                        Prostitute,
                        [Prostitute.qq == member.id, Prostitute.group_id == group.id],
                        {"qq": member.id,
                         "group_id": group.id,
                         "client": clients,
                         "pay": pay,
                         "last_date": current_date})
                    await Wallet.update(group, member, today_pay, "站街")
                    if today_clients == 0:
                        text = f"可惜，今天你没有接到客人，\n卖铺时间：{current_time}\n现共接客： {clients} 人，\n" \
                               f"现有工资 {pay} 硬币"
                    elif today_clients >= 8:
                        text = f"你独领风骚，这条街的客户全来了你这，你今天接客 {today_clients} 人，\n工资 {today_pay} 硬币\n" \
                               f"卖铺时间：{current_time}\n现共接客 {clients} 人，\n现有工资： {pay} 硬币"
                    else:
                        text = f"卖铺成功！\n本次开张接到 {today_clients} 个客人，获得工资 {today_pay} 硬币\n" \
                               f"卖铺时间：{current_time}\n现共接客 {clients} 人，\n现有工资 {pay} 硬币"
                    return text
                except:
                    text = "卖铺出错，请联系管理员。"
                    return text

    @staticmethod
    async def update_race(member: Member, group: Group, subject: str, prompt: str):
        try:
            subject = subject_list[subject]
        except KeyError:
            available_subject = ""
            count = 0
            for i in available_subject_list:
                available_subject = (available_subject + "、" if count != 0 else available_subject) + i
                count += 1
            return Plain(text=f"更新种族失败！\n目前更改种族的对象有：\n{available_subject}")
        check = await orm.fetchall(
            select(
                MigrateProstitute.self_race_edit
            ).where(
                MigrateProstitute.qq == member.id,
                MigrateProstitute.group == group.id))
        if not check:
            check = [[-1]]
        try:
            race = race_list[prompt]
        except KeyError:
            available_race = ""
            count = 0
            for i in available_race_list:
                available_race = (available_race + "、" if count != 0 else available_race) + i
                count += 1
            return Plain(text=f"更新种族失败！\n目前可用的种族有：\n{available_race}")
        if subject == "self":
            if check[0][0] == -1:
                available_race = ""
                count = 0
                for i in available_race_list:
                    available_race = (available_race + "、" if count != 0 else available_race) + i
                    count += 1
                await orm.insert_or_update(
                    MigrateProstitute,
                    [MigrateProstitute.qq == member.id, MigrateProstitute.group == group.id],
                    {
                        "qq": member.id,
                        "group": group.id,
                        "self_race_edit": 0}
                )
                return Plain(text=f"修改物种后无法通过该指令再次修改，请慎重选择！\n默认 {subject} 的种族为 人类，\n"
                                  f"目前可用的种族有：\n{available_race}\n本次未进行任何处理，可重新发送指令修改")
            elif check[0][0] == 1:
                return Plain(text="你已经选好了自己的物种，无法再进行修改！")
            await orm.insert_or_update(
                MigrateProstitute,
                [MigrateProstitute.qq == member.id, MigrateProstitute.group == group.id],
                {
                    "qq": member.id,
                    "group": group.id,
                    "self_race": race,
                    "self_race_edit": 1}
            )
        elif subject == "client":
            await orm.insert_or_update(
                MigrateProstitute,
                [MigrateProstitute.qq == member.id, MigrateProstitute.group == group.id],
                {
                    "qq": member.id,
                    "group": group.id,
                    "client_race": race}
            )
        return Plain(text=f"更新 {'自己' if subject == 'self' else '客人'} 种族为 {prompt} 成功！")

    @staticmethod
    async def prostitute_toplist(app: Ariadne, group: Group, member: Member, scale: str = "total"):
        if fetch := await orm.fetchall(
            select(
                Prostitute.client,
                Prostitute.qq
            ).where(
                Prostitute.group_id == group.id
            ).order_by(Prostitute.client.desc())
        ):
            cap = 10 if len(fetch) >= 10 else len(fetch)
            toplist = [Plain(text=f"本群十佳站街排行榜")]
            for index in range(cap):
                user = await app.getMember(group, fetch[index][1])
                user = user.name if user else fetch[index][1]
                if fetch[index][0] == 0:
                    continue
                toplist.append(Plain(text=f"\n{index + 1}. {user}：{fetch[index][0]} 人"))
            return MessageItem(MessageChain.create(toplist), QuoteSource())

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


class HelpYouSearchHelp(HelpPage):
    __description__ = "站街"
    __trigger__ = "站街"
    __category__ = 'hidden'
    __switch__ = Setting.prostitute
    __icon__ = "beta"

    def __init__(self, group: Group = None, member: Member = None, friend: Friend = None):
        super().__init__()
        self.__help__ = None
        self.group = group
        self.member = member
        self.friend = friend

    async def compose(self):
        if self.group or self.member:
            if not await group_setting.get_setting(self.group.id, Setting.prostitute):
                status = HelpPageElement(icon="toggle-switch-off", text="已经关噜！")
            else:
                status = HelpPageElement(icon="toggle-switch", text="已经开惹")
        else:
            status = HelpPageElement(icon="close", text="暂不支持")
        self.__help__ = [
            HelpPageElement(icon=self.__icon__, text="站街", is_title=True),
            HelpPageElement(text="清者自清，看不懂什么意思很正常"),
            status,
            HelpPageElement(icon="cash", text="每天可使用本功能获得一定数量的硬币"),
            HelpPageElement(icon="pound-box", text="更改设置需要管理员权限\n"
                                                   "发送\"打开站街开关\"或者\"关闭站街开关\"即可更改开关"),
            HelpPageElement(icon="lightbulb-on", text="使用示例：\n直接发送\"站街\"即可"),
            HelpPageElement(icon="alert-circle", text="不要站得到处都是！")
        ]
        super().__init__(self.__help__)
        return await super().compose()
