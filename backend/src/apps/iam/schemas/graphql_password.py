import strawberry

@strawberry.input
class PasswordResetRequestInput:
    email: str

@strawberry.input
class PasswordResetConfirmInput:
    token: str
    new_password: str

@strawberry.input
class ChangePasswordInput:
    current_password: str
    new_password: str
