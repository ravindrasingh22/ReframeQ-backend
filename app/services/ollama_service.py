import httpx

from app.core.config import settings


def _detect_distortion(text: str) -> str:
    normalized = text.strip().lower()
    if not normalized:
        return 'general reflection'
    if any(phrase in normalized for phrase in ['they think', 'judging me', 'everyone thinks', 'they must think']):
        return 'mind reading'
    if any(phrase in normalized for phrase in ['always', 'never', 'ruined', 'impossible', 'nothing works']):
        return 'all-or-nothing'
    if any(phrase in normalized for phrase in ['disaster', 'everything will go wrong', 'worst will happen']):
        return 'catastrophizing'
    if any(phrase in normalized for phrase in ['i am a failure', 'useless', 'stupid']):
        return 'labeling'
    return 'general reflection'


def generate_chat_reply(message: str, language: str = 'en', history: list[tuple[str, str]] | None = None) -> tuple[str, str]:
    distortion = _detect_distortion(message)
    prompt_prefix = (
        'You are ReframeQ, a supportive non-clinical CBT-style wellness coach for the end user. '
        'The platform is the coach and the human is the user seeking help with a difficult thought. '
        'Do not answer like a search engine, teacher, or generic assistant. '
        'Do not explain scientific evidence, research sources, or general knowledge unless the user explicitly asks for factual information. '
        'Do not answer your own Socratic question. Instead, guide the user to reflect on their own situation. '
        'Your job is to respond to the user thought with: 1 short validation, 1 brief cognitive pattern label when relevant, 1 grounded Socratic question, and 1 small next step. '
        'Keep the response to 2 to 4 short sentences total. '
        'Do not diagnose or prescribe. '
    )
    if language.strip().lower() == 'hinglish':
        prompt_prefix += 'Respond in natural Hinglish (Hindi-English mix, Roman script). '
    else:
        prompt_prefix += 'Respond in simple English. '

    history_lines: list[str] = []
    for role, content in (history or []):
        speaker = 'User' if role == 'user' else 'Assistant'
        history_lines.append(f'{speaker}: {content}')

    prompt = (
        f'{prompt_prefix}\n'
        f'Likely cognitive pattern in the latest user message: {distortion}.\n'
        'If the user shares a belief like "people are unfriendly" or "I will fail", stay anchored to that belief and help them test it. '
        'Prefer questions like "What is one other explanation?" or "What evidence points against this thought?" '
        'Never turn the exchange into an informational article.\n'
        + '\n'.join(history_lines)
        + f'\nUser: {message}\nAssistant:'
    )

    payload = {
        'model': settings.ollama_model,
        'prompt': prompt,
        'stream': False,
    }

    with httpx.Client(timeout=settings.ollama_timeout_seconds) as client:
        response = client.post(f'{settings.ollama_base_url}/api/generate', json=payload)
        response.raise_for_status()
        data = response.json()

    reply = str(data.get('response', '')).strip()
    if not reply:
        reply = 'I am here with you. Let us take one small calm step together.'
    return reply, settings.ollama_model
