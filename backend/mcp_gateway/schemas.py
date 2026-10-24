from datetime import datetime

from pydantic import BaseModel


class ConnectRequestOut(BaseModel):
    client_name: str
    redirect_host: str
    expires_at: datetime


class ConnectRedirectOut(BaseModel):
    redirect_url: str
