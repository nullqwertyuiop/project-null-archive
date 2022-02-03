import traceback

from graia.broadcast.interrupt import InterruptControl, Waiter
from loguru import logger
from dateutil.relativedelta import relativedelta

from graia.ariadne.app import Ariadne
from graia.ariadne.event.mirai import *
from graia.ariadne.message.element import *
from graia.ariadne.event.message import Group, FriendMessage, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.exception import AccountMuted, UnknownTarget
from sqlalchemy import select

from sagiri_bot.utils import get_setting, user_permission_require
from sagiri_bot.core.app_core import AppCore
from sagiri_bot.orm.async_orm import orm, UserPermission, Setting, PermanentBlackList
from sagiri_bot.frequency_limit_module import GlobalFrequencyLimitDict

core: AppCore = AppCore.get_core_instance()
bcc = core.get_bcc()
config = core.get_config()
inc = InterruptControl(core.get_bcc())


@bcc.receiver("MemberJoinEvent")
async def member_join(app: Ariadne, event: MemberJoinEvent):
    if not await get_setting(event.member.group.id, Setting.event_listener):
        pass
    else:
        try:
            await app.sendMessage(
                event.member.group, MessageChain.create([
                    At(target=event.member.id),
                    Plain(text=f" {event.member.name} 已加入群聊。")
                ])
            )
        except AccountMuted:
            pass


@bcc.receiver("MemberLeaveEventQuit")
async def member_leave(app: Ariadne, event: MemberLeaveEventQuit):
    if not await get_setting(event.member.group.id, Setting.event_listener):
        pass
    else:
        try:
            await app.sendMessage(
                event.member.group, MessageChain.create([
                    Plain(text="%s 已退出群聊。" % event.member.name)
                ])
            )
        except AccountMuted:
            pass


@bcc.receiver("MemberMuteEvent")
async def member_muted(app: Ariadne, event: MemberMuteEvent):
    if event.operator is not None:
        if event.member.id == config.host_qq:
            try:
                await app.unmuteMember(event.member.group, event.member)
                if not await get_setting(event.member.group.id, Setting.event_listener):
                    pass
                else:
                    await app.sendMessage(
                        event.member.group, MessageChain.create([
                            Plain(text=f"主控 {event.member.id} 被禁言。")
                        ])
                    )
            except (PermissionError, AccountMuted):
                pass
        else:
            if not await get_setting(event.member.group.id, Setting.event_listener):
                pass
            else:
                try:
                    m, s = divmod(event.durationSeconds, 60)
                    h, m = divmod(m, 60)
                    d, h = divmod(h, 24)
                    await app.sendMessage(
                        event.member.group, MessageChain.create([
                            Plain(
                                text="%s 被禁言 %s" %
                                     (event.member.name, "%d 天 %02d 小时 %02d 分钟 %02d 秒" % (d, h, m, s)))
                        ])
                    )
                except AccountMuted:
                    pass


@bcc.receiver("MemberUnmuteEvent")
async def member_unmute(app: Ariadne, event: MemberUnmuteEvent):
    if not await get_setting(event.member.group.id, Setting.event_listener):
        pass
    else:
        try:
            await app.sendMessage(
                event.member.group, MessageChain.create([
                    Plain(text="%s 被解除禁言。" % event.member.name)
                ])
            )
        except AccountMuted:
            pass


@bcc.receiver("MemberLeaveEventKick")
async def member_kicked(app: Ariadne, event: MemberLeaveEventKick):
    if not await get_setting(event.member.group.id, Setting.event_listener):
        pass
    else:
        try:
            await app.sendMessage(
                event.member.group, MessageChain.create([
                    Plain(text="%s 被踢出群聊。" % event.member.name)
                ])
            )
        except AccountMuted:
            pass


@bcc.receiver("MemberSpecialTitleChangeEvent")
async def member_special_title_change(app: Ariadne, event: MemberSpecialTitleChangeEvent):
    if not await get_setting(event.member.group.id, Setting.event_listener):
        pass
    else:
        try:
            await app.sendMessage(
                event.member.group, MessageChain.create([
                    Plain(text="%s 的群头衔从 %s 改为 %s。" % (event.member.name, event.origin, event.current))
                ])
            )
        except AccountMuted:
            pass


@bcc.receiver("BotGroupPermissionChangeEvent")
async def bot_group_permission_change(app: Ariadne, event: BotGroupPermissionChangeEvent):
    try:
        if event.current == MemberPerm.Administrator and event.origin == MemberPerm.Member:
            await app.sendMessage(
                event.group, MessageChain.create([
                    Plain(text="机器人的权限变成 %s。\n已开启需求该权限的模块。" % event.current)
                ])
            )
        elif event.current == MemberPerm.Member and event.current == MemberPerm.Administrator:
            await app.sendMessage(
                event.group, MessageChain.create([
                    Plain(text="机器人的权限变成 %s。\n已关闭需求权限的模块。" % event.current)
                ])
            )
    except AccountMuted:
        pass


@bcc.receiver("MemberPermissionChangeEvent")
async def member_permission_change(app: Ariadne, event: MemberPermissionChangeEvent):
    if not await get_setting(event.member.group.id, Setting.event_listener):
        pass
    else:
        try:
            if event.member:
                await app.sendMessage(
                    event.member.group, MessageChain.create([
                        Plain(text="%s 的权限变成 %s。" % (event.member.name, event.current))
                    ])
                )
        except AccountMuted:
            pass


@bcc.receiver("BotLeaveEventKick")
async def bot_leave_group(app: Ariadne, event: BotLeaveEventKick):
    await app.sendFriendMessage(
        config.host_qq, MessageChain.create([
            Plain(text=f"机器人被踢出 {event.group.name} 群。")
        ])
    )
    await orm.insert_or_update(
        PermanentBlackList,
        [PermanentBlackList.id == event.group.id, PermanentBlackList.type == "group"],
        {"id": event.group.id,
         "type": "group",
         "date": datetime.now(),
         "reason": "机器人曾被踢出。"}
    )


@bcc.receiver("GroupNameChangeEvent")
async def group_name_changed(app: Ariadne, event: GroupNameChangeEvent):
    if not await get_setting(event.group.id, Setting.event_listener):
        pass
    else:
        try:
            await app.sendMessage(
                event.group, MessageChain.create([
                    Plain(text=f"本群名称由 {event.origin} 变为 {event.current}。")
                ])
            )
        except AccountMuted:
            pass


@bcc.receiver("GroupEntranceAnnouncementChangeEvent")
async def group_entrance_announcement_changed(app: Ariadne, event: GroupEntranceAnnouncementChangeEvent):
    if not await get_setting(event.group.id, Setting.event_listener):
        pass
    else:
        try:
            await app.sendMessage(
                event.group, MessageChain.create([
                    Plain(text=f"入群公告改变\n原公告：{event.origin}\n新公告：{event.current}")
                ])
            )
        except AccountMuted:
            pass


@bcc.receiver("GroupAllowAnonymousChatEvent")
async def group_allow_anonymous_chat_changed(app: Ariadne, event: GroupAllowAnonymousChatEvent):
    if not await get_setting(event.group.id, Setting.event_listener):
        pass
    else:
        try:
            await app.sendMessage(
                event.group, MessageChain.create([
                    Plain(text=f"匿名功能已{'开启。' if event.current else '关闭。'}")
                ])
            )
        except AccountMuted:
            pass


@bcc.receiver("GroupAllowConfessTalkEvent")
async def group_allow_confess_talk_changed(app: Ariadne, event: GroupAllowConfessTalkEvent):
    if not await get_setting(event.group.id, Setting.event_listener):
        pass
    else:
        try:
            await app.sendMessage(
                event.group, MessageChain.create([
                    Plain(text=f"坦白说功能已{'开启。' if not event.current else '关闭。'}")
                ])
            )
        except AccountMuted:
            pass


@bcc.receiver("GroupAllowMemberInviteEvent")
async def group_allow_member_invite_changed(app: Ariadne, event: GroupAllowMemberInviteEvent):
    if not await get_setting(event.group.id, Setting.event_listener):
        pass
    else:
        try:
            await app.sendMessage(
                event.group, MessageChain.create([
                    Plain(text=f"现在{'允许邀请成员加入。' if event.current else '不允许邀请成员加入。'}")
                ])
            )
        except AccountMuted:
            pass


@bcc.receiver("MemberCardChangeEvent")
async def member_card_changed(app: Ariadne, event: MemberCardChangeEvent):
    if not await get_setting(event.member.group.id, Setting.event_listener):
        pass
    else:
        try:
            if event.operator:
                if event.member.name == event.origin or event.origin == "" or event.current == "":
                    pass
                else:
                    await app.sendMessage(
                        event.member.group, MessageChain.create([
                            Plain(
                                text=f"{event.member.name} 的群名片被 {event.operator.name} 从 {event.origin} 改为 {event.current}。")
                        ])
                    )
            else:
                if event.member.name == event.origin or event.origin == "" or event.current == "":
                    pass
                else:
                    await app.sendMessage(
                        event.member.group, MessageChain.create([
                            Plain(text=f"{event.origin} 的群名片改为了 {event.current}。")
                        ])
                    )
        except AccountMuted:
            pass


@bcc.receiver("NewFriendRequestEvent")
async def new_friend_request(app: Ariadne, event: NewFriendRequestEvent):
    await event.reject()
    await app.sendFriendMessage(
        config.host_qq, MessageChain.create([
            Plain(text=f"已拒绝好友邀请。\n"),
            Plain(text=f"ID：{event.supplicant}\n"),
            Plain(text=f"来自：{event.nickname}\n"),
            Plain(text=f"描述：{event.message}\n"),
            Plain(text=f"source：{event.sourceGroup}")
        ])
    )
    # await app.sendFriendMessage(
    #     config.host_qq, MessageChain.create([
    #         Plain(text=f"机器人好友邀请。\n"),
    #         Plain(text=f"ID：{event.supplicant}\n"),
    #         Plain(text=f"来自：{event.nickname}\n"),
    #         Plain(text=f"描述：{event.message}\n"),
    #         Plain(text=f"source：{event.sourceGroup}")
    #     ])
    # )
    # if blacklist := await orm.fetchall(
    #         select(
    #             PermanentBlackList.id,
    #             PermanentBlackList.reason,
    #             PermanentBlackList.date
    #         ).where(PermanentBlackList.id == event.supplicant, PermanentBlackList.type == "user")
    # ):
    #     await event.reject(message=f"因 {blacklist[1]} 已于 {blacklist[2]} 拉黑。")
    # else:
    #     await event.accept()


@bcc.receiver("MemberJoinRequestEvent")
async def new_member_join_request(app: Ariadne, event: MemberJoinRequestEvent):
    try:
        msg = await app.sendGroupMessage(
            event.groupId, MessageChain.create([
                Plain(text=f"收到新的加群请求。\n"),
                Plain(text=f"ID：{event.supplicant}\n"),
                Plain(text=f"昵称：{event.nickname}\n"),
                Plain(text=f"描述：{event.message}\n"),
                Plain(text=f"回复本条消息 接受 / 拒绝 进行处理。")
            ])
        )

        @Waiter.create_using_function([GroupMessage])
        async def new_member_join_request_event_waiter(waiter_message: MessageChain, waiter_group: Group,
                                                 waiter_member: Member):
            if all([
                waiter_group.id == event.groupId,
                waiter_message.has(Quote)
            ]):
                if all([
                    waiter_message[Quote][0].id == msg.messageId,
                    "".join(i.text for i in waiter_message.get(Plain)).replace(" ", '') == "接受"
                ]):
                    if waiter_member.permission == MemberPerm.Member:
                        await app.sendGroupMessage(
                            event.groupId, MessageChain.create([
                                Plain(text="权限不足。")
                            ])
                        )
                    else:
                        return True
                elif all([
                    waiter_message[Quote][0].id == msg.messageId,
                    "".join(i.text for i in waiter_message.get(Plain)).replace(" ", '') == "拒绝"
                ]):
                    if waiter_member.permission == MemberPerm.Member:
                        await app.sendGroupMessage(
                            event.groupId, MessageChain.create([
                                Plain(text="权限不足。")
                            ])
                        )
                    else:
                        return False

        status = await inc.wait(new_member_join_request_event_waiter)
        try:
            await (event.accept() if status else event.reject())
        except:
            await app.sendGroupMessage(
                event.groupId, MessageChain.create([
                    Plain(text=f"无法处理该请求。")
                ])
            )
        await app.sendGroupMessage(
            event.groupId, MessageChain.create([
                Plain(text=f"已{'接受' if status else '拒绝'}该入群申请。")
            ])
        )
    except AccountMuted:
        pass


@bcc.receiver("BotInvitedJoinGroupRequestEvent")
async def bot_invited_join_group(app: Ariadne, event: BotInvitedJoinGroupRequestEvent):
    await event.reject()
    if event.supplicant != config.host_qq:
        await app.sendFriendMessage(
            config.host_qq, MessageChain.create([
                Plain(text=f"已拒绝群聊邀请\n"),
                Plain(text=f"邀请者ID：{event.supplicant}\n"),
                Plain(text=f"来自：{event.nickname}\n"),
                Plain(text=f"描述：{event.message}\n"),
                Plain(text=f"群聊ID：{event.groupId}\n"),
                Plain(text=f"群聊名称：{event.groupName}")
            ])
        )
    # if event.supplicant != config.host_qq:
    #     await app.sendFriendMessage(
    #         config.host_qq, MessageChain.create([
    #             Plain(text=f"机器人收到加入群聊邀请\n"),
    #             Plain(text=f"邀请者ID：{event.supplicant}\n"),
    #             Plain(text=f"来自：{event.nickname}\n"),
    #             Plain(text=f"描述：{event.message}\n"),
    #             Plain(text=f"群聊ID：{event.groupId}\n"),
    #             Plain(text=f"群聊名称：{event.groupName}")
    #         ])
    #     )
    #     if blacklist := await orm.fetchall(
    #             select(
    #                 PermanentBlackList.id,
    #                 PermanentBlackList.reason,
    #                 PermanentBlackList.date
    #             ).where(PermanentBlackList.id == event.groupId, PermanentBlackList.type == "group")
    #     ):
    #         await event.reject()
    #         try:
    #             await app.sendFriendMessage(
    #                 event.supplicant, MessageChain.create([
    #                     Plain(text=f"已收到加入群聊邀请。\n"),
    #                     Plain(text=f"来自：{event.nickname}\n"),
    #                     Plain(text=f"群聊ID：{event.groupId}\n"),
    #                     Plain(text=f"群聊名称：{event.groupName}\n"),
    #                     Plain(text=f"处理方式：拒绝\n"),
    #                     Plain(text=f"群组 ID 在黑名单中。\n"),
    #                     Plain(text=f"拉黑原因：{blacklist[0][1]}\n"),
    #                     Plain(text=f"拉黑时间：{blacklist[0][2]}\n")
    #                 ])
    #             )
    #         except UnknownTarget:
    #             pass
    #     else:
    #         try:
    #             await app.sendFriendMessage(
    #                 event.supplicant, MessageChain.create([
    #                     Plain(text=f"已收到加入群聊邀请。\n"),
    #                     Plain(text=f"来自：{event.nickname}\n"),
    #                     Plain(text=f"群聊ID：{event.groupId}\n"),
    #                     Plain(text=f"群聊名称：{event.groupName}\n"),
    #                     Plain(text=f"处理方式：自助处理，24 小时内仍未处理将转发至管理员\n"),
    #                     Plain(text=f"----------\n"),
    #                     Plain(text=f"使用时请注意：\n"),
    #                     Plain(text=f"1. 禁言机器人时机器人会主动退群并拉黑 24 小时\n"),
    #                     Plain(text=f'2. 将机器人踢出群聊时将"永久"拉黑该群与邀请者\n'),
    #                     Plain(text=f'3. 可发送 "/help" 查看帮助列表\n'),
    #                     Plain(text=f"4. 管理员不保证机器人全时可用（由于冻结或处理阻塞）\n"),
    #                     Plain(text=f'5. 如无需使用或机器人造成了问题请发送 "/quit" 令机器人退群\n'),
    #                     Plain(text=f"5. 机器人目前处于开发阶段，不保证稳定性\n")
    #                 ])
    #             )
    #             await app.sendFriendMessage(
    #                 event.supplicant, MessageChain.create([
    #                     Plain(text=f'发送 "撤回申请" 可自助取消本次申请。\n'),
    #                     Plain(text=f'发送 "我已阅读使用须知" 可自助完成本次申请。\n'),
    #                 ])
    #             )
    #         except UnknownTarget:
    #             pass
    #
    #         inc = InterruptControl(bcc)
    #
    #         @Waiter.create_using_function([FriendMessage])
    #         def waiter(
    #                 waiter_event: FriendMessage,
    #                 waiter_friend: Friend, waiter_message: MessageChain
    #         ):
    #             if all([
    #                 waiter_friend.id == event.supplicant,
    #                 waiter_message.asDisplay() == "撤回申请"
    #             ]):
    #                 return False
    #             if all([
    #                 waiter_friend.id == event.supplicant,
    #                 waiter_message.asDisplay() == "我已阅读使用须知"
    #             ]):
    #                 return True
    #
    #         if await inc.wait(waiter):
    #             try:
    #                 await event.accept()
    #                 try:
    #                     await app.sendFriendMessage(
    #                         event.supplicant, MessageChain.create([
    #                             Plain(text=f"已接受本次申请，祝您拥有良好的使用体验。")
    #                         ])
    #                     )
    #                 except UnknownTarget:
    #                     pass
    #             except Exception:
    #                 logger.error(traceback.format_exc())
    #         else:
    #             try:
    #                 await event.reject()
    #                 try:
    #                     await app.sendFriendMessage(
    #                         event.supplicant, MessageChain.create([
    #                             Plain(text=f"已撤回本次申请。")
    #                         ])
    #                     )
    #                 except UnknownTarget:
    #                     pass
    #             except Exception:
    #                 logger.error(traceback.format_exc())


@bcc.receiver("GroupRecallEvent")
async def anti_revoke(app: Ariadne, event: GroupRecallEvent):
    if await get_setting(event.group.id, Setting.anti_revoke) and event.authorId != config.bot_qq:
        try:
            msg = await app.getMessageFromId(event.messageId)
            revoked_msg = msg.messageChain
            author_member = await app.getMember(event.group.id, event.authorId)
            author_name = "自己" if event.operator.id == event.authorId else author_member.name
            resend_msg = MessageChain.create([Plain(text=f"{event.operator.name} 撤回了 {author_name} 的一条消息：\n\n")]) \
                .extend(revoked_msg)
            await app.sendMessage(
                event.group,
                resend_msg.asSendable()
            )
        except (AccountMuted, UnknownTarget):
            pass


join_info = {}


@bcc.receiver("BotJoinGroupEvent")
async def bot_join_group(app: Ariadne, group: Group):
    logger.info(f"机器人加入群组 <{group.name}>")
    try:
        await orm.insert_or_update(
            Setting,
            [Setting.group_id == group.id],
            {"group_id": group.id, "group_name": group.name, "active": True}
        )
        await orm.insert_or_update(
            UserPermission,
            [UserPermission.member_id == config.host_qq, UserPermission.group_id == group.id],
            {"member_id": config.host_qq, "group_id": group.id, "level": 4}
        )
        GlobalFrequencyLimitDict().add_group(group.id)
        if group.id in join_info.keys():
            limit_time = join_info[group.id] + relativedelta(seconds=10)
            if limit_time >= datetime.now():
                pass
        else:
            join_info[group.id] = datetime.now()
            await app.sendFriendMessage(
                config.host_qq, MessageChain.create([
                    Plain(text=f"机器人加入群聊 <{group.name}>")
                ])
            )
            await app.sendMessage(
                group, MessageChain.create([
                    Plain(text=f"机器人加入群组 <{group.name}>"),
                    Plain(text=f'\n可发送 "/help" 查看使用说明'),
                    Plain(text=f'\n可发送 "本群授权状态" 查看目前功能启用状态')
                ])
            )
    except AccountMuted:
        pass
    except:
        logger.error(traceback.format_exc())


@bcc.receiver(BotMuteEvent)
# async def bot_mute(app: Ariadne, group: Group, operator: Member):
async def bot_mute(app: Ariadne, event: BotMuteEvent):
    logger.info(f"机器人在群 <{event.group.name}> 中被 <{event.operator.name}> 禁言。")
    try:
        await app.quitGroup(event.group)
        await app.sendFriendMessage(
            config.host_qq, MessageChain.create([
                Plain(text=f"机器人在群 <{event.group.name}> 中被 <{event.operator.name}> 禁言。")
            ])
        )
    except:
        pass


# nudged_data = {}
#
#
# @bcc.receiver("NudgeEvent")
# async def nudge(app: Ariadne, event: NudgeEvent):
#     if event.target == config.bot_qq:
#         if event.context_type == "group":
#             if not await get_setting(event.group_id, Setting.event_listener):
#                 pass
#             else:
#                 if member := await app.getMember(event.group_id, event.supplicant):
#                     logger.info(f"机器人被群 <{member.group.name}> 中用户 <{member.name}> 戳了戳。")
#                     if member.group.id in nudged_data.keys():
#                         if member.id in nudged_data[member.group.id].keys():
#                             period = nudged_data[member.group.id][member.id]["time"] + relativedelta(minutes=1)
#                             if datetime.now() >= period:
#                                 nudged_data[member.group.id][member.id] = {"count": 0, "time": datetime.now()}
#                             count = nudged_data[member.group.id][member.id]["count"] + 1
#                             if count == 1:
#                                 try:
#                                     await app.sendNudge(member)
#                                 except:
#                                     pass
#                                 nudged_data[member.group.id][member.id] = {"count": count, "time": datetime.now()}
#                             elif count == 2:
#                                 try:
#                                     await app.sendNudge(member)
#                                     await app.sendMessage(
#                                         member.group, MessageChain.create([
#                                             Plain(text=f"不许戳了！")
#                                         ])
#                                     )
#                                 except:
#                                     pass
#                                 nudged_data[member.group.id][member.id] = {"count": count, "time": datetime.now()}
#                             elif count == 3:
#                                 try:
#                                     await app.sendNudge(member)
#                                     await app.sendMessage(
#                                         member.group, MessageChain.create([
#                                             Plain(text=f"说了不许再戳了！")
#                                         ])
#                                     )
#                                 except:
#                                     pass
#                                 nudged_data[member.group.id][member.id] = {"count": count, "time": datetime.now()}
#                             elif count == 4:
#                                 try:
#                                     await app.sendNudge(member)
#                                 except:
#                                     pass
#                                 nudged_data[member.group.id][member.id] = {"count": count, "time": datetime.now()}
#                             elif count == 5:
#                                 try:
#                                     await app.sendNudge(member)
#                                     await app.sendMessage(
#                                         member.group, MessageChain.create([
#                                             Plain(text=f"呜呜呜你欺负我，不理你了！")
#                                         ])
#                                     )
#                                 except:
#                                     pass
#                                 nudged_data[member.group.id][member.id] = {"count": count, "time": datetime.now()}
#                             elif 6 <= count <= 9:
#                                 nudged_data[member.group.id][member.id] = {"count": count, "time": datetime.now()}
#                             elif count == 10:
#                                 try:
#                                     await app.sendNudge(member)
#                                     await app.sendMessage(
#                                         member.group, MessageChain.create([
#                                             Plain(text="你真的很有耐心欸。")
#                                         ])
#                                     )
#                                 except:
#                                     pass
#                         else:
#                             nudged_data[member.group.id][member.id] = {"count": 1, "time": datetime.now()}
#                             await app.sendNudge(member)
#                     else:
#                         nudged_data[member.group.id] = {member.id: {"count": 1, "time": datetime.now()}}
#                         await app.sendNudge(member)
#         else:
#             if friend := await app.getFriend(event.supplicant):
#                 logger.info(f"机器人被好友 <{friend.nickname}> 戳了戳。")
