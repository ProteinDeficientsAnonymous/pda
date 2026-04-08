"""Community API — thin composer that mounts all domain sub-routers."""

from ninja import Router

from community._calendar import router as calendar_router
from community._docs import router as docs_router

# Re-export symbols imported directly in tests
from community._event_helpers import (  # noqa: F401
    _build_guest_list,
    _can_see_phones,
    _find_my_rsvp,
)
from community._event_schemas import EventPatchIn  # noqa: F401
from community._events import router as events_router
from community._feedback import router as feedback_router
from community._guidelines import router as guidelines_router
from community._home import router as home_router
from community._join_form import router as join_form_router
from community._join_requests import router as join_requests_router
from community._pages import router as pages_router
from community._polls import router as polls_router
from community._surveys import router as surveys_router
from community._surveys_public import router as surveys_public_router
from community._whatsapp import router as whatsapp_router

router = Router()
router.add_router("", guidelines_router)
router.add_router("", home_router)
router.add_router("", pages_router)
router.add_router("", join_form_router)
router.add_router("", join_requests_router)
router.add_router("", feedback_router)
router.add_router("", events_router)
router.add_router("", calendar_router)
router.add_router("", whatsapp_router)
router.add_router("", polls_router)
router.add_router("", surveys_router)
router.add_router("", surveys_public_router)
router.add_router("", docs_router)
