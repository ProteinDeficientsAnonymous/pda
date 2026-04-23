"""Build/version info endpoint — exposes the deployed commit SHA for traceability."""

import os

from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel

router = Router()


class VersionOut(BaseModel):
    commit_sha: str
    commit_sha_short: str
    environment: str


@router.get("/version/", response={200: VersionOut}, auth=None)
def get_version(request):
    sha = os.environ.get("RAILWAY_GIT_COMMIT_SHA") or "dev"
    environment = os.environ.get("RAILWAY_ENVIRONMENT_NAME") or "local"
    return Status(
        200,
        VersionOut(
            commit_sha=sha,
            commit_sha_short=sha[:7],
            environment=environment,
        ),
    )
