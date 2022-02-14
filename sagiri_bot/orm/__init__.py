import asyncio
import inspect
import json
import traceback

from sqlalchemy.exc import InternalError
from sqlalchemy.orm import InstrumentedAttribute

from sagiri_bot.orm.async_orm import orm, Setting

orm_cache = {}


attributes = inspect.getmembers(Setting, lambda a: not (inspect.isroutine(a)))
tables = [a[1] for a in attributes if not (a[0].startswith('_') or a[0].endswith('_') or not isinstance(a[1], InstrumentedAttribute))]


async def update_orm_cache():
    column_names = (await orm.execute("SHOW COLUMNS FROM `setting`;")).fetchall()
    column_names = [i[0] for i in column_names]
    values = (await orm.execute("select * from `setting`;")).fetchall()
    for value in values:
        if value[0] not in orm_cache.keys():
            orm_cache[value[0]] = {}
        for index, column_name in enumerate(column_names):
            orm_cache[value[0]][column_name] = value[index]


async def add_setting_column(name: str, value_type=str, default: str = None, nullable: bool = False):
    try:
        sql = f"ALTER TABLE `setting` ADD `{name} {value_type}`"
        sql += f" DEFAULT {default}" if default else ""
        sql += " NOT NULL" if nullable else ""
        sql += ";"
        await orm.execute(sql)
    except InternalError as e:
        if "Duplicate column" in str(e):
            pass
        else:
            traceback.format_exc()


loop = asyncio.get_event_loop()
loop.run_until_complete(update_orm_cache())
