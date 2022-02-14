import asyncio
import json
from datetime import datetime
from json import JSONDecodeError
from pathlib import Path

import aiohttp
from aiohttp import BasicAuth
from graia.ariadne.app import Ariadne
from graia.ariadne.exception import UnknownTarget, AccountMuted
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.ariadne.model import Group, Friend
from graia.saya import Saya
from graia.scheduler import GraiaScheduler
from graia.scheduler.timers import crontabify
from loguru import logger

from sagiri_bot.core.app_core import AppCore
from sagiri_bot.message_sender.message_item import MessageItem
from sagiri_bot.message_sender.strategy import Normal, QuoteSource

saya = Saya.current()
bcc = saya.broadcast
core: AppCore = AppCore.get_core_instance()
app = core.get_app()
loop = core.get_loop()
scheduler = GraiaScheduler(loop, bcc)
config = core.get_config()
proxy = config.proxy if config.proxy != "proxy" else ''


class GithubWatcher:
    __name__ = "GithubWatcher"
    __description__ = "Github 订阅 Handler"
    __usage__ = "None"
    __cached = {}
    if config.functions['github']['username'] != "username" and config.functions['github']['token'] != 'token':
        __auth = True
        __session = aiohttp.ClientSession(auth=BasicAuth(
            login=config.functions['github']['username'],
            password=config.functions['github']['token']
        ))
    else:
        __auth = False
        __first_warned = False
        __session = aiohttp.ClientSession()
    __status = True
    __base_url = "https://api.github.com"
    __events_url = "/repos/{owner}/{repo}/events"
    __is_running = False
    initialize = False

    @staticmethod
    async def enable(**kwargs):
        GithubWatcher.__status = True
        return MessageChain.create([Plain(text="已开启 Github 仓库订阅")])

    @staticmethod
    async def disable(**kwargs):
        GithubWatcher.__status = False
        return MessageChain.create([Plain(text="已关闭 Github 仓库订阅")])

    @staticmethod
    async def add(**kwargs):
        if not GithubWatcher.__status:
            return MessageChain.create([Plain(text="Github 仓库订阅功能已关闭")])
        repos = None
        group = None
        friend = None
        app = None
        for name, arg in kwargs.items():
            if name == "arg" and isinstance(arg, str):
                repos = arg
            if isinstance(arg, Group):
                group = arg
            if isinstance(arg, Friend):
                friend = arg
            if isinstance(arg, Ariadne):
                app = arg
        err = []
        if not group and not friend:
            err = err.extend([
                Plain(text="无法获取 Group 或 Friend 实例")
            ])
        if not app:
            err = err.extend([
                Plain(text="无法获取 Ariadne 实例")
            ])
        if not repos:
            err = err.extend([
                Plain(text="未填写需要订阅的仓库")
            ])
        if err:
            return MessageChain.create(err)
        repos = repos.split(" ")
        failed = []
        duplicated = []
        success_count = 0
        for repo in repos:
            url = f"https://api.github.com/search/repositories?q={repo}"
            async with GithubWatcher.__session.get(url=url, proxy=proxy) as resp:
                result = (await resp.json())["items"]
                if not result:
                    failed.append(repo)
                    continue
                repo = result[0]['full_name']
            repo = repo.split("/")
            repo = (repo[0], repo[1])
            if repo not in GithubWatcher.__cached.keys():
                GithubWatcher.__cached[repo] = {
                    "group": [],
                    "friend": [],
                    "last_id": -1,
                    "enabled": True
                }
            if group:
                if group.id in GithubWatcher.__cached[repo]['group']:
                    duplicated.append(f"{repo[0]}/{repo[1]}")
                else:
                    GithubWatcher.__cached[repo]['group'] = GithubWatcher.__cached[repo]['group'] + [group.id]
            if friend:
                if friend.id in GithubWatcher.__cached[repo]['friend']:
                    duplicated.append(f"{repo[0]}/{repo[1]}")
                else:
                    GithubWatcher.__cached[repo]['friend'] = GithubWatcher.__cached[repo]['friend'] + [friend.id]
            if GithubWatcher.__cached[repo]['last_id'] == -1:
                await GithubWatcher.github_schedule(app=app, manuel=True, per_page=1, page=1, repo=repo)
            success_count += 1
        res = [Plain(text=f"{success_count} 个仓库订阅成功")]
        if failed:
            res.append(Plain(text=f"\n{len(failed)} 个仓库订阅失败"
                                  f"\n失败的仓库有：{' '.join(failed)}"))
        if duplicated:
            res.append(Plain(text=f"\n{len(duplicated)} 个仓库已在订阅列表中"
                                  f"\n重复的仓库有：{' '.join(duplicated)}"))
        try:
            GithubWatcher.store_cache(manual=False)
            GithubWatcher.update_cache(manual=False)
            return MessageChain.create(res)
        except Exception as e:
            logger.error(e)
            res.append(Plain(text="\n\n刷新缓存失败"))
            return MessageChain.create(res)

    @staticmethod
    async def remove(**kwargs):
        if not GithubWatcher.__status:
            return MessageChain.create([Plain(text=f"Github 仓库订阅功能已关闭")])
        repos = None
        group = None
        friend = None
        err = []
        for name, arg in kwargs.items():
            if name == "arg" and isinstance(arg, str):
                repos = arg
            if isinstance(arg, Group):
                group = arg
            if isinstance(arg, Friend):
                friend = arg
        if not group and not friend:
            err = err.extend([
                Plain(text=f"无法获取 Group 或 Friend 实例")
            ])
        if not repos:
            err = err.extend([
                Plain(text="未填写需要取消订阅的仓库")
            ])
        if err:
            return MessageChain.create(err)
        repos = repos.split(" ")
        failed = []
        success_count = 0
        for repo in repos:
            repo = repo.split("/")
            if len(repo) != 2:
                failed.append("/".join(repo))
                continue
            repo = (repo[0], repo[1])
            if repo not in GithubWatcher.__cached.keys():
                failed.append("/".join(repo))
                continue
            if group:
                GithubWatcher.__cached[repo]['group'] = [
                    group_id for group_id in GithubWatcher.__cached[repo]['group'] if group_id != group.id
                ]
            if friend:
                GithubWatcher.__cached[repo]['friend'] = [
                    friend_id for friend_id in GithubWatcher.__cached[repo]['group'] if friend_id != friend.id
                ]
            if not (GithubWatcher.__cached[repo]['group'] and GithubWatcher.__cached[repo]['friend']):
                GithubWatcher.__cached.pop(repo)
            success_count += 1
        res = [Plain(text=f"{success_count} 个仓库取消订阅成功")]
        if failed:
            res.append(Plain(text=f"\n{len(failed)} 个仓库取消订阅失败"
                                  f"\n失败的仓库有：{' '.join(failed)}"))
        try:
            GithubWatcher.store_cache(manual=False)
            GithubWatcher.update_cache(manual=False)
            return MessageChain.create(res)
        except Exception as e:
            logger.error(e)
            res.append(Plain(text="\n\n刷新缓存失败"))
            return MessageChain.create(res)

    @staticmethod
    async def cache(**kwargs):
        accepted = ['update', 'store']
        command = None
        for name, arg in kwargs.items():
            if name == "arg" and isinstance(arg, str):
                command = arg
        if not command:
            return MessageChain.create([Plain(text=f"未填写参数")])
        if command not in accepted:
            return MessageChain.create([Plain(text=f"未知参数：{command}")])
        if command == 'update':
            return GithubWatcher.update_cache(manual=True)
        if command == 'store':
            return GithubWatcher.store_cache(manual=True)

    @staticmethod
    def update_cache(manual: bool = False):
        try:
            with open(str(Path(__file__).parent.joinpath("watcher_data.json")), "r") as r:
                data = json.loads(r.read())
                cache = {}
                for key in data.keys():
                    owner, repo = key.split("/")
                    cache[(owner, repo)] = data[key]
                GithubWatcher.__cached = cache
            return MessageChain.create([Plain(text="更新缓存成功")]) if manual else None
        except (FileNotFoundError, JSONDecodeError):
            return MessageChain.create([Plain(text="无法更新缓存，请检查是否删除了缓存文件并重新储存缓存")])

    @staticmethod
    def store_cache(manual: bool = False):
        with open(str(Path(__file__).parent.joinpath("watcher_data.json")), "w") as w:
            cache = {}
            for key in GithubWatcher.__cached.keys():
                new_key = f"{key[0]}/{key[1]}"
                cache[new_key] = GithubWatcher.__cached[key]
            w.write(json.dumps(cache, indent=4))
        return MessageChain.create([Plain(text="写入缓存成功")]) if manual else None

    @staticmethod
    async def check(**kwargs) -> MessageChain:
        group = None
        friend = None
        for name, arg in kwargs.items():
            if isinstance(arg, Group):
                group = arg
            if isinstance(arg, Friend):
                friend = arg
        if not group and not friend:
            return MessageChain.create([
                Plain(text=f"无法获取 Group 或 Friend 实例")
            ])
        watched = []
        target = group if group else friend
        field = 'group' if group else 'friend'
        for repo in GithubWatcher.__cached.keys():
            if target.id in GithubWatcher.__cached[repo][field]:
                watched.append(f"{repo[0]}/{repo[1]}")
        res = [Plain(text=f"{'本群' if group else '你'}订阅的仓库有：\n"
                          f"{' '.join(watched)}")]
        return MessageChain.create(res)

    @staticmethod
    async def get_repo_event(repo: tuple, per_page: int = 30, page: int = 1):
        url = GithubWatcher.__base_url \
              + GithubWatcher.__events_url.replace('{owner}', repo[0]).replace('{repo}', repo[1]) \
              + f'?per_page={per_page}&page={page}'
        try:
            res = await GithubWatcher.__session.get(url=url, proxy=proxy)
            res = await res.json()
            if isinstance(res, list):
                return res
            elif isinstance(res, dict):
                if "message" in res.keys():
                    if "API rate limit exceeded" in res["message"]:
                        logger.error("GitHub API 超出速率限制")
                        if not GithubWatcher.__auth:
                            logger.error("请设置 GitHub 用户名和 OAuth Token 以提高限制")
                            GithubWatcher.__first_warned = True
            return res
        except Exception as e:
            logger.error(e)
            logger.error(f"无法取得仓库 {repo[0]}/{repo[1]} 的更新，将跳过该仓库")
            logger.error(f"请检查仓库是否存在{'，或者 GitHub 用户名与 OAuth Token 是否配置正确' if GithubWatcher.__auth else ''}")
            GithubWatcher.__cached[repo]['enabled'] = False
            return None

    @staticmethod
    async def a_generate_plain(event: dict):
        return await asyncio.get_event_loop().run_in_executor(None, GithubWatcher.generate_plain, event)

    @staticmethod
    def generate_plain(event: dict):
        actor = event['actor']['display_login']
        event_time = datetime.fromisoformat(event['created_at'] + '+08:00') \
            .strftime('%Y-%m-%d %H:%M:%S')
        resp = None
        if event['type'] == 'IssuesEvent':
            if event['payload']['action'] == 'opened':
                title = event['payload']['issue']['title']
                number = event['payload']['issue']['number']
                body = event['payload']['issue']['body']
                if body:
                    if len(body) > 100:
                        body = body[:100] + "......"
                    body = body + "\n"
                link = event['payload']['issue']['html_url']
                resp = Plain(text=f"----------\n"
                                  f"[新 Issue]\n"
                                  f"#{number} {title}\n"
                                  f"{body}\n"
                                  f"\n"
                                  f"发布人：{actor}\n"
                                  f"时间：{event_time}\n"
                                  f"链接：{link}\n")
        elif event['type'] == 'IssueCommentEvent':
            if event['payload']['action'] == 'created':
                title = event['payload']['issue']['title']
                number = event['payload']['issue']['number']
                body = event['payload']['comment']['body']
                if body:
                    if len(body) > 100:
                        body = body[:100] + "......"
                    body = body + "\n"
                link = event['payload']['comment']['html_url']
                resp = Plain(text=f"----------\n"
                                  f"[新 Comment]\n"
                                  f"#{number} {title}\n"
                                  f"{body}"
                                  f"\n"
                                  f"发布人：{actor}\n"
                                  f"时间：{event_time}\n"
                                  f"链接：{link}\n")
        elif event['type'] == 'PullRequestEvent':
            if event['payload']['action'] == 'opened':
                title = event['payload']['pull_request']['title']
                number = event['payload']['pull_request']['number']
                body = event['payload']['pull_request']['body']
                if body:
                    if len(body) > 100:
                        body = body[:100] + "......"
                    body = body + "\n"
                head = event['payload']['pull_request']['head']['label']
                base = event['payload']['pull_request']['base']['label']
                commits = event['payload']['pull_request']['commits']
                link = event['payload']['pull_request']['html_url']
                resp = Plain(text=f"----------\n"
                                  f"[新 PR]\n"
                                  f"#{number} {title}\n"
                                  f"{body}"
                                  f"\n"
                                  f"{head} → {base}\n"
                                  f"提交数：{commits}\n"
                                  f"发布人：{actor}\n"
                                  f"时间：{event_time}\n"
                                  f"链接：{link}\n")
        elif event['type'] == 'PushEvent':
            commits = []
            for commit in event['payload']['commits']:
                commits.append(f"· [{commit['author']['name']}] {commit['message']}")
            resp = Plain(text=f"----------\n"
                              f"[新 Push]\n"
                              + "\n".join(commits) +
                              f"\n"
                              f"提交数：{len(commits)}\n"
                              f"发布人：{actor}\n"
                              f"时间：{event_time}\n")
        elif event['type'] == 'CommitCommentEvent':
            body = event['payload']['comment']['body']
            if body:
                if len(body) > 100:
                    body = body[:100] + "......"
                body = body + "\n"
            link = event['payload']['comment']['html_url']
            resp = Plain(text=f"----------\n"
                              f"[新 Comment]\n"
                              f"{body}"
                              f"\n"
                              f"发布人：{actor}\n"
                              f"时间：{event_time}\n"
                              f"链接：{link}\n")
        return resp if resp else None

    @staticmethod
    async def github_schedule(**kwargs):
        if GithubWatcher.__is_running:
            return None
        if not GithubWatcher.initialize:
            GithubWatcher.update_cache()
            GithubWatcher.initialize = True
        try:
            app = None
            manual = False
            repo = None
            per_page = 30
            page = 1
            for name, arg in kwargs.items():
                if name == "manual" and isinstance(arg, bool):
                    manual = arg
                if name == "repo" and isinstance(arg, tuple):
                    repo = arg
                if name == "per_page" and isinstance(arg, int):
                    per_page = arg
                if name == "page" and isinstance(arg, int):
                    page = arg
                if isinstance(arg, Ariadne):
                    app = arg
            if not app:
                logger.error("无法获得 Ariadne 实例")
                return None
            if GithubWatcher.__status and repo:
                res = []
                if events := await GithubWatcher.get_repo_event(repo, per_page, page):
                    GithubWatcher.__cached[repo]['last_id'] = int(events[0]['id'])
                    if resp := await GithubWatcher.a_generate_plain(events[0]):
                        res.append(resp)
                if not res:
                    return None
                res.insert(0, Plain(text=f"仓库：{repo[0]}/{repo[1]}\n"))
                res.append(Plain(text=f"----------\n获取时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
                return MessageChain.create(res)
            if GithubWatcher.__status and not GithubWatcher.__is_running:
                GithubWatcher.__is_running = True
                for repo in GithubWatcher.__cached.keys():
                    if not GithubWatcher.__cached[repo]['enabled']:
                        continue
                    res = []
                    if events := await GithubWatcher.get_repo_event(repo, per_page, page):
                        last_id = GithubWatcher.__cached[repo]['last_id']
                        new_last_id = last_id
                        for index, event in enumerate(events):
                            if index == 0:
                                new_last_id = int(event['id'])
                            if int(event['id']) <= last_id:
                                break
                            if resp := await GithubWatcher.a_generate_plain(event):
                                res.append(resp)
                            else:
                                continue
                        GithubWatcher.__cached[repo]['last_id'] = new_last_id
                        GithubWatcher.store_cache()
                    if res:
                        res.insert(0, Plain(text=f"仓库：{repo[0]}/{repo[1]}\n"))
                        res.append(Plain(text=f"----------\n获取时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
                        res = MessageChain.create(res)
                        if manual:
                            GithubWatcher.__is_running = False
                            return MessageItem(res, Normal())
                        for group in GithubWatcher.__cached[repo]['group']:
                            try:
                                await app.sendGroupMessage(group, res)
                            except (AccountMuted, UnknownTarget):
                                pass
                        for friend in GithubWatcher.__cached[repo]['friend']:
                            try:
                                await app.sendFriendMessage(friend, res)
                            except UnknownTarget:
                                pass
                GithubWatcher.__is_running = False
        except Exception as e:
            logger.error(e)
            GithubWatcher.__is_running = False
        else:
            if manual:
                return MessageItem(MessageChain.create([Plain(text="Github 订阅功能已关闭。")]), QuoteSource())


@scheduler.schedule(crontabify("* * * * *"))
async def github_schedule(app: Ariadne):
    try:
        await GithubWatcher.github_schedule(app=app, manual=False)
    except:
        pass
