from sqlmodel import select, update
from app.db.session import AsyncSession
from app.models.tenant import TenantMembership

class TenantService:
    @staticmethod
    async def associate_invitations(db: AsyncSession, email: str, user_id: int):
        """
        Associates any pending invitations for the given email with the new user.
        """
        # Find memberships with this email that are not accepted (pending)
        # And presumably user_id is None, but the constraint says unique user+tenant... 
        # If invitation exists, user is likely None.
        
        # We just update user_id on them.
        stmt = (
            update(TenantMembership)
            .where(
                TenantMembership.invitee_email_address == email,
                TenantMembership.is_accepted == False
            )
            .values(user_id=user_id)
        )
        await db.execute(stmt)
        await db.commit()
