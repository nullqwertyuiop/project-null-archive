# import json
#
# import requests
# from graia.ariadne.app import Ariadne
# from graia.ariadne.event.message import Group, Member, GroupMessage
# from graia.ariadne.message.chain import MessageChain
# from graia.ariadne.message.element import Plain
# from graia.saya import Saya, Channel
# from graia.saya.builtins.broadcast.schema import ListenerSchema
# from graia.scheduler import GraiaScheduler
# from requests import utils
#
# from sagiri_bot.core.app_core import AppCore
# from sagiri_bot.handler.handler import AbstractHandler
# from sagiri_bot.message_sender.message_item import MessageItem
# from sagiri_bot.message_sender.message_sender import MessageSender
# from sagiri_bot.message_sender.strategy import QuoteSource
# from sagiri_bot.decorators import switch, blacklist
#
# saya = Saya.current()
# channel = Channel.current()
# bcc = saya.broadcast
# core: AppCore = AppCore.get_core_instance()
# app = core.get_app()
# loop = core.get_loop()
# scheduler = GraiaScheduler(loop, bcc)
#
#
# @channel.use(ListenerSchema(listening_events=[GroupMessage]))
# async def snowball_realtime_news_handler(app: Ariadne, message: MessageChain, group: Group,
#                                          member: Member):
#     if result := await SnowBallRealtimeHandler.handle(app, message, group, member):
#         await MessageSender(result.strategy).send(app, result.message, message, group, member)
#
#
# class SnowBallRealtimeHandler(AbstractHandler):
#     __name__ = "SnowBallRealtimeHandler"
#     __description__ = "实时获取雪球新闻"
#     __usage__ = "None"
#     cookie_dict = {}
#
#     @staticmethod
#     @switch()
#     @blacklist()
#     async def handle(app: Ariadne, message: MessageChain, group: Group, member: Member):
#         if message.asDisplay() == "##签到":
#             member_id = member.id
#             result = await SignInRewardHandler.sign_in(member_id)
#             return MessageItem(MessageChain.create([Plain(text=result)]), QuoteSource())
#         elif message.asDisplay() == "##钱包":
#             member_id = member.id
#             result = await SignInRewardHandler.get_wallet(member_id)
#             return MessageItem(MessageChain.create([Plain(text=result)]), QuoteSource())
#
#     @staticmethod
#     async def get_cookie():
#         s = requests.Session()
#         link1 = "http://xueqiu.com"
#         header1 = {
#             'Accept': '*/*',
#             'Accept-Encoding': 'gzip, deflate, br',
#             'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
#             'Connection': 'keep-alive',
#             'Host': 'xueqiu.com',
#             'Referer': 'http://xueqiu.com/',
#             'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
#                           'Chrome/67.0.3396.99 Safari/537.36',
#             'X-Requested-With': 'XMLHttpRequest',
#         }
#         cookies = s.get(link1, headers=header1).cookies
#         SnowBallRealtimeHandler.cookie_dict = cookies
#         cookies_str = json.dumps(requests.utils.dict_from_cookiejar(cookies))
#
#     @staticmethod
#     async def snowball_realtime():
#         # with open('cookie', 'rb') as f:
#         #     s.cookies.update(pickle.load(f))
#         headers = {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) ' 'Chrome/51.0'
#                           '.2704.63 Safari/537.36'}
#         response = requests.get('http://xueqiu.com/statuses/livenews/list.json?since_id=-1',
#                                 headers=headers, verify=True, timeout=30,
#                                 cookies=requests.utils.cookiejar_from_dict(SnowBallRealtimeHandler.cookie_dict))
#         content = response.content
#         result = json.loads(content)
#         list = []
#         news = result['items']
#         piece = {}
#         for i in range(0, len(news)):
#             piece['id'] = news[i]['id']
#             piece['text'] = news[i]['text']
#             piece['target'] = news[i]['target']
#             piece['created_at'] = news[i]['created_at']
#             list.append(piece)
#         return list
#
#     def compareID():
#         with open('id', 'r') as f:
#             last = f.read()
#         if int(snowball_realtime()[0]['id']) == int(last):
#             return True
#         else:
#             return False
#
#     def updateID():
#         try:
#             with open('id', 'w') as f:
#                 f.write(str(snowball_realtime()[0]['id']))
#             return True
#         except:
#             return False
#
#     def readSettings():
#         try:
#             with open('stock_settings', 'r') as f:
#                 return f.read()
#         except:
#             with open('stock_settings', 'w') as f:
#                 f.write('0')
