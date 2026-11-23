from datetime import datetime as dt_datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic_classes import *
from sql_alchemy import *
from database import get_db
from bal_stdlib import *

router = APIRouter()

############################################
#   Habit Method Endpoints
############################################


def _parse_done_at(raw) -> dt_datetime:
    """Convert the ``doneAt`` request value into a datetime.

    Accepts ISO-8601 strings (with or without a trailing ``Z``) and leaves
    real datetimes untouched. Anything else is a 422, because ``doneAt`` is
    a required parameter of ``Habit.markDone``.
    """
    if raw is None or raw == "":
        raise HTTPException(status_code=422, detail="doneAt is required: pass the moment the habit was done")
    if isinstance(raw, dt_datetime):
        return raw
    text = str(raw).strip()
    if text.endswith("Z"):
        text = text[:-1]
    try:
        return dt_datetime.fromisoformat(text)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"doneAt must be an ISO-8601 datetime, got: {raw!r}")


@router.post("/habit/{habit_id}/methods/markDone/", response_model=None, tags=["Habit Methods"])
async def execute_habit_markDone(
    habit_id: int,  # the Habit that markDone runs on
    params: dict = Body(default=None, embed=True),
    database: Session = Depends(get_db)
):
    """Mark the habit as done at a given moment and grow its streak.

    Implements the modeled ``Habit.markDone(doneAt: datetime)``.

    Parameters (in the JSON body, wrapped in ``params``):
    - doneAt (datetime, required): the moment the habit was done.

    Side effects (persisted with a commit):
    - ``Habit.lastDoneAt`` is set to ``doneAt``;
    - ``Habit.currentStreak`` is incremented by one.

    Responses:
    - 200 with the updated habit (``{"habit": ..., "progressEntries_ids": [...]}``);
    - 404 when the habit does not exist;
    - 409 when ``doneAt`` lies before the habit's current ``lastDoneAt``
      (a habit cannot have been done before the last time it was done);
    - 422 when ``doneAt`` is missing or not a datetime.
    """
    done_at = _parse_done_at((params or {}).get("doneAt"))
    habit = database.query(Habit).filter(Habit.id == habit_id).first()
    if habit is None:
        raise HTTPException(status_code=404, detail="Habit not found")
    if habit.lastDoneAt is not None and done_at < habit.lastDoneAt:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot mark habit {habit_id} done at {done_at.isoformat()}: "
                f"it was already done at {habit.lastDoneAt.isoformat()}"
            ),
        )
    habit.markDone(done_at)
    database.commit()
    database.refresh(habit)
    progressEntries_ids = [x[0] for x in database.query(ProgressEntry.id).filter(ProgressEntry.habit_id == habit.id).all()]
    return {"habit": habit, "progressEntries_ids": progressEntries_ids}


@router.post("/habit/{habit_id}/methods/resetStreak/", response_model=None, tags=["Habit Methods"])
async def execute_habit_resetStreak(
    habit_id: int,  # the Habit that resetStreak runs on
    params: dict = Body(default=None, embed=True),
    database: Session = Depends(get_db)
):
    """Reset the habit's streak to zero.

    Implements the modeled ``Habit.resetStreak()``. Takes no parameters: an
    empty request body succeeds.

    Side effects (persisted with a commit):
    - ``Habit.currentStreak`` is set to 0;
    - ``Habit.lastDoneAt`` is left untouched (history is not rewritten).

    Responses:
    - 200 with the updated habit (``{"habit": ..., "progressEntries_ids": [...]}``);
    - 404 when the habit does not exist.
    """
    habit = database.query(Habit).filter(Habit.id == habit_id).first()
    if habit is None:
        raise HTTPException(status_code=404, detail="Habit not found")
    habit.resetStreak()
    database.commit()
    database.refresh(habit)
    progressEntries_ids = [x[0] for x in database.query(ProgressEntry.id).filter(ProgressEntry.habit_id == habit.id).all()]
    return {"habit": habit, "progressEntries_ids": progressEntries_ids}
