import re
from datetime import datetime

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, Member, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain, ForwardNode, Forward
from graia.ariadne.model import Friend
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema

from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import Normal
from sagiri_bot.decorators import switch, blacklist

saya = Saya.current()
channel = Channel.current()

channel.name("FakeForward")
channel.author("nullqwertyuiop")
channel.description("更加高级的伪造功能，不要让我踢你的屁股")


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def fake_forward_handler(app: Ariadne, message: MessageChain, friend: Friend):
    if result := await FakeForward.handle(app, message, friend=friend):
        await MessageSender(result.strategy).send(app, result.message, message, friend, friend)


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def fake_forward_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await FakeForward.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


class FakeForward(AbstractHandler):
    __name__ = "FakeForward"
    __description__ = "伪造转发 Handler"
    __usage__ = "None"
    func_switch = {}

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if re.match("构造转发(:|：).*", message.asDisplay()):
            raw_data = re.sub("构造转发(:|：)\n*", "", message.asDisplay(), count=1)
            fwd_nodelist = []
            while True:
                if fwd_node := re.compile("节点\{(\d+)#(\d{4}\/\d{1,2}\/\d{1,2} \d{1,2}:\d{2})#(.+)#:#(.+)\}\n*")\
                        .search(raw_data):
                    raw_data = re.sub('节点\{(\d+)#(\d{4}\/\d{1,2}\/\d{1,2} \d{1,2}:\d{2})#(.+)#:#(.+)\}\n*', "",
                                      raw_data, count=1)
                    target = int(fwd_node.group(1))
                    time = fwd_node.group(2)
                    target_name = fwd_node.group(3)
                    message = fwd_node.group(4)
                    fwd_nodelist.append(
                        ForwardNode(
                            target=target,
                            time=datetime.strptime(time, "%Y/%m/%d %H:%M"),
                            name=target_name,
                            message=MessageChain.create(Plain(text=message)),
                        )
                    )
                else:
                    break
            if not fwd_nodelist:
                return None
            else:
                fwd_nodelist.append(
                    ForwardNode(
                        target=member.id,
                        time=datetime.now(),
                        name="已构造的消息",
                        message=MessageChain.create(Plain(text=f"本条转发消息为已构造的消息。\n"
                                                               f"请不要通过该方法传播谣言，"
                                                               f"要不然我就要用我的靴子狠狠地踢你的屁股。"))
                    )
                )
                return MessageItem(MessageChain.create(Forward(nodeList=fwd_nodelist)), Normal())
        else:
            return None
