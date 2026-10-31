"""
SatyaSwar - User Profile REST Routes
Member 2: Backend, Infrastructure, Database and Security

Implements user profile retrieval with auto-provisioning, profile updating, and
account deletion requests under /api/v1/users.
"""

from fastapi import APIRouter, Depends, status

from app.dependencies.auth import AuthUser, get_current_user
from app.models.schemas import UserProfile, UserUpdate
from app.repositories import users as users_repo

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: AuthUser = Depends(get_current_user),
) -> UserProfile:
    """
    Retrieves the authenticated user's profile.
    Automatically provisions the user profile document in Firestore on first call.
    """
    return users_repo.get_or_create_user(
        uid=current_user.uid,
        email=current_user.email or "",
        name=current_user.name or "",
    )


@router.patch("/me", response_model=UserProfile)
async def update_current_user_profile(
    update_data: UserUpdate,
    current_user: AuthUser = Depends(get_current_user),
) -> UserProfile:
    """
    Updates whitelisted profile fields (name, phone) for the authenticated user.
    """
    return users_repo.update_user_profile(
        uid=current_user.uid,
        update_data=update_data,
    )


@router.delete("/me", status_code=status.HTTP_202_ACCEPTED)
async def delete_current_user_account(
    current_user: AuthUser = Depends(get_current_user),
) -> dict[str, str]:
    """
    Initiates account deletion.
    Transitions account status to PENDING_DELETION and schedules complete cascading cleanup.
    """
    users_repo.mark_account_pending_deletion(current_user.uid)
    # Perform immediate cascading cleanup for MVP
    users_repo.execute_complete_account_deletion(current_user.uid)
    return {
        "status": "pending_deletion",
        "message": "Account and all associated records have been marked and scheduled for deletion",
    }

