from ninja import Router

from community._attendance_report import router as attendance_report_router
from community._calendar import router as calendar_router
from community._docs import router as docs_router
from community._docs_documents import router as docs_documents_router
from community._event_actions import router as event_actions_router
from community._event_blasts import router as event_blasts_router
from community._event_cohost_invites import router as event_cohost_invites_router
from community._event_comments import router as event_comments_router
from community._event_flags import router as event_flags_router

# Re-export symbols imported directly in tests
from community._event_helpers import (  # noqa: F401
    _build_guest_list,
    _can_see_phones,
    _find_my_rsvp,
)
from community._event_host_actions import router as event_host_actions_router
from community._event_invitations import router as event_invitations_router
from community._event_rsvps import router as event_rsvps_router
from community._event_schemas import EventPatchIn  # noqa: F401
from community._event_tags import router as event_tags_router
from community._events import router as events_router
from community._feedback import router as feedback_router
from community._geocode import router as geocode_router
from community._guidelines import router as guidelines_router
from community._home import router as home_router
from community._join_form import router as join_form_router
from community._join_request_resend import router as join_request_resend_router
from community._join_request_submit import router as join_request_submit_router
from community._join_requests import router as join_requests_router
from community._login_link import router as login_link_router
from community._member_promotion_message import (
    router as member_promotion_message_router,
)
from community._pages import router as pages_router
from community._poll_options import router as poll_options_router
from community._polls import router as polls_router
from community._public_rsvp_manage import router as public_rsvp_manage_router
from community._public_rsvp_resend import router as public_rsvp_resend_router
from community._public_rsvp_submit import router as public_rsvp_submit_router
from community._surveys import router as surveys_router
from community._surveys_public import router as surveys_public_router
from community._tentative_approval_message import (
    router as tentative_approval_message_router,
)
from community._version import router as version_router
from community._welcome_template import router as welcome_template_router
from community._whatsapp_link import router as whatsapp_link_router

router = Router()
router.add_router("", guidelines_router)
router.add_router("", home_router)
router.add_router("", pages_router)
router.add_router("", join_form_router)
router.add_router("", join_requests_router)
router.add_router("", join_request_submit_router)
router.add_router("", join_request_resend_router)
router.add_router("", login_link_router)
router.add_router("", feedback_router)
# Mount before events_router so the literal `/events/attendance-report/` route
# resolves before that router's `/events/{event_id}/` parameterized route.
router.add_router("", attendance_report_router)
router.add_router("", events_router)
router.add_router("", event_tags_router)
router.add_router("", event_rsvps_router)
router.add_router("", event_host_actions_router)
router.add_router("", public_rsvp_submit_router)
# Mount resend before manage so the literal `/public/my-rsvps/resend/` route
# resolves before that router's `/public/my-rsvps/{event_id}/` parameterized route.
router.add_router("", public_rsvp_resend_router)
router.add_router("", public_rsvp_manage_router)
router.add_router("", event_actions_router)
router.add_router("", event_blasts_router)
router.add_router("", event_cohost_invites_router)
router.add_router("", event_invitations_router)
router.add_router("", event_flags_router)
router.add_router("", calendar_router)
router.add_router("", welcome_template_router)
router.add_router("", tentative_approval_message_router)
router.add_router("", member_promotion_message_router)
router.add_router("", whatsapp_link_router)
router.add_router("", polls_router)
router.add_router("", poll_options_router)
router.add_router("", event_comments_router)
router.add_router("", surveys_router)
router.add_router("", surveys_public_router)
router.add_router("", docs_router)
router.add_router("", docs_documents_router)
router.add_router("", geocode_router)
router.add_router("", version_router)
