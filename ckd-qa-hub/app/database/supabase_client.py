import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        _client = create_client(url, key)
    return _client


def fetch_warning_letters(limit: int = 100, offset: int = 0) -> list[dict]:
    db = get_client()
    res = (
        db.table("warning_letters")
        .select("*, ai_analyses(*)")
        .order("issued_date", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return res.data


def fetch_fda_483(limit: int = 100, offset: int = 0) -> list[dict]:
    db = get_client()
    res = (
        db.table("fda_483")
        .select("*, ai_analyses(*)")
        .order("inspection_date", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return res.data


def fetch_mfds_notices(limit: int = 100) -> list[dict]:
    db = get_client()
    res = (
        db.table("mfds_notices")
        .select("*, ai_analyses(*)")
        .order("published_date", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data


def fetch_weekly_briefing(week_start: str) -> dict | None:
    db = get_client()
    res = (
        db.table("weekly_briefings")
        .select("*")
        .eq("week_start", week_start)
        .maybe_single()
        .execute()
    )
    return res.data


def upsert_ai_analysis(source_type: str, source_id: str, analysis: dict) -> None:
    db = get_client()
    db.table("ai_analyses").upsert(
        {"source_type": source_type, "source_id": source_id, **analysis},
        on_conflict="source_type,source_id",
    ).execute()


def upsert_weekly_briefing(week_start: str, content: str, actions: str) -> None:
    db = get_client()
    db.table("weekly_briefings").upsert(
        {"week_start": week_start, "briefing_content": content, "action_items": actions},
        on_conflict="week_start",
    ).execute()


def count_new_this_week(table: str, date_col: str) -> int:
    """이번 주(월요일~오늘) 신규 건수 반환"""
    from datetime import date, timedelta
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    db = get_client()
    res = (
        db.table(table)
        .select("id", count="exact")
        .gte(date_col, monday.isoformat())
        .execute()
    )
    return res.count or 0
