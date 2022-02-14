# import asyncio
# import inspect
# import traceback
#
# from sqlalchemy import select, Column, Boolean
# from sqlalchemy.exc import InternalError
# from sqlalchemy.orm import InstrumentedAttribute
#
# from sagiri_bot.orm.async_orm import Setting, orm
#
# attributes = inspect.getmembers(Setting, lambda a: not (inspect.isroutine(a)))
# tables = [a[1] for a in attributes if not (a[0].startswith('_') or a[0].endswith('_') or not isinstance(a[1], InstrumentedAttribute))]
# metadata = [a[1] for a in attributes if a[0] == "metadata"][0]
# group = [a[1] for a in attributes if a[0] == 'group_id' and isinstance(a[1], InstrumentedAttribute)][0]
# print("\n".join([f"{a[0]}: {a[1]}" for a in attributes if not (a[0].startswith('_') or a[0].endswith('_') or not isinstance(a[1], InstrumentedAttribute))]))
#
# print(metadata)
#
# setattr(Setting, "test_column", Column(Boolean, default=False))
#
# print("\n".join([f"{a[0]}: {a[1]}" for a in attributes if not (a[0].startswith('_') or a[0].endswith('_') or not isinstance(a[1], InstrumentedAttribute))]))
#
#
#
# async def m():
#     try:
#         await orm.execute("alter table `setting` add `test_column` boolean default false not null;")
#     except InternalError as e:
#         if "Duplicate column" in str(e):
#             pass
#         else:
#             traceback.format_exc()
#
#     a = (await orm.execute("SHOW COLUMNS FROM `setting`;")).fetchall()
#     la = [i[0] for i in a]
#     print(la)
#     b = (await orm.execute("select * from `setting`;")).fetchall()
#     print(b)
#
# loop = asyncio.get_event_loop()
# loop.run_until_complete(m())
#
