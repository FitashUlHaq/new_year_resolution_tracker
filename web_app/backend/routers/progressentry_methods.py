from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic_classes import *
from sql_alchemy import *
from database import get_db
from bal_stdlib import *

router = APIRouter()

############################################
#   ProgressEntry Method Endpoints
############################################


@router.post("/progressentry/{progressentry_id}/methods/edit/", response_model=None, tags=["ProgressEntry Methods"])
async def execute_progressentry_edit(
    progressentry_id: int,  # the ProgressEntry that edit runs on
    params: dict = Body(default=None, embed=True),
    database: Session = Depends(get_db)
):
    """Edit the notes and amount recorded on a progress entry.

    Implements the modeled ``ProgressEntry.edit(notes: str, amount: float)``.

    Parameters (in the JSON body, wrapped in ``params``):
    - notes (str): the new notes; passing ``null`` clears them;
    - amount (float): the new amount; passing ``null`` clears it.

    Only the keys present in ``params`` are written, so a caller may edit the
    notes without touching the amount. Calling the endpoint with neither key
    is refused: it would change nothing.

    Side effects (persisted with a commit):
    - ``ProgressEntry.notes`` and/or ``ProgressEntry.amount`` are updated.

    Responses:
    - 200 with the updated entry (``{"progressentry": ...}``);
    - 404 when the entry does not exist;
    - 422 when neither ``notes`` nor ``amount`` is present in the body.
    """
    body = params or {}
    if "notes" not in body and "amount" not in body:
        raise HTTPException(
            status_code=422,
            detail="Provide at least one of 'notes' or 'amount' to edit the progress entry",
        )
    entry = database.query(ProgressEntry).filter(ProgressEntry.id == progressentry_id).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="ProgressEntry not found")
    if "notes" in body:
        notes = body["notes"]
        if notes is not None and not isinstance(notes, str):
            raise HTTPException(status_code=422, detail="notes must be a string or null")
        entry.edit(notes=notes)
    if "amount" in body:
        amount = body["amount"]
        if amount is not None and not isinstance(amount, (int, float)):
            raise HTTPException(status_code=422, detail="amount must be a number or null")
        entry.edit(amount=float(amount) if amount is not None else None)
    database.commit()
    database.refresh(entry)
    return {"progressentry": entry}


@router.post("/progressentry/{progressentry_id}/methods/remove/", response_model=None, tags=["ProgressEntry Methods"])
async def execute_progressentry_remove(
    progressentry_id: int,  # the ProgressEntry that remove runs on
    params: dict = Body(default=None, embed=True),
    database: Session = Depends(get_db)
):
    """Delete a progress entry.

    Implements the modeled ``ProgressEntry.remove()``. Takes no parameters:
    an empty request body succeeds.

    Side effects (persisted with a commit):
    - the ``ProgressEntry`` row is deleted from the database.

    Responses:
    - 200 with a confirmation (``{"removed": true, "progressentry_id": ...}``);
    - 404 when the entry does not exist (or was already removed).
    """
    entry = database.query(ProgressEntry).filter(ProgressEntry.id == progressentry_id).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="ProgressEntry not found")
    removed = {
        "id": entry.id,
        "date": entry.date,
        "notes": entry.notes,
        "amount": entry.amount,
        "author_id": entry.author_id,
        "habit_id": entry.habit_id,
        "resolution_id": entry.resolution_id,
    }
    entry.remove()
    database.commit()
    return {"removed": True, "progressentry_id": progressentry_id, "progressentry": removed}
