import asyncpg, asyncio

async def test():
    conn = await asyncpg.connect("postgresql://postgres:mysecretpassword@localhost:5432/postgres")
    row = await conn.fetch("SELECT version()")
    print(row)
    await conn.close()

asyncio.run(test())
