from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from mcp_gateway.models import OAuthAuthRequest, OAuthClient

# keeps "this request expired" (instead of "doesn't exist") showing for a while after expiry
_EXPIRED_REQUEST_GRACE = timedelta(days=1)
_UNUSED_CLIENT_AGE = timedelta(days=7)


class Command(BaseCommand):
    help = "Delete expired MCP sign-in requests and client registrations that never got a grant"

    def handle(self, *args, **options):
        now = timezone.now()
        requests, _ = OAuthAuthRequest.objects.filter(
            expires_at__lt=now - _EXPIRED_REQUEST_GRACE
        ).delete()
        cutoff = now - _UNUSED_CLIENT_AGE
        _, per_model = (
            OAuthClient.objects.filter(created_at__lt=cutoff, grants__isnull=True)
            .exclude(auth_requests__created_at__gte=cutoff)
            .delete()
        )
        clients = per_model.get(OAuthClient._meta.label, 0)
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {requests} expired auth requests and {clients} unused clients"
            )
        )
