from ninja import Schema


class GoogleAuthRequest(Schema):
    token: str


class UserResponse(Schema):
    user_id: int
    email: str
    name: str
    picture: str


class AuthResponse(Schema):
    token: str
    user: UserResponse
