#!/usr/bin/env python3
"""Seed script for development data."""
from __future__ import annotations

import asyncio
import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.core.security import hash_password
from app.models import Base, Couple, CoupleStatus, User, UserRole, UserWallet

settings = get_settings()


async def seed_data() -> None:
    """Create sample data for development."""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        # Create sample couple
        couple = Couple(
            id=uuid.uuid4(),
            couple_name="Demo Couple",
            anniversary_date=date(2023, 2, 14),
            status=CoupleStatus.ACTIVE,
        )
        session.add(couple)

        # Create sample users
        user_a = User(
            id=uuid.uuid4(),
            couple_id=couple.id,
            email="demo_a@example.com",
            password_hash=hash_password("password123"),
            display_name="Alice",
            email_verified=True,
            role=UserRole.PARTNER_A,
        )
        user_b = User(
            id=uuid.uuid4(),
            couple_id=couple.id,
            email="demo_b@example.com",
            password_hash=hash_password("password123"),
            display_name="Bob",
            email_verified=True,
            role=UserRole.PARTNER_B,
        )
        session.add(user_a)
        session.add(user_b)

        # Create wallets
        wallet_a = UserWallet(user_id=user_a.id, balance=100)
        wallet_b = UserWallet(user_id=user_b.id, balance=50)
        session.add(wallet_a)
        session.add(wallet_b)

        await session.commit()

        print("Seed data created successfully!")
        print(f"  Couple: {couple.couple_name} (ID: {couple.id})")
        print(f"  User A: {user_a.email} / password123")
        print(f"  User B: {user_b.email} / password123")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_data())
