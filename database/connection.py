import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine



class Connection:
    project_url: str = os.environ["PROJECT_URL"]
    key: str = os.environ["KEY"]
    channel: str = os.environ["CHANNEL"]
    connection_string: str = os.environ["DATABASE_URI"]
    engine: AsyncEngine = create_async_engine(url=connection_string, pool_pre_ping=True)


connection: Connection = Connection()
