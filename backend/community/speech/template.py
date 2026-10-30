from datetime import datetime

from config.auth import gated_jwt
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel

from community.models import SpeechTemplate

router = Router()


class SpeechTemplateOut(BaseModel):
    shared_pm: str
    walk_pm: str
    restaurant_pm: str
    open_roles: list[str]
    updated_at: datetime


def _out(obj: SpeechTemplate) -> SpeechTemplateOut:
    return SpeechTemplateOut(
        shared_pm=obj.shared_pm,
        walk_pm=obj.walk_pm,
        restaurant_pm=obj.restaurant_pm,
        open_roles=obj.open_roles,
        updated_at=obj.updated_at,
    )


@router.get("/speech-template/", response={200: SpeechTemplateOut}, auth=gated_jwt)
def get_speech_template(request):
    return Status(200, _out(SpeechTemplate.get()))
