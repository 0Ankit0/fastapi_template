from fastapi import APIRouter

router = APIRouter(
    prefix="/iam",
    tags=["iam"],
    responses={404: {"description": "Not found"}},
)

@router.get("/users")
def read_users():
    return [{"username": "user1"}, {"username": "user2"}]