import datetime
import pandas as pd
from typing import Dict, Any, List
from database.connection import connection
from sqlalchemy import text, Table, String, Column, MetaData


def create_schema_and_table() -> None:
    with connection.engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS attendees"))
        metadata = MetaData("attendees")
        attendee_table: Table = Table(
            "presence",
            metadata,
            Column("seat", String, unique=True, nullable=False, primary_key=True),
            Column("name", String, nullable=False),
            Column("check_in", String, nullable=False),
        )
        metadata.create_all(conn, tables=[attendee_table], checkfirst=True)


def presence_check(seat: str) -> pd.DataFrame:
    with connection.engine.connect() as conn:
        stmt: str = """SELECT seat FROM attendees.presence WHERE seat = :pattern"""
        return pd.read_sql(text(stmt), con=conn, params={"pattern": seat})


def insert_data(data: Dict[str, Any]) -> bool:
    """Update attendee's presence, return True if added successfully"""
    data["check_in"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    if not presence_check(seat=data["seat"]).empty:
        # If present, no update
        return False

    insert_stmt: str = """
    INSERT INTO attendees.presence (seat, name, check_in) VALUES (:seat, :name, :check_in)
    """

    with connection.engine.begin() as conn:
        try:
            conn.execute(text(insert_stmt), parameters=data)
            return True

        except Exception as e:
            print(e)
            conn.rollback()
            return False


def attended_count() -> List[Dict[str, Any]]:
    with connection.engine.connect() as conn:
        try:
            select_stmt: str = """
            SELECT seat, name, check_in FROM attendees.presence 
            WHERE 1=1
            ORDER BY seat
            """

            return pd.read_sql(text(select_stmt), con=conn).to_dict("records")

        except Exception:
            conn.rollback()
            return []


if __name__ == "__main__":
    create_schema_and_table()
