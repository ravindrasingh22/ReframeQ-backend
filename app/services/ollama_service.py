import httpx

from app.core.config import settings


def generate_chat_reply(message: str, language: str = 'en', history: list[tuple[str, str]] | None = None) -> tuple[str, str]:
    prompt_prefix = (
        'You are ReframeQ, a supportive non-clinical CBT-style wellness coach. '
        'Do not diagnose or prescribe. Keep response brief and empathetic. '
    )
    if language.strip().lower() == 'hinglish':
        prompt_prefix += 'Respond in natural Hinglish (Hindi-English mix, Roman script). '
    else:
        prompt_prefix += 'Respond in simple English. '

    history_lines: list[str] = []
    for role, content in (history or []):
        speaker = 'User' if role == 'user' else 'Assistant'
        history_lines.append(f'{speaker}: {content}')

    prompt = f'{prompt_prefix}\n' + '\n'.join(history_lines) + f'\nUser: {message}\nAssistant:'

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
