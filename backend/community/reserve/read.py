from ninja import Router
from ninja.responses import Status

from community.models import ReserveEntry
from community.reserve.schemas import ReserveOut, entry_out

router = Router()


@router.get("/reserve/", response={200: ReserveOut}, auth=None)
def get_reserve(request):
    entries = list(ReserveEntry.objects.in_display_order())
    updated_at = max((e.updated_at for e in entries), default=None)
    return Status(200, ReserveOut(entries=[entry_out(e) for e in entries], updated_at=updated_at))
