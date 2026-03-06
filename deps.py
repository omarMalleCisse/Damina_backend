"""
Dépendances FastAPI génériques pour l'auth et les permissions.
"""
from typing import Optional, Callable

from fastapi import Depends, HTTPException, status

import auth
import models


def require_admin(current_user: models.User = Depends(auth.get_current_user)) -> models.User:
    """Dépendance : exige un utilisateur connecté et admin. Sinon 403."""
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs",
        )
    return current_user


def ensure_admin(current_user: models.User) -> None:
    """Lève 403 si l'utilisateur n'est pas admin. À appeler dans une route."""
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs",
        )


def can_access_resource(
    current_user: models.User,
    resource_user_id: Optional[int],
) -> bool:
    """
    Retourne True si l'utilisateur peut accéder à la ressource.
    - Admin : toujours True
    - Sinon : True seulement si resource_user_id == current_user.id (ou ressource publique si None).
    """
    if getattr(current_user, "is_admin", False):
        return True
    if resource_user_id is None:
        return True  # ressource sans owner
    return resource_user_id == current_user.id


def require_access(
    current_user: models.User,
    resource_user_id: Optional[int],
    message: str = "Vous n'avez pas accès à cette ressource",
) -> None:
    """Lève 403 si can_access_resource est False."""
    if not can_access_resource(current_user, resource_user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)
