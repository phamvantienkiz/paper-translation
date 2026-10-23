from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "paper-translation-backend",
        "version": "0.1.0",
    }
