import httpx

from app.core.config import settings
from app.schemas.onboarding_ai import OnboardingAIRequest, OnboardingAIResult
from app.services.onboarding_ai_config_service import DEFAULT_FIRST_REFRAME_CONFIG


GOAL_HINTS = {
    'overthinking': 'evidence, alternative explanations, and one calmer next step',
    'friendships': 'social situations, assumptions, and one confidence-building action',
    'focus': 'short tasks, reduced overwhelm, and one 15-minute step',
    'parenting': 'calmer responses, separating behavior from identity, and one steady action',
    'confidence': 'self-talk, realistic evidence, and small brave actions',
}

PATTERN_LABELS = {
    'all_or_nothing': 'All-or-nothing thinking',
    'catastrophizing': 'Catastrophizing',
    'mind_reading': 'Mind reading',
    'labeling': 'Labeling',
    'should_statements': 'Should statements',
    'fortune_telling': 'Fortune telling',
    'emotional_reasoning': 'Emotional reasoning',
    'unknown': 'Thinking pattern',
}


def detect_pattern_from_text(text: str) -> str:
    normalized = (text or '').strip().lower()
    if not normalized:
        return 'unknown'
    if any(token in normalized for token in ['always', 'never', 'ruined', 'impossible', 'everything', 'nothing']):
        return 'all_or_nothing'
    if any(token in normalized for token in ['what if', 'disaster', 'fall apart', 'worst', 'never catch up', 'go wrong']):
        return 'catastrophizing'
    if any(token in normalized for token in ['they think', 'everyone thinks', 'judging me', 'must hate me', 'must be upset with me']):
        return 'mind_reading'
    if any(token in normalized for token in ['i am a failure', 'i am useless', 'i am stupid', 'bad parent', 'bad person']):
        return 'labeling'
    if any(token in normalized for token in ['should', 'should not', 'must', 'have to']):
        return 'should_statements'
    if any(token in normalized for token in ['i feel like', 'it feels like', 'because i feel']):
        return 'emotional_reasoning'
    return 'unknown'


def _language_name(language: str) -> str:
    return 'natural Hinglish in Roman script' if language.strip().lower() == 'hinglish' else 'simple English'


def _base_tone(style: str) -> str:
    return style.strip().lower() or 'gentle'


def _goal_hint(goal: str) -> str:
    return GOAL_HINTS.get(goal.strip().lower(), 'useful examples and one small next step')


def _pattern_label(pattern: str) -> str:
    return PATTERN_LABELS.get(pattern.strip().lower(), 'Thinking pattern')


def _clarity_message(request: OnboardingAIRequest) -> str:
    state = request.context.state_context
    style = _base_tone(request.context.style_context.coach_style)
    if (state.mental_noise_score or 0) >= 70:
        return f"You're carrying a lot of mental noise right now, so I'll keep this {style} and simple."
    if (state.clarity_score or 0) <= 35:
        return f"We can keep this {style} and structured so you do not have to figure everything out at once."
    if (state.readiness_score or 0) >= 70:
        return f"You seem ready to act, so I'll keep this {style} and focused on one useful next step."
    return f"I'll keep this {style} and steady so the first steps feel manageable."


def _tutorial_example(request: OnboardingAIRequest) -> OnboardingAIResult:
    goal = request.context.goal_context.goal.strip().lower()
    examples = {
        'friendships': (
            'A friend has not replied for hours.',
            'They must be upset with me.',
            'A slow reply can mean many things, not only rejection.',
        ),
        'focus': (
            'A task feels so big that you keep avoiding it.',
            'If I cannot do it perfectly, there is no point starting.',
            'A small imperfect start still counts and gives you more information.',
        ),
        'parenting': (
            'Your child ignores an instruction after a long day.',
            'I am failing as a parent.',
            'One hard moment does not define you or your relationship.',
        ),
    }
    situation, thought, reframe = examples.get(
        goal,
        (
            'Something stressful happens and your mind jumps to the worst conclusion.',
            'This proves everything is going badly.',
            'One moment can feel intense without defining the whole situation.',
        ),
    )
    return OnboardingAIResult(
        situation=situation,
        thought=thought,
        reframe=reframe,
        tone=_base_tone(request.context.style_context.coach_style),
        fallback_used=False,
    )


def _first_reframe_fallback(request: OnboardingAIRequest) -> OnboardingAIResult:
    context = request.context
    tone = _base_tone(context.style_context.coach_style)
    pattern = context.input_context.detected_pattern if context.input_context.detected_pattern != 'unknown' else detect_pattern_from_text(context.input_context.user_message or '')
    label = _pattern_label(pattern)
    user_type = context.account_context.user_type.strip().lower()
    goal = context.goal_context.goal.strip().lower()
    thought = (context.input_context.user_message or '').strip()

    reframe = 'This thought may be presenting the harshest explanation as if it were the only one.'
    if pattern == 'mind_reading':
        reframe = 'You may be filling in other people’s thoughts before you have enough evidence.'
    elif pattern == 'catastrophizing':
        reframe = 'Your mind may be jumping from a hard moment to the worst possible outcome.'
    elif pattern == 'labeling':
        reframe = 'A painful moment can lead to a harsh label, but labels often hide the fuller picture.'
    elif pattern == 'all_or_nothing':
        reframe = 'This may be turning one hard moment into a total conclusion, when the fuller picture is usually more mixed.'

    question = 'What facts support this thought, and what facts point to a different explanation?'
    if user_type == 'teen':
        question = 'What is one other explanation that could also be true here?'
    elif goal == 'focus':
        question = 'What is the smallest useful step you could do in the next 15 minutes?'
    elif goal == 'parenting':
        question = 'What response would match the parent you want to be in the next few minutes?'

    next_step = 'Write one alternative explanation that feels possible, even if you do not fully believe it yet.'
    if goal == 'focus':
        next_step = 'Choose one 15-minute task and start before you decide how you feel about it.'
    elif goal == 'friendships':
        next_step = 'List one neutral explanation before reacting to the situation.'
    elif goal == 'parenting':
        next_step = 'Pause, take one breath, and choose one calmer response for the next interaction.'

    if thought:
        if 'behind' in thought.lower():
            reframe = 'Feeling behind today does not mean you are failing overall. It may mean you are overloaded and need a smaller next step.'
            next_step = 'Choose one task you can finish in 10 minutes and start there.'
            question = 'What evidence says you are fully behind, and what evidence says this may be a hard day?'
        elif 'friendly' in thought.lower() or 'reply' in thought.lower():
            reframe = 'A distant interaction does not automatically mean rejection. There may be several explanations you do not know yet.'
            next_step = 'Wait for one more data point before deciding what the interaction means.'
            question = 'What else could explain their response besides a negative judgment about you?'

    return OnboardingAIResult(
        detected_pattern_label=label,
        pattern_label=label,
        reframe_title='A different way to look at it',
        reframe=reframe,
        reframe_text=reframe,
        next_step_title='Try this next',
        socratic_question=question,
        question_title='One question to test it',
        question_text=question,
        next_step=next_step,
        next_step_text=next_step,
        tone=tone,
        config_version=DEFAULT_FIRST_REFRAME_CONFIG['schema_version'],
        fallback_used=False,
    )


def _blocked_result(request: OnboardingAIRequest) -> OnboardingAIResult:
    return OnboardingAIResult(
        reframe='Let us pause the exercise for now and focus on immediate support.',
        reframe_text='Let us pause the exercise for now and focus on immediate support.',
        reframe_title='A different way to look at it',
        next_step='Open the support options on the next screen.',
        next_step_text='Open the support options on the next screen.',
        next_step_title='Try this next',
        question_title='One question to test it',
        question_text='What support can you reach for right now?',
        tone=_base_tone(request.context.style_context.coach_style),
        config_version=DEFAULT_FIRST_REFRAME_CONFIG['schema_version'],
        fallback_used=True,
    )


def _normalize_first_reframe_output(raw_text: str, fallback: OnboardingAIResult, show_pattern_label: bool) -> OnboardingAIResult:
    parsed: dict[str, str] = {}
    for line in [part.strip() for part in raw_text.splitlines() if part.strip()]:
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        parsed[key.strip().lower()] = value.strip()

    pattern_label = parsed.get('pattern_label') or fallback.pattern_label or fallback.detected_pattern_label
    reframe_text = parsed.get('reframe_text') or fallback.reframe_text or fallback.reframe or ''
    next_step_text = parsed.get('next_step_text') or fallback.next_step_text or fallback.next_step or ''
    question_text = parsed.get('question_text') or fallback.question_text or fallback.socratic_question or ''

    if not reframe_text:
        reframe_text = fallback.reframe_text or fallback.reframe or ''
    if not next_step_text:
        next_step_text = fallback.next_step_text or fallback.next_step or ''
    if not question_text or '?' not in question_text:
        question_text = fallback.question_text or fallback.socratic_question or 'What is one other explanation that could also be true here?'

    question_text = question_text.split('?')[0].strip() + '?'
    return fallback.model_copy(
        update={
            'pattern_label': pattern_label if show_pattern_label else None,
            'detected_pattern_label': pattern_label if show_pattern_label else None,
            'reframe_title': fallback.reframe_title or 'A different way to look at it',
            'reframe_text': reframe_text,
            'reframe': reframe_text,
            'next_step_title': fallback.next_step_title or 'Try this next',
            'next_step_text': next_step_text,
            'next_step': next_step_text,
            'question_title': fallback.question_title or 'One question to test it',
            'question_text': question_text,
            'socratic_question': question_text,
            'fallback_used': False,
        }
    )


def build_onboarding_ai_fallback(request: OnboardingAIRequest) -> OnboardingAIResult:
    if request.context.safety_context.scan_status in {'block', 'handoff'} or request.context.safety_context.needs_handoff:
        return _blocked_result(request)

    step = request.step
    tone = _base_tone(request.context.style_context.coach_style)
    goal = request.context.goal_context.goal.strip().lower()

    if step == 'goal_microcopy':
        return OnboardingAIResult(
            message=f"We'll focus on {_goal_hint(goal)}.",
            tone=tone,
            fallback_used=False,
        )
    if step == 'clarity_interpretation':
        return OnboardingAIResult(
            message=_clarity_message(request),
            tone=tone,
            fallback_used=False,
        )
    if step == 'style_confirmation':
        return OnboardingAIResult(
            message=f"I'll keep this {tone} and clear.",
            tone=tone,
            fallback_used=False,
        )
    if step == 'tutorial_example':
        return _tutorial_example(request)
    return _first_reframe_fallback(request)


def _build_prompt(request: OnboardingAIRequest, fallback: OnboardingAIResult, config: dict | None = None) -> str:
    context = request.context
    language = _language_name(context.entry_context.language)
    if request.step == 'first_reframe':
        active_config = config or DEFAULT_FIRST_REFRAME_CONFIG
        return (
            f"{active_config.get('system_prompt', '')}\n"
            f"{active_config.get('developer_prompt', '')}\n"
            f"Respond in {language}.\n"
            f"User type: {context.account_context.user_type}\n"
            f"Goal: {context.goal_context.goal}\n"
            f"Coach style: {context.style_context.coach_style}\n"
            f"Mental noise: {context.state_context.mental_noise_score}\n"
            f"Clarity: {context.state_context.clarity_score}\n"
            f"User thought: {context.input_context.user_message or ''}\n"
            "Output format:\n"
            "pattern_label: ...\n"
            "reframe_text: ...\n"
            "next_step_text: ...\n"
            "question_text: ...\n"
        )
    return (
        'You are ReframeQ, a supportive non-clinical CBT-style onboarding coach. '
        'Do not diagnose, prescribe, or make policy decisions. '
        f'Respond in {language}. '
        f'The onboarding step is {request.step}. '
        f'User type: {context.account_context.user_type}. '
        f'Account mode: {context.account_context.account_mode}. '
        f'Goal: {context.goal_context.goal}. '
        f'Coach style: {context.style_context.coach_style}. '
        f'Mental noise: {context.state_context.mental_noise_score}. '
        f'Clarity: {context.state_context.clarity_score}. '
        f'Detected pattern: {context.input_context.detected_pattern}. '
        f'User message: {context.input_context.user_message or ""}. '
        'Return plain text only. '
        'Use this fallback content as the structure and intent to preserve if you are uncertain: '
        f'message={fallback.message or ""}; '
        f'situation={fallback.situation or ""}; '
        f'thought={fallback.thought or ""}; '
        f'reframe={fallback.reframe or ""}; '
        f'question={fallback.socratic_question or ""}; '
        f'next_step={fallback.next_step or ""}.'
    )


def _try_model_enrichment(request: OnboardingAIRequest, fallback: OnboardingAIResult, config: dict | None = None) -> tuple[OnboardingAIResult, str]:
    prompt = _build_prompt(request, fallback, config)
    payload = {
        'model': (config or {}).get('model_name', settings.ollama_model),
        'prompt': prompt,
        'stream': False,
    }
    last_error: httpx.HTTPError | None = None
    data: dict = {}
    for base_url in _ollama_base_url_candidates():
        try:
            with httpx.Client(timeout=settings.ollama_timeout_seconds) as client:
                response = client.post(f'{base_url}/api/generate', json=payload)
                response.raise_for_status()
                data = response.json()
                break
        except httpx.HTTPError as exc:
            last_error = exc
            continue
    else:
        if last_error:
            raise last_error

    reply = str(data.get('response', '')).strip()
    if not reply:
        return fallback.model_copy(update={'fallback_used': True}), str(payload['model'])

    if request.step in {'goal_microcopy', 'clarity_interpretation', 'style_confirmation'}:
        return fallback.model_copy(update={'message': reply, 'fallback_used': False}), str(payload['model'])
    if request.step == 'tutorial_example':
        parts = [part.strip() for part in reply.split('\n') if part.strip()]
        if len(parts) >= 3:
            return fallback.model_copy(
                update={
                    'situation': parts[0],
                    'thought': parts[1],
                    'reframe': parts[2],
                    'fallback_used': False,
                }
            ), str(payload['model'])
        return fallback.model_copy(update={'fallback_used': True}), str(payload['model'])

    if request.step == 'first_reframe':
        normalized = _normalize_first_reframe_output(reply, fallback, bool((config or DEFAULT_FIRST_REFRAME_CONFIG).get('show_pattern_label', True)))
        return normalized, str(payload['model'])

    parts = [part.strip() for part in reply.split('\n') if part.strip()]
    if len(parts) >= 3:
        updates = {
            'reframe': parts[0],
            'socratic_question': parts[1],
            'next_step': parts[2],
            'fallback_used': False,
        }
        if len(parts) >= 4:
            updates['detected_pattern_label'] = parts[3]
        return fallback.model_copy(update=updates), str(payload['model'])
    return fallback.model_copy(update={'fallback_used': True}), str(payload['model'])


def generate_onboarding_ai_result(request: OnboardingAIRequest, config: dict | None = None) -> tuple[OnboardingAIResult, str]:
    fallback = build_onboarding_ai_fallback(request)
    if request.context.safety_context.scan_status in {'block', 'handoff'} or request.context.safety_context.needs_handoff:
        return fallback, 'safety_fallback'

    try:
        if request.step == 'first_reframe':
            enriched_fallback = fallback.model_copy(update={'config_version': (config or DEFAULT_FIRST_REFRAME_CONFIG).get('schema_version')})
            return _try_model_enrichment(request, enriched_fallback, config)
        return _try_model_enrichment(request, fallback, config)
    except httpx.HTTPError:
        return fallback.model_copy(update={'fallback_used': True}), 'fallback'
def _ollama_base_url_candidates() -> list[str]:
    configured = settings.ollama_base_url.rstrip('/')
    candidates = [configured]
    localhost = 'http://localhost:11434'
    docker_host = 'http://host.docker.internal:11434'
    for candidate in [localhost, docker_host]:
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates

