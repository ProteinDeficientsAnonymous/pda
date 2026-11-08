from datetime import datetime

from config.auth import gated_jwt
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel

from community.models import MemberRestoredEmailTemplate

router = Router()


class MemberRestoredEmailOut(BaseModel):
    body: str
    updated_at: datetime


def _out(obj: MemberRestoredEmailTemplate) -> MemberRestoredEmailOut:
    return MemberRestoredEmailOut(body=obj.body, updated_at=obj.updated_at)


@router.get("/member-restored-email/", response={200: MemberRestoredEmailOut}, auth=gated_jwt)
def get_member_restored_email(request):
    return Status(200, _out(MemberRestoredEmailTemplate.get()))
