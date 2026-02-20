from fastapi import APIRouter

from app.api.v1 import auth, health, posts

router = APIRouter()

router.include_router(health.router, tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(posts.router, prefix="/posts", tags=["posts"])
# Placeholder for future routes:
# router.include_router(couples.router, prefix="/couples", tags=["couples"])
# router.include_router(wallet.router, prefix="/wallet", tags=["wallet"])
# router.include_router(account.router, prefix="/account", tags=["account"])
