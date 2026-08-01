import logging

logging.getLogger("asyncio").setLevel(logging.WARNING)

from community.models import *  # noqa: E402,F401,F403
from users.models import *  # noqa: E402,F401,F403
