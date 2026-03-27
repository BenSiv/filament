import sqlite3


DEFAULT_REVIEW_VALUES = {
    "atomicity_status": "unknown",
    "connectivity_status": "unknown",
    "duplication_status": "unknown",
    "title_status": "unknown",
}


def _review_columns(cur):
    cur.execute("PRAGMA table_info(ai_review)")
    return {row[1] for row in cur.fetchall()}


def insert_review(cur, qid, nid, promotion_status, action_summary):
    if not nid:
        return
    columns = _review_columns(cur)
    if not columns:
        return

    data = {}
    if "qid" in columns:
        data["qid"] = qid
    if "nid" in columns:
        data["nid"] = nid
    for key, value in DEFAULT_REVIEW_VALUES.items():
        if key in columns:
            data[key] = value
    if "promotion_status" in columns:
        data["promotion_status"] = promotion_status
    if "action_summary" in columns:
        data["action_summary"] = action_summary

    if not data:
        return

    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    sql = f"INSERT INTO ai_review({cols}) VALUES ({placeholders})"
    cur.execute(sql, list(data.values()))
