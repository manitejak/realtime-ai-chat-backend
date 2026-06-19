from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_refresh_token, \
decode_refresh_token, hash_password, verify_password, hash_refresh_token, \
verify_refresh_token_hash
from app.db.repositories.refresh_tokens import RefreshTokenRepository
from app.db.repositories.users import UserRepository
from app.schemas.auth import TokenPairResponse


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    async def sign_up(self, email: str, password: str) -> TokenPairResponse:
        existing = await self.users.get_by_email(email)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Email already registered')
        user = await self.users.create(email=email, password_hash=hash_password(password))
        access_token, access_expires_at = create_access_token(user.id)
        refresh_token, jti, refresh_expires_at = create_refresh_token(user.id)
        await self.refresh_tokens.create(user.id, jti, hash_refresh_token(refresh_token), refresh_expires_at)
        await self.session.commit()
        return TokenPairResponse(access_token=access_token, refresh_token=refresh_token, expires_at=access_expires_at)

    async def login(self, email: str, password: str) -> TokenPairResponse:
        user = await self.users.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials')
        access_token, access_expires_at = create_access_token(user.id)
        refresh_token, jti, refresh_expires_at = create_refresh_token(user.id)
        await self.refresh_tokens.create(user.id, jti, hash_refresh_token(refresh_token), refresh_expires_at)
        await self.session.commit()
        return TokenPairResponse(access_token=access_token, refresh_token=refresh_token, expires_at=access_expires_at)

    async def refresh(self, refresh_token: str) -> TokenPairResponse:
        payload = decode_refresh_token(refresh_token)
        stored = await self.refresh_tokens.get_by_jti(payload['jti'])
        if not stored or stored.is_revoked or not verify_refresh_token_hash(refresh_token, stored.token_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid refresh token')
        await self.refresh_tokens.revoke(stored)
        access_token, access_expires_at = create_access_token(payload['sub'])
        next_refresh_token, jti, refresh_expires_at = create_refresh_token(payload['sub'])
        await self.refresh_tokens.create(payload['sub'], jti, hash_refresh_token(next_refresh_token), refresh_expires_at)
        await self.session.commit()
        return TokenPairResponse(access_token=access_token, refresh_token=next_refresh_token, expires_at=access_expires_at)