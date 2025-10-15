import datetime
import pandas as pd
from typing import Dict, Any, List
from database.connection import db_connection
from sqlalchemy import text, Table, String, Column, MetaData


def create_schema_and_table() -> None:
    with db_connection.conn.begin() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS attendees"))
        metadata = MetaData("attendees")
        attendee_table: Table = Table(
            "presence",
            metadata,
            Column("seat", String, unique=True, nullable=False, primary_key=True),
            Column("name", String, nullable=False),
            Column("check_in", String, nullable=False),
        )
        metadata.create_all(connection, tables=[attendee_table], checkfirst=True)


def presence_check(seat: str) -> pd.DataFrame:
    with db_connection.conn.connect() as connection:
        stmt: str = """SELECT seat FROM attendees.presence WHERE seat = :pattern"""
        return pd.read_sql(text(stmt), con=connection, params={"pattern": seat})


def insert_data(data: Dict[str, Any]) -> None:
    data["check_in"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    create_schema_and_table()

    with db_connection.conn.connect() as connection:
        try:
            if not presence_check(seat=data["seat"]).empty:
                return

            insert_stmt: str = """
            INSERT INTO attendees.presence (seat, name, check_in) VALUES (:seat, :name, :check_in)
            """
            connection.execute(text(insert_stmt), parameters=data)
            connection.commit()
            return

        except Exception as e:
            print(e)
            connection.rollback()
            return "N/A"


def attended_count() -> List[Dict[str, Any]]:
    with db_connection.conn.connect() as connection:
        try:
            select_stmt: str = """
            SELECT seat, name, check_in FROM attendees.presence 
            WHERE 1=1
            ORDER BY seat
            """

            return pd.read_sql(text(select_stmt), con=connection).to_dict("records")

        except Exception:
            connection.rollback()
            return []


if __name__ == "__main__":
    create_schema_and_table()
