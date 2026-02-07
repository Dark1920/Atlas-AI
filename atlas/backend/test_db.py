import asyncio
import aiosqlite

async def test_connection():
    try:
        conn = await aiosqlite.connect('./atlas.db')
        print('Connected successfully!')
        await conn.close()
    except Exception as e:
        print(f'Connection failed: {e}')

if __name__ == '__main__':
    asyncio.run(test_connection())