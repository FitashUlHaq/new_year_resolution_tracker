from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic_classes import *
from sql_alchemy import *
from database import get_db
from bal_stdlib import *

router = APIRouter()

############################################
#   SubGoal Method Endpoints
############################################


@router.post("/subgoal/{subgoal_id}/methods/markComplete/", response_model=None, tags=["SubGoal Methods"])
async def execute_subgoal_markComplete(
    subgoal_id: int,  # the SubGoal that markComplete runs on
    params: dict = Body(default=None, embed=True),
    database: Session = Depends(get_db)
):
    """Mark a milestone (sub-goal) as complete.

    Implements the modeled ``SubGoal.markComplete()``. Takes no parameters:
    an empty request body succeeds.

    Side effects (persisted with a commit):
    - ``SubGoal.completed`` becomes ``True``;
    - the parent resolution is left unchanged (its status is managed by the
      resolution's own activate/complete/pause methods).

    Responses:
    - 200 with the updated sub-goal (``{"subgoal": ...}``);
    - 404 when the sub-goal does not exist;
    - 409 when the sub-goal is already completed (marking it complete again
      would change nothing).
    """
    subgoal = database.query(SubGoal).filter(SubGoal.id == subgoal_id).first()
    if subgoal is None:
        raise HTTPException(status_code=404, detail="SubGoal not found")
    if subgoal.completed:
        raise HTTPException(
            status_code=409,
            detail=f"SubGoal {subgoal_id} is already completed; it cannot be completed again",
        )
    subgoal.markComplete()
    database.commit()
    database.refresh(subgoal)
    return {"subgoal": subgoal}
