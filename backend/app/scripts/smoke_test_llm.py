import asyncio
import json

from backend.app.agent.service import LLMService
from backend.app.core.errors import LLMProviderError
from backend.app.dependencies import get_settings


async def main() -> None:
    settings = get_settings()
    service = LLMService(settings)
    try:
        response = await service.generate_json(
            'Return valid JSON with keys "status" and "message". '
            'Use status="ok" and a short message.'
        )
    except LLMProviderError as exc:
        _print_provider_error(exc)
        return

    print(f"provider_used: {response.provider_used}")
    print("attempts:")
    for attempt in response.attempts:
        print(
            "- "
            f"provider={attempt.provider} "
            f"model={attempt.model} "
            f"success={attempt.success} "
            f"latency_ms={attempt.latency_ms:.2f} "
            f"error={attempt.error or ''}"
        )
    print("content:")
    print(json.dumps(response.response.content, indent=2, sort_keys=True))


def _print_provider_error(error: LLMProviderError) -> None:
    print("LLM provider smoke test failed.")
    print(f"error: {error}")
    attempts = error.details.get("attempts", [])
    if attempts:
        print("attempts:")
        for attempt in attempts:
            print(
                "- "
                f"provider={attempt.get('provider')} "
                f"model={attempt.get('model')} "
                f"success={attempt.get('success')} "
                f"latency_ms={attempt.get('latency_ms')} "
                f"error={attempt.get('error') or ''}"
            )


if __name__ == "__main__":
    asyncio.run(main())
