from django.http import Http404, JsonResponse

from config.memory import ensure_tracemalloc, memory_profile_enabled, snapshot


def memory_snapshot_view(request):
    if not memory_profile_enabled():
        raise Http404
    ensure_tracemalloc()
    return JsonResponse(snapshot())
