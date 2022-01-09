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
from SAGIRIBOT.ORM.AsyncORM import orm, GNNUCredit, GNNUCreditHistory
from SAGIRIBOT.decorators import switch, blacklist

saya = Saya.current()
channel = Channel.current()


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def gnnu_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await GNNUCreditHandler.handle(app, message, group, member):
        await GroupMessageSender(result.strategy).send(app, result.message, message, group, member)


class GNNUCreditHandler(AbstractHandler):
    __name__ = "GNNUCreditHandler"
    __description__ = "赣南师范大学学分 Handler"
    __usage__ = "None"

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group, member: Member):
        if message.asDisplay().startswith("#绑定#"):
            _, __, student_id, student_name = message.asDisplay().split("#", maxsplit=3)
            try:
                student_id = int(student_id)
                return MessageItem(MessageChain.create(
                    await GNNUCreditHandler.update_qq(member, student_id, student_name)
                ), QuoteSource(GroupStrategy()))
            except ValueError:
                return MessageItem(MessageChain.create([
                    Plain(text=f"输入学号 ({student_id}) 有误，请检查您的输入")
                ]), QuoteSource(GroupStrategy()))
        elif message.asDisplay() == "我的实践学分":
            return MessageItem(MessageChain.create(
                await GNNUCreditHandler.get_by_qq(member)
            ), QuoteSource(GroupStrategy()))

    @staticmethod
    async def update_qq(member: Member, student_id: int, student_name: str):
        bind_check = await orm.fetchall(
            select(
                GNNUCredit.bind
            ).where(GNNUCredit.qq == member.id)
        )
        id_check = await orm.fetchall(
            select(
                GNNUCredit.bind
            ).where(GNNUCredit.id == student_id)
        )
        if bind_check:
            if bind_check[0][0]:
                return [Plain(text=f"您已完成过绑定，请联系机器人管理员更改绑定。")]
        if id_check:
            if id_check[0]:
                return [Plain(text=f"该学号已被绑定，请联系机器人管理员更改绑定。")]
        await orm.insert_or_update(
            GNNUCredit,
            [GNNUCredit.id == student_id],
            {"qq": member.id,
             "id": student_id,
             "name": student_name,
             "bind": 1
             }
        )
        return [Plain(text=f"已绑定至学号 {student_id}。")]

    @staticmethod
    async def get_by_qq(member: Member):
        fetch_qq = await orm.fetchall(
            select(
                GNNUCredit.id
            ).where(GNNUCredit.qq == member.id)
        )
        if not fetch_qq:
            return [Plain(text=f"账号 {member.id} 未绑定学号，请按如下示例绑定：\n#绑定#211110000#张三")]
        student_id = fetch_qq[0][0]
        print(student_id)
        if query := await GNNUCreditHandler.query(student_id):
            return query
        return "查询失败，请联系机器人管理员。"

    @staticmethod
    async def get_by_name(student_name: str):
        fetch_qq = await orm.fetchall(
            select(
                GNNUCredit.id
            ).where(GNNUCredit.name == student_name)
        )
        if not fetch_qq:
            return [Plain(text=f"用户 {student_name} 未绑定学号，请按如下示例绑定：\n#绑定#211110000#张三")]
        student_id = fetch_qq[0][0]
        if query := await GNNUCreditHandler.query(student_id):
            return query
        return "查询失败，请联系机器人管理员。"

    @staticmethod
    async def query(student_id: int):
        fetch = await orm.fetchall(
            select(
                GNNUCreditHistory.id,
                GNNUCreditHistory.record,
                GNNUCreditHistory.reason,
                GNNUCreditHistory.date,
                GNNUCreditHistory.validated
            ).where(GNNUCreditHistory.student == student_id)
        )
        print(fetch)
        if not fetch:
            return [Plain(text=f"学号 {student_id} 的实践学分为 0（无记录）。")]
        detail = []
        total_credit = 0
        for i in range(len(fetch)):
            total_credit += round(float(fetch[i][1]), 1)
            detail.append(Plain(text=f"\n#{i + 1} 于"
                                     f"{fetch[i][3]}因{fetch[i][2]}"
                                     f"获得学分{fetch[i][1]}分"
                                     f"（{'已验证' if fetch[i][4] else '未验证'}，记录编号 #{fetch[i][0]}）"))
        query = [Plain(text=f"学号 {student_id} 的实践学分为 {round(total_credit, 1)}。\n"
                            f"----------\n"
                            f"实践学分明细如下：")]
        query.extend(detail)
        return query
