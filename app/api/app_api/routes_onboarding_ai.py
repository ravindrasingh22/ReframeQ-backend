from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.onboarding_ai import OnboardingAIRequest, OnboardingAIResponse, OnboardingAISafetyDecision
from app.services.onboarding_ai_config_service import DEFAULT_FIRST_REFRAME_CONFIG, get_first_reframe_config
from app.services.onboarding_ai_service import generate_onboarding_ai_result

router = APIRouter()


@router.post('/generate', response_model=OnboardingAIResponse)
def generate_onboarding_ai(
    payload: OnboardingAIRequest,
    db: Annotated[Session, Depends(get_db)],
) -> OnboardingAIResponse:
    config = get_first_reframe_config(db) if payload.step == 'first_reframe' else None
    result, model = generate_onboarding_ai_result(payload, config=config)
    return OnboardingAIResponse(
        step=payload.step,
        result=result,
        model=model,
        safety_decision=OnboardingAISafetyDecision(
            scan_status=payload.context.safety_context.scan_status,
            policy_code=payload.context.safety_context.policy_code,
        ),
    )
