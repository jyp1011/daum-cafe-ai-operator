from fastapi import APIRouter
from app.api.v1 import auth, cafes, quiz, moderation

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(cafes.router)
router.include_router(quiz.router)
router.include_router(moderation.router)
