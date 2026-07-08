from .login_attempt import LoginAttemptRepository
from .profile import UserProfileRepository
from .token_tracking import TokenTrackingRepository
from .used_token import UsedTokenRepository
from .user import UserRepository

class IAMRepository(
    LoginAttemptRepository,
    UserProfileRepository,
    TokenTrackingRepository,
    UsedTokenRepository,
    UserRepository
):
    
    def commit(self, db):
        """Commit the current transaction."""
        return db.commit()
    
iam_repository = IAMRepository()