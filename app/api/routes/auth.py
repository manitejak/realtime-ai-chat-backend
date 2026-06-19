from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.auth import LoginRequest, RefreshRequest, SignUpRequest, TokenPairResponse
from app.services.auth import AuthService

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/signup', response_model=TokenPairResponse, status_code=201)
async def signup(payload: SignUpRequest, session: AsyncSession = Depends(get_db_session)) -> TokenPairResponse:
    return await AuthService(session).sign_up(payload.email, payload.password)


@router.post('/login', response_model=TokenPairResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_db_session)) -> TokenPairResponse:
    return await AuthService(session).login(payload.email, payload.password)


@router.post('/refresh', response_model=TokenPairResponse)
async def refresh(payload: RefreshRequest, session: AsyncSession = Depends(get_db_session)) -> TokenPairResponse:
    return await AuthService(session).refresh(payload.refresh_token)