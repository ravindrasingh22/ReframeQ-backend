from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin_permissions
from app.db.session import get_db
from app.schemas.admin import (
    FirstReframeConfigResponse,
    FirstReframeConfigUpdateRequest,
    FirstReframePreviewRequest,
    FirstReframePreviewResponse,
)
from app.schemas.onboarding_ai import OnboardingAIRequest
from app.services.onboarding_ai_config_service import get_first_reframe_config, save_first_reframe_config
from app.services.onboarding_ai_service import detect_pattern_from_text, generate_onboarding_ai_result

router = APIRouter()


@router.get('/onboarding/first-reframe', response_model=FirstReframeConfigResponse)
def get_onboarding_first_reframe_config(
    current_user: Annotated[dict, Depends(require_admin_permissions('ai.read'))],
    db: Annotated[Session, Depends(get_db)],
) -> FirstReframeConfigResponse:
    _ = current_user
    return FirstReframeConfigResponse(**get_first_reframe_config(db))


@router.put('/onboarding/first-reframe', response_model=FirstReframeConfigResponse)
def update_onboarding_first_reframe_config(
    payload: FirstReframeConfigUpdateRequest,
    current_user: Annotated[dict, Depends(require_admin_permissions('ai.write'))],
    db: Annotated[Session, Depends(get_db)],
) -> FirstReframeConfigResponse:
    _ = current_user
    saved = save_first_reframe_config(db, payload.model_dump())
    return FirstReframeConfigResponse(**saved)


@router.post('/onboarding/first-reframe/preview', response_model=FirstReframePreviewResponse)
def preview_onboarding_first_reframe(
    payload: FirstReframePreviewRequest,
    current_user: Annotated[dict, Depends(require_admin_permissions('ai.read'))],
    db: Annotated[Session, Depends(get_db)],
) -> FirstReframePreviewResponse:
    _ = current_user
    config = get_first_reframe_config(db)
    request = OnboardingAIRequest.model_validate(
        {
            'step': 'first_reframe',
            'context': {
                'entry_context': {
                    'language': payload.language,
                    'country': payload.country,
                    'app_source': 'admin_preview',
                    'signup_path': 'direct_signup',
                    'is_new_user': True,
                    'is_resuming': False,
                },
                'account_context': {
                    'account_mode': payload.account_mode,
                    'user_type': payload.user_type,
                },
                'goal_context': {
                    'goal': payload.goal,
                    'secondary_goals': payload.secondary_goals,
                },
                'state_context': {
                    'clarity_score': payload.clarity_score,
                    'control_score': payload.control_score,
                    'mental_noise_score': payload.mental_noise_score,
                    'readiness_score': payload.readiness_score,
                },
                'style_context': {
                    'coach_style': payload.coach_style,
                },
                'input_context': {
                    'user_message': payload.user_thought,
                    'detected_pattern': detect_pattern_from_text(payload.user_thought),
                },
                'safety_context': {
                    'scan_status': 'allow',
                    'policy_code': 'ok',
                    'blocked_topics': [],
                    'needs_handoff': False,
                },
            },
        }
    )
    result, model = generate_onboarding_ai_result(request, config=config)
    return FirstReframePreviewResponse(model=model, result=result.model_dump())
