from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    model_validator,
)


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokensPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserRegistration(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    password_repeat: str = Field(..., min_length=8, max_length=128)

    @model_validator(mode="after")
    def check_passwords_match(self):
        if self.password != self.password_repeat:
            raise ValueError("Passwords do not match")
        return self
