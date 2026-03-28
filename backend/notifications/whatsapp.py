import json
import logging
import urllib.error
import urllib.request
from urllib.parse import urljoin

from django.conf import settings

logger = logging.getLogger("pda.notifications")


def send_to_group(message: str) -> bool:
    """POST a message to the WhatsApp group via the bot microservice.

    Fails silently — returns False on any error so callers don't need to handle exceptions.
    """
    bot_url = getattr(settings, "WHATSAPP_BOT_URL", "")
    bot_secret = getattr(settings, "WHATSAPP_BOT_SECRET", "")
    group_id = getattr(settings, "WHATSAPP_GROUP_ID", "")

    if not bot_url or not group_id:
        logger.debug("WhatsApp not configured — skipping notification")
        return False

    payload = json.dumps({"groupId": group_id, "message": message}).encode()
    req = urllib.request.Request(
        urljoin(bot_url + "/", "send"),
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Bot-Secret": bot_secret,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status >= 400:
                logger.warning("WhatsApp bot returned HTTP %s", resp.status)
                return False
        return True
    except (urllib.error.URLError, OSError) as exc:
        logger.warning("WhatsApp send failed: %s", exc)
        return False
