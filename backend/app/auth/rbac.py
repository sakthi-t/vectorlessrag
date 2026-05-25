from fastapi import Depends, HTTPException, status

from app.auth.tenant import TenantContext


def require_role(required_role: str):
    def dependency(ctx: TenantContext = Depends()):
        if required_role == "admin" and ctx.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        return ctx

    return dependency
