# import asyncio
# import re
# from datetime import datetime
#
# from graia.ariadne.app import Ariadne, ApplicationLaunched
# from graia.ariadne.event.message import Group, Member, GroupMessage
# from graia.ariadne.exception import AccountMuted
# from graia.ariadne.model import MemberPerm
# from graia.ariadne.message.chain import MessageChain
# from graia.ariadne.message.element import Plain
# from graia.saya import Saya, Channel
# from graia.saya.builtins.broadcast.schema import ListenerSchema
# from sqlalchemy import select
#
# from sagiri_bot.handler.handler import AbstractHandler
# from sagiri_bot.message_sender.message_item import MessageItem
# from sagiri_bot.message_sender.message_sender import MessageSender
# from sagiri_bot.message_sender.strategy import QuoteSource
# from sagiri_bot.orm.async_orm import orm, ScheduledMessage
# from sagiri_bot.decorators import switch, blacklist
# from sagiri_bot.utils import user_permission_require
#
# saya = Saya.current()
# channel = Channel.current()
#
#
# @channel.use(ListenerSchema(listening_events=[GroupMessage]))
# async def scheduled_message_handler(app: Ariadne, message: MessageChain, group: Group, member: Member):
#     if result := await ScheduledMessageHandler.handle(app, message, group, member):
#         await MessageSender(result.strategy).send(app, result.message, message, group, member)
#
#
# class ScheduledMessageHandler(AbstractHandler):
#     __name__ = "ScheduledMessage"
#     __description__ = "帮你查查 Handler"
#     __usage__ = "None"
#     cache = {}
#     s_switch = True
#
#     @staticmethod
#     @switch()
#     @blacklist()
#     async def handle(app: Ariadne, message: MessageChain, group: Group, member: Member):
#         if re.match(r"添加定时消息#(.*)#(.*)", message.asDisplay()):
#             if (await user_permission_require(group, member, 2)) or (member.permission != MemberPerm.Member):
#                 return MessageItem(
#                     await ScheduledMessageHandler.update_scheduled_message(group, message),
#                     QuoteSource()
#                 )
#             else:
#                 return MessageItem(MessageChain.create([Plain(text="权限不足。")]), QuoteSource())
#         elif re.match(r"删除定时消息#(.*)", message.asDisplay()):
#             if (await user_permission_require(group, member, 2)) or (member.permission != MemberPerm.Member):
#                 return MessageItem(
#                     await ScheduledMessageHandler.delete_scheduled_message(group, message),
#                     QuoteSource()
#                 )
#             else:
#                 return MessageItem(MessageChain.create([Plain(text="权限不足。")]), QuoteSource())
#         elif message.asDisplay() == "刷新定时消息缓存":
#             return MessageItem(await ScheduledMessageHandler.update_cache(), QuoteSource())
#         elif message.asDisplay() == "开启定时消息":
#             if await user_permission_require(group, member, 4):
#                 ScheduledMessageHandler.s_switch = True
#                 return MessageItem(MessageChain.create([Plain(text=f"开启定时消息成功。")]), QuoteSource())
#             else:
#                 return MessageItem(MessageChain.create([Plain(text="权限不足。")]), QuoteSource())
#         elif message.asDisplay() == "停止定时消息":
#             if await user_permission_require(group, member, 4):
#                 ScheduledMessageHandler.s_switch = False
#                 return MessageItem(MessageChain.create([Plain(text=f"关闭定时消息成功。")]), QuoteSource())
#             else:
#                 return MessageItem(MessageChain.create([Plain(text="权限不足。")]), QuoteSource())
#         elif message.asDisplay() == "查看所有定时消息":
#             if await user_permission_require(group, member, 4):
#                 return MessageItem(MessageChain.fromPersistentString(str(ScheduledMessageHandler.cache)),
#                                    QuoteSource())
#             else:
#                 return MessageItem(MessageChain.create([Plain(text="权限不足。")]), QuoteSource())
#         elif message.asDisplay() == "本群定时消息":
#             return MessageItem(await ScheduledMessageHandler.fetch_scheduled_msg(group), QuoteSource())
#         else:
#             return None
#
#     @staticmethod
#     async def update_scheduled_message(group: Group, message: MessageChain):
#         message_serialization = message.asPersistentString()
#         reg = re.compile("添加定时消息#(.*)#(.*)")
#         s_time = reg.search(message.asDisplay()).group(1).replace("：", ":")
#         if not s_time:
#             return MessageChain.create([Plain(text=f"检测到空数据。")])
#         reg_t = re.compile("(([0-1][0-9])|(2[0-3])):[0-5][0-9]")
#         if not reg_t.search(s_time):
#             return MessageChain.create([Plain(text=f"时间格式错误。")])
#         _, __, m_serialization = message_serialization.split("#", maxsplit=2)
#         if not m_serialization:
#             return MessageChain.create([Plain(text=f"检测到空数据。")])
#         update = False
#         original_msg = None
#         if original := await orm.fetchall(
#                 select(
#                     ScheduledMessage.message
#                 ).where(ScheduledMessage.group_id == group.id,
#                         ScheduledMessage.time == s_time)
#         ):
#             update = True
#             try:
#                 original_msg = original[0][0]
#             except IndexError:
#                 pass
#         await orm.insert_or_update(
#             ScheduledMessage,
#             [ScheduledMessage.group_id == group.id, ScheduledMessage.time == s_time],
#             {"group_id": group.id,
#              "time": s_time,
#              "message": m_serialization,
#              }
#         )
#         await ScheduledMessageHandler.update_cache()
#         if not (update and original_msg):
#             return MessageChain.extend(MessageChain.create([Plain(text=f"添加定时消息成功。\n定时于 {s_time} 的消息为：\n")]),
#                                        MessageChain.fromPersistentString(m_serialization))
#         else:
#             return MessageChain.extend(MessageChain.create([Plain(text=f"覆写定时消息成功。\n定时于 {s_time} 的消息为：\n")]),
#                                        MessageChain.fromPersistentString(m_serialization),
#                                        MessageChain.create([Plain(text=f"\n----------\n覆写前定时消息为：\n")]),
#                                        MessageChain.fromPersistentString(original_msg))
#
#     @staticmethod
#     async def delete_scheduled_message(group: Group, message: MessageChain):
#         reg = re.compile("删除定时消息#(.*)")
#         s_time = reg.search(message.asDisplay()).group(1).replace("：", ":")
#         if not s_time:
#             return MessageChain.create([Plain(text=f"检测到空数据。")])
#         reg_t = re.compile("(([0-1][0-9])|(2[0-3])):[0-5][0-9]")
#         if not reg_t.search(s_time):
#             return MessageChain.create([Plain(text=f"时间格式错误。")])
#         try:
#             await orm.delete(ScheduledMessage,
#                              [ScheduledMessage.time == s_time, ScheduledMessage.group_id == group.id]
#                              )
#         except:
#             return MessageChain.create([Plain(text=f"删除定时消息失败，请联系机器人管理员。")])
#         await ScheduledMessageHandler.update_cache()
#         return MessageChain.create([Plain(text=f"成功删除定时于 {s_time} 的消息。")])
#
#     @staticmethod
#     async def fetch_scheduled_msg(group: Group):
#         schedules = await orm.fetchall(
#             select(
#                 ScheduledMessage.time,
#                 ScheduledMessage.message
#             ).where(ScheduledMessage.group_id == group.id)
#         )
#         if not schedules:
#             return MessageChain.create([Plain(text=f"本群未设定任何定时消息。")])
#         fetched = MessageChain.create([Plain(text=f"本群设定的定时消息为：")])
#         for schedule in schedules:
#             time = schedule[0]
#             msg = schedule[1]
#             fetched = MessageChain.extend(fetched,
#                                           MessageChain.create([Plain(text=f"\n{time}：\n")]),
#                                           MessageChain.fromPersistentString(msg))
#         return fetched
#
#     @staticmethod
#     async def update_cache():
#         schedules = await orm.fetchall(
#             select(
#                 ScheduledMessage.group_id,
#                 ScheduledMessage.time,
#                 ScheduledMessage.message
#             )
#         )
#         if not schedules:
#             schedules = []
#         else:
#             ScheduledMessageHandler.cache = {}
#             for schedule in schedules:
#                 group_id = schedule[0]
#                 time = schedule[1]
#                 msg = schedule[2]
#                 if ScheduledMessageHandler.cache.get(time):
#                     ScheduledMessageHandler.cache[time][group_id] = msg
#                 else:
#                     ScheduledMessageHandler.cache.update({
#                         time: {
#                             group_id: msg
#                         }
#                     })
#         return MessageChain.create([Plain(text=f"已刷新定时消息缓存。\n现已缓存 {len(schedules)} 条。")])
#
#
# @channel.use(ListenerSchema(listening_events=[ApplicationLaunched]))
# async def scheduled_message_caching():
#     await ScheduledMessageHandler.update_cache()
#
#
# @channel.use(ListenerSchema(listening_events=[ApplicationLaunched]))
# async def scheduled_message_sender(app: Ariadne):
#     now = datetime.now()
#     wait_for_next_minute = False
#     while True:
#         if ScheduledMessageHandler.s_switch:
#             times = ScheduledMessageHandler.cache.keys()
#             now_time = now.strftime("%H:%M")
#             if now_time in times:
#                 groups = ScheduledMessageHandler.cache[now_time].keys()
#                 for group in groups:
#                     try:
#                         msg = ScheduledMessageHandler.cache[now_time][group]
#                         await app.sendGroupMessage(
#                             app,
#                             group,
#                             MessageChain.fromPersistentString(msg)
#                         )
#                     except AccountMuted:
#                         pass
#                     except:
#                         pass
#         after_minute = now.second + now.microsecond / 1_000_000
#         if after_minute != 0:
#             to_next_minute = 60 - after_minute
#         else:
#             to_next_minute = 0
#         if wait_for_next_minute:
#             to_next_minute += 60
#         await asyncio.sleep(to_next_minute)
#         prev = now
#         now = datetime.now()
#         wait_for_next_minute = now.minute == prev.minute
