from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Plain
from graia.ariadne.model import Friend, Member, Group
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast import ListenerSchema

from sagiri_bot.decorators import blacklist, switch
from sagiri_bot.handler.handler import AbstractHandler
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.message_sender import MessageSender
from sagiri_bot.message_sender.strategy import Normal
from sagiri_bot.utils import HelpPage, HelpPageElement

saya = Saya.current()
channel = Channel.current()

channel.name("SignInReward")
channel.author("nullqwertyuiop")
channel.description("签到")


@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def help_generator_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
    if result := await HelpGenerator.handle(app, message, group=group, member=member):
        await MessageSender(result.strategy).send(app, result.message, message, group, member)


@channel.use(ListenerSchema(listening_events=[FriendMessage]))
async def help_generator_handler(app: Ariadne, message: MessageChain, friend: Friend):
    if result := await HelpGenerator.handle(app, message, friend=friend):
        await MessageSender(result.strategy).send(app, result.message, message, friend, friend)


class HelpGenerator(AbstractHandler):
    __name__ = "SignInRewardHandler"
    __description__ = "签到获取奖励"
    __usage__ = "None"
    __cached_help_menu = None
    sub_classes = HelpPage.__subclasses__()
    utility = [x for x in sub_classes if x.__category__ == "utility"]
    entertainment = [x for x in sub_classes if x.__category__ == "entertainment"]
    hidden = [x for x in sub_classes if x.__category__ == "hidden"]
    experimental = [x for x in sub_classes if x.__category__ == "experimental"]
    _ = [utility, entertainment, hidden, experimental]
    __available = [[], [], [], []]
    counter = 1
    for _index, _category in enumerate(_):
        _category.sort(key=lambda x: x.__name__.lower())
        for _class in _category:
            __available[_index].append(
                (counter, _class, _class.__description__, _class.__trigger__, _class.__icon__))
            counter += 1
    sub_classes = []
    for _category in __available:
        sub_classes.extend(_category)
    __sub_classes = sub_classes
    del sub_classes, counter, utility, entertainment, hidden, experimental, _

    @staticmethod
    @switch()
    @blacklist()
    async def handle(app: Ariadne, message: MessageChain, group: Group = None,
                     member: Member = None, friend: Friend = None):
        if message.asDisplay().startswith(".help"):
            available = HelpGenerator.__available
            if message.asDisplay().startswith(".help "):
                arg = message.asDisplay()[6:]
                if arg.isdigit():
                    arg = int(arg)
                elif arg == "render":
                    canvas_data = await HelpGenerator.render_help_page()
                    return MessageItem(MessageChain.create([
                        Image(data_bytes=canvas_data),
                        Plain(text="已完成渲染")
                    ]), Normal())
                canvas_data = None
                for index, sub_classes in enumerate(available):
                    if index == 2:
                        for sub_class in sub_classes:
                            if arg == sub_class[0]:
                                hp = HelpPage([
                                    HelpPageElement(
                                        icon=sub_class[4],
                                        text="已隐藏",
                                        is_title=True
                                    ),
                                    HelpPageElement(
                                        icon="lightbulb-on",
                                        text="已隐藏的内容",
                                        description="可发送 \".help [触发词]\" 查看未隐藏的帮助页面"
                                    ),
                                ])
                                canvas = await hp.compose()
                                canvas_data = canvas.pic2bytes()
                            elif arg == sub_class[2] or arg == sub_class[3]:
                                hp = sub_class[1](group=group, member=member, friend=friend)
                                canvas = await hp.compose()
                                canvas_data = canvas.pic2bytes()
                    else:
                        for sub_class in sub_classes:
                            if arg == sub_class[0] or arg == sub_class[2] or arg == sub_class[3]:
                                hp = sub_class[1](group=group, member=member, friend=friend)
                                canvas = await hp.compose()
                                canvas_data = canvas.pic2bytes()
                if canvas_data:
                    return MessageItem(MessageChain.create([
                        Image(data_bytes=canvas_data)
                    ]), Normal())
                else:
                    return MessageItem(MessageChain.create([
                        Plain(text=f"无法找到页面或条目 {arg}")
                    ]), Normal())
            else:
                if not HelpGenerator.__cached_help_menu:
                    canvas_data = await HelpGenerator.render_help_page()
                else:
                    canvas_data = HelpGenerator.__cached_help_menu
                return MessageItem(MessageChain.create([
                    Image(data_bytes=canvas_data)
                ]), Normal())

    @staticmethod
    async def render_help_page():
        available = HelpGenerator.__available
        icons = ["hammer-wrench", "gamepad-square", "eye-off", "flask-outline"]
        category_text = ["实用工具", "娱乐", "隐藏功能", "实验性"]
        hide_content = [False, False, True, False]
        elements = [
            HelpPageElement(
                icon="help-circle",
                text="帮助菜单",
                is_title=True,
                description="发送 \".help 序号\" 查看详细帮助页面"
            ),
            HelpPageElement(
                text=" "
            )
        ]
        for category, icon, text, hide_content in zip(available, icons, category_text, hide_content):
            elements.append(
                HelpPageElement(
                    icon=icon,
                    text=text,
                    is_title=True)
            )
            for help_page in category:
                if not hide_content:
                    elements.append(
                        HelpPageElement(
                            icon=help_page[4],
                            text=f"{help_page[0]}. {help_page[2]}",
                            description=help_page[3])
                    )
                else:
                    elements.append(
                        HelpPageElement(
                            icon=help_page[4],
                            text=f"{help_page[0]}. 已隐藏",
                            description="已隐藏")
                    )
            elements.append(
                HelpPageElement(
                    text=" "
                )
            )
        elements.append(
            HelpPageElement(
                icon="hexagon-multiple",
                text="Null",
                description="本项目为 Project. Null 组成部分"
            )
        )
        hp = HelpPage(elements)
        canvas = await hp.compose()
        canvas_data = canvas.pic2bytes()
        HelpGenerator.__cached_help_menu = canvas_data
        return canvas_data
