from config.auth import gated_jwt
from ninja import Router
from ninja.responses import Status

from community.message_templates.member_promotion_email import MemberPromotionEmailOut
from community.models import MemberRestoredEmailTemplate

router = Router()


def _out(obj: MemberRestoredEmailTemplate) -> MemberPromotionEmailOut:
    return MemberPromotionEmailOut(body=obj.body, updated_at=obj.updated_at)


@router.get("/member-restored-email/", response={200: MemberPromotionEmailOut}, auth=gated_jwt)
def get_member_restored_email(request):
    return Status(200, _out(MemberRestoredEmailTemplate.get()))
