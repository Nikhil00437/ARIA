from datetime import datetime
from typing import Optional
from pymongo import MongoClient

mongo = MongoClient("mongodb://localhost:27017/")
mongo.server_info()
db = mongo["Aria-conversations"]
collection      = db["Conversations"]
cmd_log_col     = db["CommandLog"]

# Command log
def log_command(session_id: str, command: str, output: str, mode: str) -> None:
    try:
        cmd_log_col.insert_one({
            "session_id": session_id,
            "type":       "command",
            "command":    command,
            "output":     output[:2000],
            "mode":       mode,
            "timestamp":  datetime.now(),
        })
    except Exception: pass

def get_command_history(session_id: str, limit: int = 20) -> list:
    try:
        docs = list(
            cmd_log_col.find(
                {"session_id": session_id},
                {"_id": 0, "command": 1, "timestamp": 1, "mode": 1},
            ).sort("timestamp", -1).limit(limit)
        )
        return list(reversed(docs))
    except Exception: return []
    
# Session persistence
def save_session_messages(session_id: str, user_msg: str, assistant_msg: str, mode: str) -> None:
    try:
        collection.update_one(
            {"session_id": session_id},
            {"$push": {"messages": {"$each": [
                {"role": "user",      "content": user_msg},
                {"role": "assistant", "content": assistant_msg, "mode": mode},
            ]}}},
            upsert=True,
        )
    except Exception: pass
