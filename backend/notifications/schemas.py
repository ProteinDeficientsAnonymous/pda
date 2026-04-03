from datetime import datetime

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: str
    notification_type: str
    event_id: str | None
    message: str
    is_read: bool
    created_at: datetime


class UnreadCountOut(BaseModel):
    count: int
