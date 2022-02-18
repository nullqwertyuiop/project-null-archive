import yaml
from os import environ
from loguru import logger
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from sqlalchemy import select, update, insert, delete
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import Column, Integer, String, DateTime, Boolean, BLOB, BIGINT

from .adapter import get_adapter

yaml.warnings({'YAMLLoadWarning': False})
environ['NLS_LANG'] = 'AMERICAN_AMERICA.AL32UTF8'


# DB_LINK = 'oracle://test:123456@localhost:1521/xe'
# DB_LINK = "mysql+aiomysql://root:pass@localhost:3306/test"
# DB_LINK = "sqlite:///data.db"


def get_config(config: str):
    with open('config.yaml', 'r', encoding='utf-8') as f:  # 从json读配置
        configs = yaml.load(f.read(), Loader=yaml.BaseLoader)
    if config in configs.keys():
        return configs[config]
    else:
        logger.error(f"getConfig Error: {config}")


DB_LINK = get_config("db_link")


# DB_LINK = "sqlite+aiosqlite:///data.db"


class AsyncEngine:
    def __init__(self, db_link):
        self.engine = create_async_engine(
            db_link,
            **get_adapter(db_link),
            echo=False
        )

    async def execute(self, sql, **kwargs):
        async with AsyncSession(self.engine) as session:
            try:
                result = await session.execute(sql, **kwargs)
                await session.commit()
                return result
            except Exception as e:
                await session.rollback()
                # await session.close()
                raise e

    async def fetchall(self, sql):
        return (await self.execute(sql)).fetchall()

    async def fetchone(self, sql):
        # self.warning(sql)
        result = await self.execute(sql)
        one = result.fetchone()
        if one:
            return one
        else:
            return None

    async def fetchone_dt(self, sql, n=999999):
        # self.warning(sql)
        result = await self.execute(sql)
        columns = result.keys()
        length = len(columns)
        for _ in range(n):
            one = result.fetchone()
            if one:
                yield {columns[i]: one[i] for i in range(length)}

    @staticmethod
    def warning(x):
        print('\033[033m{}\033[0m'.format(x))

    @staticmethod
    def error(x):
        print('\033[031m{}\033[0m'.format(x))


class AsyncORM(AsyncEngine):
    """对象关系映射（Object Relational Mapping）"""

    def __init__(self, conn):
        super().__init__(conn)
        self.session = AsyncSession(bind=self.engine)
        self.Base = declarative_base(self.engine)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        # self.create_all()

    # def __del__(self):
    #     self.session.close()

    async def create_all(self):
        """创建所有表"""
        async with self.engine.begin() as conn:
            await conn.run_sync(self.Base.metadata.create_all)

    async def drop_all(self):
        """删除所有表"""
        async with self.engine.begin() as conn:
            await conn.run_sync(self.Base.metadata.drop_all)

    async def add(self, table, dt):
        """插入"""
        async with self.async_session() as session:
            async with session.begin():
                session.add(table(**dt), _warn=False)
            await session.commit()

    async def update(self, table, condition, dt):
        await self.execute(update(table).where(*condition).values(**dt))

    async def insert_or_update(self, table, condition, dt):
        if (await self.execute(select(table).where(*condition))).all():
            return await self.execute(update(table).where(*condition).values(**dt))
        else:
            return await self.execute(insert(table).values(**dt))

    async def insert_or_ignore(self, table, condition, dt):
        if not (await self.execute(select(table).where(*condition))).all():
            return await self.execute(insert(table).values(**dt))

    async def delete(self, table, condition):
        return await self.execute(delete(table).where(*condition))

    async def init_check(self) -> bool:
        for table in Base.__subclasses__():
            try:
                await self.fetchone(select(table))
            except OperationalError:
                async with self.engine.begin() as conn:
                    await conn.run_sync(table.__table__.create(self.engine))
                return False
        return True


orm = AsyncORM(DB_LINK)

Base = orm.Base


class ChatRecord(Base):
    """ 聊天记录表 """
    __tablename__ = "chat_record"

    id = Column(Integer, primary_key=True)
    time = Column(DateTime, nullable=False)
    group_id = Column(BIGINT, nullable=False)
    member_id = Column(BIGINT, nullable=False)
    persistent_string = Column(String(length=4000), nullable=False)
    seg = Column(String(length=4000), nullable=False)


class BlackList(Base):
    """ 黑名单表 """
    __tablename__ = "black_list"

    member_id = Column(BIGINT, primary_key=True)
    group_id = Column(BIGINT, primary_key=True)
    is_global = Column(Boolean, default=False)


class UserPermission(Base):
    """ 用户等级表（管理权限） """
    __tablename__ = "user_permission"

    group_id = Column(BIGINT, primary_key=True)
    member_id = Column(BIGINT, primary_key=True)
    level = Column(Integer, default=1)


class Setting(Base):
    """ 群组设置 """
    __tablename__ = "setting"

    group_id = Column(BIGINT, primary_key=True)
    group_name = Column(String(length=60), nullable=False)
    repeat = Column(Boolean, default=True)
    frequency_limit = Column(Boolean, default=True)
    setu = Column(Boolean, default=False)
    real = Column(Boolean, default=False)
    real_high_quality = Column(Boolean, default=False)
    bizhi = Column(Boolean, default=False)
    r18 = Column(Boolean, default=False)
    img_search = Column(Boolean, default=True)
    bangumi_search = Column(Boolean, default=True)
    compile = Column(Boolean, default=True)
    dice = Column(Boolean, default=True)
    avatar_func = Column(Boolean, default=True)
    anti_revoke = Column(Boolean, default=False)
    anti_flash_image = Column(Boolean, default=False)
    online_notice = Column(Boolean, default=False)
    debug = Column(Boolean, default=False)
    switch = Column(Boolean, default=True)
    active = Column(Boolean, default=True)
    music = Column(String(length=10), default="off")
    r18_process = Column(String(length=10), default="revoke")
    speak_mode = Column(String(length=10), default="chat")
    long_text_type = Column(String(length=5), default="text")
    voice = Column(String(length=10), default="101015")
    prostitute = Column(Boolean, default=True)
    sign_in = Column(Boolean, default=True)
    notice = Column(Boolean, default=True)
    img_search_cost = Column(BIGINT, default=300)
    ten_husband_cost = Column(BIGINT, default=500)
    ten_husband_limit = Column(BIGINT, default=-1)
    lah_simulation_cost = Column(BIGINT, default=1000)
    lah_simulation_limit = Column(BIGINT, default=-1)
    chat_confidence = Column(String(length=256), default="0.333333")
    img_search_similarity = Column(String(length=256), default="60.0")
    tarot = Column(BIGINT, default=-1)
    search_helper = Column(Boolean, default=True)
    random_husband = Column(Boolean, default=True)
    ten_husband = Column(Boolean, default=True)
    gacha_simulator = Column(Boolean, default=True)
    trusted = Column(Boolean, default=False)
    # abbreviated_prediction = Column(Boolean, default=True)
    # abstract_convert = Column(Boolean, default=True)
    bilibili_app_parse = Column(Boolean, default=False)
    # cp_generator = Column(Boolean, default=True)
    event_listener = Column(Boolean, default=True)
    # github_info = Column(Boolean, default=True)
    # group_wordcloud = Column(Boolean, default=True)
    # words_explain = Column(Boolean, default=True)
    # joke = Column(Boolean, default=True)
    # keyword_reply = Column(Boolean, default=True)
    # marketing_content = Column(Boolean, default=True)
    # message_merge = Column(Boolean, default=True)
    # pdf = Column(Boolean, default=True)
    # pero_dog = Column(Boolean, default=True)


class UserCalledCount(Base):
    """ 群员调用记录 """
    __tablename__ = "user_called_count"

    group_id = Column(BIGINT, primary_key=True)
    member_id = Column(BIGINT, primary_key=True)
    setu = Column(Integer, default=0)
    real = Column(Integer, default=0)
    bizhi = Column(Integer, default=0)
    at = Column(Integer, default=0)
    search = Column(Integer, default=0)
    song_order = Column(Integer, default=0)
    chat_count = Column(Integer, default=0)
    functions = Column(Integer, default=0)


class KeywordReply(Base):
    """ 关键词回复 """
    __tablename__ = "keyword_reply"

    keyword = Column(String(length=200), primary_key=True)
    # keyword_type = Column(String(length=20), default="fullmatch")
    reply_type = Column(String(length=10), nullable=False)
    reply = Column(BLOB, nullable=False)
    reply_md5 = Column(String(length=32), primary_key=True)


class TriggerKeyword(Base):
    """ 关键词触发功能 """
    __tablename__ = "trigger_keyword"

    keyword = Column(String(length=60), primary_key=True)
    function = Column(String(length=20))


class FunctionCalledRecord(Base):
    """ 功能调用记录 """
    __tablename__ = "function_called_record"

    id = Column(Integer, primary_key=True)
    time = Column(DateTime, nullable=False)
    group_id = Column(BIGINT, nullable=False)
    member_id = Column(BIGINT, nullable=False)
    function = Column(String(length=40), nullable=False)
    result = Column(Boolean, default=True)


class SignInReward(Base):
    """ 签到奖励 """
    __tablename__ = "sign_in_reward"

    qq = Column(BIGINT, primary_key=True)
    group_id = Column(BIGINT, primary_key=True)
    coin = Column(BIGINT, nullable=False, default=0)
    last_date = Column(BIGINT, nullable=False, default=0)
    streak = Column(BIGINT, nullable=False, default=0)
    extra = Column(BIGINT, nullable=False, default=0)


class Prostitute(Base):
    """ 卖铺奖励 """
    __tablename__ = "prostitute"

    qq = Column(BIGINT, primary_key=True)
    group_id = Column(BIGINT, primary_key=True)
    client = Column(BIGINT, nullable=False)
    last_date = Column(BIGINT, nullable=False, default=0)
    pay = Column(BIGINT, nullable=False, default=0)
    self_race = Column(String(length=6), default="human")
    migrate = Column(Boolean, default=False)


class MigrateProstitute(Base):
    """ 卖铺奖励迁移 """
    __tablename__ = "migrate_prostitute"

    group = Column(BIGINT, primary_key=True)
    qq = Column(BIGINT, primary_key=True)
    client = Column(BIGINT, nullable=False, default=0)
    last_date = Column(BIGINT, nullable=False, default=0)
    pay = Column(BIGINT, nullable=False, default=0)
    self_race = Column(String(length=256), nullable=False, default="human")
    client_race = Column(String(length=256), nullable=False, default="human")
    frequency = Column(BIGINT, nullable=False, default=0)
    self_race_edit = Column(BIGINT, nullable=False, default=-1)
    limit_date = Column(BIGINT, nullable=False, default=0)
    history_total = Column(BIGINT, nullable=False, default=0)


class RandomHusband(Base):
    """ 随机老公 """
    __tablename__ = "random_husband"

    group = Column(BIGINT, primary_key=True)
    qq = Column(BIGINT, primary_key=True)
    last_date = Column(BIGINT, nullable=False, default=0)
    last_file = Column(String(length=256), nullable=True, default="nonexistent")
    ten_husband_times = Column(BIGINT, nullable=False, default=0)
    ten_husband_last_date = Column(BIGINT, nullable=False, default=0)


class UsageRecord(Base):
    """ 使用记录 """
    __tablename__ = "usage_record"

    group = Column(BIGINT, primary_key=True)
    qq = Column(BIGINT, primary_key=True)
    last_date = Column(BIGINT, nullable=False, default=0)
    tarot = Column(BIGINT, nullable=False, default=0)
    clow_card = Column(BIGINT, nullable=False, default=0)
    clear_card = Column(BIGINT, nullable=False, default=0)


class LiveAHeroSimulator(Base):
    """ Live a Hero 模拟抽卡 """
    __tablename__ = "live_a_hero_simulator"

    group = Column(BIGINT, primary_key=True)
    qq = Column(BIGINT, primary_key=True)
    last_date = Column(BIGINT, nullable=False, default=0)
    simulate_times = Column(BIGINT, nullable=False, default=0)
    free_tokens = Column(BIGINT, nullable=False, default=0)
    three_stars_hero = Column(BIGINT, nullable=False, default=0)
    four_stars_hero = Column(BIGINT, nullable=False, default=0)
    five_stars_hero = Column(BIGINT, nullable=False, default=0)
    three_stars_sk = Column(BIGINT, nullable=False, default=0)
    four_stars_sk = Column(BIGINT, nullable=False, default=0)
    total_times = Column(BIGINT, nullable=False, default=0)


class GachaSimulatorRecord(Base):
    """ 模拟抽卡记录 """
    __tablename__ = "gacha_simulator_record"

    id = Column(Integer, primary_key=True)
    group_id = Column(BIGINT, nullable=False, default=0)
    member_id = Column(BIGINT, nullable=False, default=0)
    gacha = Column(String(length=32), nullable=False, default="0")
    is_ten = Column(Boolean, default=True)
    time = Column(String(length=32), nullable=False, default="0")
    a = Column(String(length=200), nullable=True)
    b = Column(String(length=200), nullable=True)
    c = Column(String(length=200), nullable=True)
    d = Column(String(length=200), nullable=True)
    e = Column(String(length=200), nullable=True)
    f = Column(String(length=200), nullable=True)
    g = Column(String(length=200), nullable=True)
    h = Column(String(length=200), nullable=True)
    i = Column(String(length=200), nullable=True)
    j = Column(String(length=200), nullable=True)


class AdvancedSetu(Base):
    """ 高级色图 """
    __tablename__ = "advanced_setu"

    group = Column(BIGINT, primary_key=True)
    strategy = Column(String(length=256), nullable=False, default="s")
    mixed = Column(Boolean, nullable=False)
    last_time = Column(BIGINT, nullable=False, default=0)
    trigger_word = Column(String(length=256), nullable=True, default="")
    first_run = Column(Boolean, nullable=False, default=True)
    process = Column(String(length=10), nullable=False, default="noProcess")


class PermanentBlackList(Base):
    """ 永久黑名单 """
    __tablename__ = "permanent_black_list"

    id = Column(BIGINT, primary_key=True)
    type = Column(String(length=32), primary_key=True)
    reason = Column(String(length=4000), nullable=False, default="0")
    date = Column(String(length=200), nullable=False, default="0")


class ScheduledMessage(Base):
    """ 定时消息 """
    __tablename__ = "scheduled_message"

    group_id = Column(BIGINT, primary_key=True)
    time = Column(String(length=20), primary_key=True)
    message = Column(String(length=4000), nullable=False, default="0")


class WalletBalance(Base):
    """ 钱包 """
    __tablename__ = "wallet"

    group_id = Column(BIGINT, primary_key=True)
    member_id = Column(BIGINT, primary_key=True)
    balance = Column(BIGINT, nullable=False, default=0)
    time = Column(String(length=32), nullable=False, default="0")


class WalletDetail(Base):
    """ 钱包明细 """
    __tablename__ = "wallet_detail"

    id = Column(Integer, primary_key=True)
    group_id = Column(BIGINT, nullable=False, default=0)
    member_id = Column(BIGINT, nullable=False, default=0)
    record = Column(BIGINT, nullable=False, default=0)
    reason = Column(String(length=200), nullable=False, default="0")
    balance = Column(BIGINT, nullable=False, default=0)
    time = Column(String(length=32), nullable=False, default="0")


class ItemInventory(Base):
    """ 背包 """
    __tablename__ = "inventory"

    member_id = Column(BIGINT, primary_key=True)
    item = Column(BIGINT, nullable=False, default=0)
    amount = Column(BIGINT, nullable=False, default=0)
    used_amount = Column(BIGINT, nullable=False, default=0)


class InventoryDetail(Base):
    """ 背包明细 """
    __tablename__ = "inventory_detail"

    id = Column(Integer, primary_key=True)
    member_id = Column(BIGINT, nullable=False, default=0)
    item = Column(BIGINT, nullable=False, default=0)
    amount = Column(BIGINT, nullable=False, default=0)
    get = Column(Boolean, default=True)


class LoliconData(Base):
    """ lolicon api数据 """
    __tablename__ = "lolicon_data"

    pid = Column(BIGINT, primary_key=True)
    p = Column(Integer, primary_key=True)
    uid = Column(BIGINT, nullable=False)
    title = Column(String(length=200), nullable=False)
    author = Column(String(length=200), nullable=False)
    r18 = Column(Boolean, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    tags = Column(String(length=1000), nullable=False)
    ext = Column(String(length=20), nullable=False)
    upload_date = Column(DateTime, nullable=False)
    original_url = Column(String(length=200), nullable=False)


class InviteData(Base):
    """ 邀请 """
    __tablename__ = "invite_data"

    id = Column(Integer, primary_key=True)
    group_id = Column(BIGINT, nullable=False, default=0)
    supplicant_id = Column(BIGINT, nullable=False, default=0)
    time = Column(DateTime, nullable=False)
    status = Column(Boolean, nullable=False, default=True)

# class SchedulerTasks(Base):
#     """ 计划任务 """
#     __tablename__ = "scheduler_tasks"
# print("\n".join([f"{i}: {type(getattr(JLUEpidemicAccountInfo, i))}" for i in dir(JLUEpidemicAccountInfo)]))
