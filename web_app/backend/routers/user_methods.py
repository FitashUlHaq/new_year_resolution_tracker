from datetime import datetime as dt_datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic_classes import *
from sql_alchemy import *
from database import get_db
from bal_stdlib import *

router = APIRouter()

############################################
#   User Method Endpoints
############################################


@router.post("/user/{user_id}/methods/addProgressEntry/", response_model=None, tags=["User Methods"])
async def execute_user_addProgressEntry(
    user_id: int,  # the User that addProgressEntry runs on
    params: dict = Body(default=None, embed=True),
    database: Session = Depends(get_db)
):
    """Record a progress entry for the user against one of their resolutions.

    Implements the modeled ``User.addProgressEntry(resolution, entry)``.

    Parameters (in the JSON body, wrapped in ``params``):
    - resolution (int, required): id of the Resolution the progress is
      logged against;
    - entry (object, required): the progress entry fields ``date``
      (datetime, required), ``notes`` (str, optional), ``amount``
      (float, optional) and ``habit`` (int, optional, links the entry to a
      Habit of this user).

    Side effects (persisted with a commit):
    - a new ``ProgressEntry`` row is created with ``author_id`` = this user;
    - ``resolution_id`` / ``habit_id`` are set from the given references.

    Responses:
    - 200 with the created entry (``{"progressentry": ..., "user_id": ...,
      "resolution_id": ...}``);
    - 404 when the user or the resolution does not exist;
    - 400 when a referenced habit does not exist or does not belong to this
      user, or when the entry payload is malformed;
    - 422 when ``resolution`` or ``entry`` is missing.
    """
    body = params or {}
    user = database.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    resolution_ref = body.get("resolution")
    entry_data = body.get("entry")
    if resolution_ref is None or entry_data is None or not isinstance(entry_data, dict):
        raise HTTPException(
            status_code=422,
            detail="Provide 'resolution' (the Resolution id) and 'entry' (the progress entry fields)",
        )
    resolution_id = resolution_ref.get("id") if isinstance(resolution_ref, dict) else resolution_ref
    if not isinstance(resolution_id, int):
        raise HTTPException(status_code=422, detail="resolution must be the id of an existing Resolution")

    resolution = database.query(Resolution).filter(Resolution.id == resolution_id).first()
    if resolution is None:
        raise HTTPException(status_code=404, detail=f"Resolution {resolution_id} not found")
    if resolution.owner_id != user.id:
        raise HTTPException(
            status_code=400,
            detail=f"Resolution {resolution_id} does not belong to user {user_id}: log progress on your own resolutions",
        )

    raw_date = entry_data.get("date")
    if isinstance(raw_date, str):
        try:
            entry_date = dt_datetime.fromisoformat(raw_date.replace("Z", ""))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"entry.date must be an ISO-8601 datetime, got: {raw_date!r}")
    elif isinstance(raw_date, dt_datetime):
        entry_date = raw_date
    else:
        raise HTTPException(status_code=422, detail="entry.date is required and must be an ISO-8601 datetime")

    habit_id = entry_data.get("habit")
    if habit_id is not None:
        habit = database.query(Habit).filter(Habit.id == habit_id).first()
        if habit is None:
            raise HTTPException(status_code=400, detail=f"Habit {habit_id} not found")
        if habit.habitUser_id != user.id:
            raise HTTPException(status_code=400, detail=f"Habit {habit_id} does not belong to user {user_id}")

    notes = entry_data.get("notes")
    if notes is not None and not isinstance(notes, str):
        raise HTTPException(status_code=422, detail="entry.notes must be a string or null")
    amount = entry_data.get("amount")
    if amount is not None and not isinstance(amount, (int, float)):
        raise HTTPException(status_code=422, detail="entry.amount must be a number or null")

    entry = ProgressEntry(
        date=entry_date,
        notes=notes,
        amount=float(amount) if amount is not None else None,
        author_id=user.id,
        habit_id=habit_id,
        resolution_id=resolution.id,
    )
    user.addProgressEntry(resolution, entry)
    database.add(entry)
    database.commit()
    database.refresh(entry)
    return {"progressentry": entry, "user_id": user.id, "resolution_id": resolution.id}


@router.post("/user/{user_id}/methods/createResolution/", response_model=None, tags=["User Methods"])
async def execute_user_createResolution(
    user_id: int,  # the User that createResolution runs on
    params: dict = Body(default=None, embed=True),
    database: Session = Depends(get_db)
):
    """Create a new resolution owned by the user, starting as PLANNED.

    Implements the modeled ``User.createResolution(title, description)``.

    Parameters (in the JSON body, wrapped in ``params``):
    - title (str, required): the resolution's title;
    - description (str, optional): what the resolution is about.

    Side effects (persisted with a commit):
    - a new ``Resolution`` row is created with ``owner_id`` = this user and
      ``status`` = ``PLANNED`` (its lifecycle then runs through the
      activate/complete/pause methods).

    Responses:
    - 200 with the created resolution (``{"resolution": ..., ...ids}``);
    - 404 when the user does not exist;
    - 422 when ``title`` is missing or not a string.
    """
    body = params or {}
    user = database.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    title = body.get("title")
    if not title or not isinstance(title, str):
        raise HTTPException(status_code=422, detail="title is required and must be a string")
    description = body.get("description")
    if description is not None and not isinstance(description, str):
        raise HTTPException(status_code=422, detail="description must be a string or null")

    resolution = user.createResolution(title=title, description=description)
    database.add(resolution)
    database.commit()
    database.refresh(resolution)
    return {"resolution": resolution, "subGoals_ids": [], "progressEntries_ids": []}
