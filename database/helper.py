from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Hashable
from database.connection import connection
from sqlalchemy import text, Table, String, Column, MetaData, RowMapping, Row


async def create_schema_and_table() -> None:
    async with connection.engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS attendees"))
        metadata = MetaData()
        attendee_table: Table = Table(
            "presence",
            metadata,
            Column("seat", String, unique=True, nullable=False, primary_key=True),
            Column("name", String, nullable=False),
            Column("check_in", String, nullable=False),
            schema="attendees",
        )
        
        await conn.run_sync(
            metadata.create_all, tables=[attendee_table], checkfirst=True
        )


async def presence_check(seat: str) -> List[RowMapping]:
    async with connection.engine.connect() as conn:
        stmt: str = """SELECT seat FROM attendees.presence WHERE seat = :pattern"""
        presented: List[Row] = (
            await conn.execute(text(stmt), parameters={"pattern": seat})
        ).fetchall()
        
        return presented


async def insert_data(payload: Dict[str, Any]) -> bool:
    """Update attendee's presence, return True if added successfully"""
    payload["check_in"] = datetime.now(ZoneInfo("Asia/Bangkok")).strftime("%Y-%m-%d %H:%M")

    if await presence_check(seat=payload["seat"]):
        # If present, no update
        return False

    insert_stmt: str = """
    INSERT INTO attendees.presence (seat, name, check_in) VALUES (:seat, :name, :check_in)
    """

    async with connection.engine.begin() as conn:
        try:
            await conn.execute(text(insert_stmt), parameters=payload)
            return True

        except Exception as e:
            print(e)
            await conn.rollback()
            return False


async def attended_count() -> List[Dict[Hashable, Any]]:
    async with connection.engine.connect() as conn:
        try:
            select_stmt: str = """
            SELECT seat, name, check_in FROM attendees.presence 
            WHERE 1=1
            ORDER BY seat ASC
            """

            result: List[RowMapping] = (await conn.execute(text(select_stmt))).mappings().all()
            presented: List[Dict[Hashable, Any]] = [
                dict(data) for data in result
            ]
            
            return presented

        except Exception:
            await conn.rollback()
            return []


if __name__ == "__main__":
    create_schema_and_table()
