from datetime import datetime as dt_datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic_classes import *
from sql_alchemy import *
from database import get_db
from bal_stdlib import *

router = APIRouter()

############################################
#   Resolution Method Endpoints
############################################


def _load_resolution(resolution_id: int, database: Session) -> Resolution:
    """Load one Resolution or answer 404 - shared by the three status methods."""
    resolution = database.query(Resolution).filter(Resolution.id == resolution_id).first()
    if resolution is None:
        raise HTTPException(status_code=404, detail="Resolution not found")
    return resolution


def _resolution_response(resolution: Resolution, database: Session) -> dict:
    """Serialize a Resolution the same way GET /resolution/{id}/ does."""
    subGoals_ids = [x[0] for x in database.query(SubGoal.id).filter(SubGoal.parentResolution_id == resolution.id).all()]
    progressEntries_ids = [x[0] for x in database.query(ProgressEntry.id).filter(ProgressEntry.resolution_id == resolution.id).all()]
    return {"resolution": resolution, "subGoals_ids": subGoals_ids, "progressEntries_ids": progressEntries_ids}


@router.post("/resolution/{resolution_id}/methods/activate/", response_model=None, tags=["Resolution Methods"])
async def execute_resolution_activate(
    resolution_id: int,  # the Resolution that activate runs on
    params: dict = Body(default=None, embed=True),
    database: Session = Depends(get_db)
):
    """Activate a resolution.

    Implements the modeled ``Resolution.activate()``. Takes no parameters: an
    empty request body succeeds.

    Side effects (persisted with a commit):
    - ``Resolution.status`` becomes ``ACTIVE``;
    - ``Resolution.updatedAt`` is set to now.

    Responses:
    - 200 with the updated resolution (``{"resolution": ..., ...ids}``);
    - 404 when the resolution does not exist;
    - 409 when the resolution is already ``ACTIVE`` (activating it again
      would change nothing).
    """
    resolution = _load_resolution(resolution_id, database)
    if resolution.status == ResolutionStatus.ACTIVE:
        raise HTTPException(
            status_code=409,
            detail=f"Resolution {resolution_id} is already ACTIVE; it cannot be activated again",
        )
    resolution.activate()
    database.commit()
    database.refresh(resolution)
    return _resolution_response(resolution, database)


@router.post("/resolution/{resolution_id}/methods/complete/", response_model=None, tags=["Resolution Methods"])
async def execute_resolution_complete(
    resolution_id: int,  # the Resolution that complete runs on
    params: dict = Body(default=None, embed=True),
    database: Session = Depends(get_db)
):
    """Mark a resolution as completed.

    Implements the modeled ``Resolution.complete()``. Takes no parameters: an
    empty request body succeeds.

    Side effects (persisted with a commit):
    - ``Resolution.status`` becomes ``COMPLETED``;
    - ``Resolution.updatedAt`` is set to now.

    Responses:
    - 200 with the updated resolution (``{"resolution": ..., ...ids}``);
    - 404 when the resolution does not exist;
    - 409 when the resolution is already ``COMPLETED`` (completing it again
      would change nothing).
    """
    resolution = _load_resolution(resolution_id, database)
    if resolution.status == ResolutionStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail=f"Resolution {resolution_id} is already COMPLETED; it cannot be completed again",
        )
    resolution.complete()
    database.commit()
    database.refresh(resolution)
    return _resolution_response(resolution, database)


@router.post("/resolution/{resolution_id}/methods/pause/", response_model=None, tags=["Resolution Methods"])
async def execute_resolution_pause(
    resolution_id: int,  # the Resolution that pause runs on
    params: dict = Body(default=None, embed=True),
    database: Session = Depends(get_db)
):
    """Put a resolution on hold.

    Implements the modeled ``Resolution.pause()``. Takes no parameters: an
    empty request body succeeds.

    Side effects (persisted with a commit):
    - ``Resolution.status`` becomes ``PAUSED``;
    - ``Resolution.updatedAt`` is set to now.

    Responses:
    - 200 with the updated resolution (``{"resolution": ..., ...ids}``);
    - 404 when the resolution does not exist;
    - 409 when the resolution is already ``PAUSED`` (pausing it again
      would change nothing).
    """
    resolution = _load_resolution(resolution_id, database)
    if resolution.status == ResolutionStatus.PAUSED:
        raise HTTPException(
            status_code=409,
            detail=f"Resolution {resolution_id} is already PAUSED; it cannot be paused again",
        )
    resolution.pause()
    database.commit()
    database.refresh(resolution)
    return _resolution_response(resolution, database)
