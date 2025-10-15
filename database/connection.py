import os
from sqlalchemy import create_engine, Engine


class Connection:
    websocket_uri: str = os.getenv("WS_URI")
    connection_string: str = os.getenv("DATABASE_URI")
    conn: Engine = create_engine(url=connection_string)


db_connection: Connection = Connection()
