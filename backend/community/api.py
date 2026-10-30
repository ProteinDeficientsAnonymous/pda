from ninja import Router

from community._feedback import router as feedback_router
from community._giphy import router as giphy_router
from community._login_link import router as login_link_router
from community._version import router as version_router
from community.attendance.csv_import import router as attendance_import_router
from community.attendance.mark import router as attendance_mark_router
from community.attendance.report import router as attendance_report_router
from community.cohosts.invites import router as event_cohost_invites_router
from community.content.docs import router as docs_router
from community.content.documents import router as docs_documents_router
from community.content.guidelines import router as guidelines_router
from community.content.home import router as home_router
from community.content.pages import router as pages_router
from community.dev_tools.api import router as dev_tools_router
from community.event_feedback.host import router as event_feedback_host_router
from community.event_feedback.public import router as event_feedback_public_router
from community.events.blasts import router as event_blasts_router
from community.events.calendar import router as calendar_router
from community.events.comments import router as event_comments_router
from community.events.crud import router as events_router
from community.events.description_templates import (
    router as event_description_templates_router,
)
from community.events.flags import router as event_flags_router
from community.events.geocode import router as geocode_router

# Re-export symbols imported directly in tests
from community.events.helpers import (  # noqa: F401
    _build_guest_list,
    _find_my_rsvp,
    is_cohost,
)
from community.events.host_actions import router as event_host_actions_router
from community.events.invitations import router as event_invitations_router
from community.events.official_defaults import router as official_event_defaults_router
from community.events.photos import router as event_actions_router
from community.events.report import router as event_report_router
from community.events.schemas import EventPatchIn  # noqa: F401
from community.events.tags import router as event_tags_router
from community.join_requests.form import router as join_form_router
from community.join_requests.manage import router as join_requests_router
from community.join_requests.resend import router as join_request_resend_router
from community.join_requests.submit import router as join_request_submit_router
from community.join_requests.unreject import router as join_request_unreject_router
from community.message_templates.member_promotion_email import (
    router as member_promotion_email_router,
)
from community.message_templates.member_promotion_message import (
    router as member_promotion_message_router,
)
from community.message_templates.rejection_email import router as rejection_email_router
from community.message_templates.tentative_approval import (
    router as tentative_approval_message_router,
)
from community.message_templates.welcome import router as welcome_template_router
from community.message_templates.whatsapp_link import router as whatsapp_link_router
from community.polls.crud import router as polls_router
from community.polls.options import router as poll_options_router
from community.rsvps.host import router as event_host_rsvps_router
from community.rsvps.member import router as event_rsvps_router
from community.rsvps.public_manage import router as public_rsvp_manage_router
from community.rsvps.public_resend import router as public_rsvp_resend_router
from community.rsvps.public_submit import router as public_rsvp_submit_router
from community.rsvps.questions import router as event_rsvp_questions_router
from community.rsvps.waitlist_order import router as event_waitlist_order_router
from community.speech.template import router as speech_template_router
from community.surveys.crud import router as surveys_router
from community.surveys.public import router as surveys_public_router
from community.surveys.reports import router as survey_reports_router
from community.surveys.responses import router as surveys_responses_router

router = Router()
router.add_router("", guidelines_router)
router.add_router("", home_router)
router.add_router("", pages_router)
router.add_router("", join_form_router)
router.add_router("", join_requests_router)
router.add_router("", join_request_submit_router)
router.add_router("", join_request_resend_router)
router.add_router("", join_request_unreject_router)
router.add_router("", login_link_router)
router.add_router("", feedback_router)
# Mount before events_router so literal /events/attendance-* routes resolve before its /events/{event_id}/ param route.
router.add_router("", attendance_report_router)
router.add_router("", attendance_import_router)
router.add_router("", attendance_mark_router)
router.add_router("", event_feedback_host_router)
router.add_router("", events_router)
router.add_router("", event_tags_router)
router.add_router("", event_description_templates_router)
router.add_router("", official_event_defaults_router)
router.add_router("", event_rsvps_router)
router.add_router("", event_rsvp_questions_router)
router.add_router("", event_host_actions_router)
router.add_router("", event_host_rsvps_router)
router.add_router("", event_waitlist_order_router)
router.add_router("", event_report_router)
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
router.add_router("", event_feedback_public_router)
router.add_router("", calendar_router)
router.add_router("", welcome_template_router)
router.add_router("", tentative_approval_message_router)
router.add_router("", member_promotion_message_router)
router.add_router("", member_promotion_email_router)
router.add_router("", rejection_email_router)
router.add_router("", whatsapp_link_router)
router.add_router("", speech_template_router)
router.add_router("", polls_router)
router.add_router("", poll_options_router)
router.add_router("", event_comments_router)
router.add_router("", surveys_router)
router.add_router("", surveys_public_router)
router.add_router("", survey_reports_router)
router.add_router("", surveys_responses_router)
router.add_router("", docs_router)
router.add_router("", docs_documents_router)
router.add_router("", geocode_router)
router.add_router("", giphy_router)
router.add_router("", version_router)
router.add_router("", dev_tools_router)
