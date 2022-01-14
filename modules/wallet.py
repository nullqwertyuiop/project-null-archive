from datetime import datetime
from typing import Union

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
from sagiri_bot.orm.async_orm import orm, WalletDetail, WalletBalance
from sagiri_bot.decorators import switch, blacklist

saya = Saya.current()
channel = Channel.current()

channel.name("Wallet")
channel.author("nullqwertyuiop")
channel.description("钱包")


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def wallet_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await Wallet.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class Wallet(AbstractHandler):
    __name__ = "WalletBalance"
    __description__ = "WalletBalance"
    __usage__ = ""
    privilege = {
        "group": [],
        "member": []
    }

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if message.asDisplay() == "钱包":
            return await Wallet.get_balance(group, member, balance_only=False)
        else:
            return None

    @staticmethod
    async def get_balance(group: Union[Group, int], member: Union[Member, int], balance_only: bool = True):
        group_id = group.id if type(group) != int else group
        member_id = member.id if type(member) != int else member
        if wallet := await orm.fetchall(
                select(
                    WalletBalance.balance,
                    WalletBalance.time
                ).where(WalletBalance.group_id == group_id, WalletBalance.member_id == member_id)
        ):
            if balance_only:
                return int(wallet[-1][0])
            else:
                return MessageItem(MessageChain.create([Plain(text=f"你现在一共有硬币 {wallet[-1][0]} 枚。\n"
                                                                   f"最后一次于 {wallet[-1][1]} 更新。")]
                                                       ), QuoteSource())
        else:
            if balance_only:
                return 0
            else:
                return MessageItem(MessageChain.create([Plain(text="你现在一共有硬币 0 枚。")]
                                                       ), QuoteSource())

    @staticmethod
    async def update(group: Union[Group, int], member: Union[Member, int], record: int, reason: str = ""):
        group_id = group.id if type(group) != int else group
        member_id = member.id if type(member) != int else member
        if wallet := await orm.fetchall(
                select(
                    WalletBalance.balance
                ).where(WalletBalance.group_id == group_id, WalletBalance.member_id == member_id)
        ):
            balance = wallet[-1][0]
        else:
            balance = 0
        try:
            await orm.insert_or_update(
                WalletBalance,
                [WalletBalance.group_id == group_id, WalletBalance.member_id == member_id],
                {
                    "group_id": group_id,
                    "member_id": member_id,
                    "balance": balance + record,
                    "time": datetime.now()
                }
            )
            await orm.add(
                WalletDetail,
                {
                    "group_id": group_id,
                    "member_id": member_id,
                    "record": record,
                    "reason": reason,
                    "balance": balance + record,
                    "time": datetime.now()
                }
            )
            return True
        except:
            return False

    @staticmethod
    async def charge(group: Union[Group, int], member: Union[Member, int], record: int, reason: str = ""):
        return await Wallet.update(group, member, (record * -1), reason)

    @staticmethod
    async def get_detail(group: Union[Group, int], member: Union[Member, int]):
        group_id = group.id if type(group) != int else group
        member_id = member.id if type(member) != int else member
        if wallet := await orm.fetchall(
                select(
                    WalletDetail.record,
                    WalletDetail.reason,
                    WalletDetail.time
                ).where(WalletDetail.group_id == group_id, WalletDetail.member_id == member_id)
        ):
            return wallet.reverse()
        else:
            return None

    @staticmethod
    async def debug(group: Union[Group, None] = None, member: Union[Member, None] = None, add: bool = True):
        if add:
            if group:
                if group.id in Wallet.privilege['group']:
                    Wallet.privilege['group'].append(group.id)
                else:
                    return
            elif member:
                if member.id in Wallet.privilege['member']:
                    Wallet.privilege['member'].append(member.id)
                else:
                    return
        else:
            if group:
                if group.id in Wallet.privilege['group']:
                    Wallet.privilege['group'].remove(group.id)
                else:
                    return
            elif member:
                if member.id in Wallet.privilege['member']:
                    Wallet.privilege['member'].remove(member.id)
                else:
                    return
