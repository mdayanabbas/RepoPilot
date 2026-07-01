from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api")


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(payload: LoginRequest) -> dict[str, str]:
    if payload.username != "demo@example.com" or payload.password != "secret":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": "demo-token", "token_type": "bearer"}
