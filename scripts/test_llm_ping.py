#!/usr/bin/env python3
"""
Standalone LLM provider health check and credential verification CLI.

Implements Issue #25: [Bug] Provider Base URL & Credential Verification Check.

Tasks:
1. Verify environment variable loading: Ensure os.getenv("GROQ_API_KEY") (or OPENROUTER_API_KEY)
   is actually populated at process boot, not None, not empty "", and not an unconfigured placeholder.
2. Verify explicit base_url configuration:
   - Groq: base_url="https://api.groq.com/openai/v1"
   - OpenRouter: base_url="https://openrouter.ai/api/v1"
3. Initialize exact AsyncOpenAI client configuration with httpx.AsyncClient(timeout=8.0).
4. Send a 1-token test prompt ("ping") to upstream provider.
5. Log upstream raw HTTP status code and response payload.
"""

import asyncio
import os
from pathlib import Path
import sys
from typing import Any

# Ensure backend directory is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "scripts" else SCRIPT_DIR
BACKEND_DIR = REPO_ROOT / "backend"

for directory in [str(REPO_ROOT), str(BACKEND_DIR)]:
    if directory not in sys.path:
        sys.path.insert(0, directory)

# Load environment file if present
try:
    from dotenv import load_dotenv
    for env_candidate in [BACKEND_DIR / ".env", REPO_ROOT / ".env", Path(".env")]:
        if env_candidate.exists():
            load_dotenv(env_candidate)
            break
except ImportError:
    pass

import httpx
import openai

try:
    from app.config import get_llm_config, get_settings
except ImportError:
    # Fallback if running completely decoupled from app module
    get_settings = None
    get_llm_config = None


GROQ_DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
OPENROUTER_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
PLACEHOLDER_KEYS = {
    "gsk_your_api_key_here",
    "your_groq_api_key_here",
    "your_openrouter_api_key_here",
    "your_api_key_here",
}


def mask_key(key: str | None) -> str:
    """Mask key preserving prefix and last 4 characters for debugging."""
    if not key:
        return "<EMPTY/NONE>"
    if len(key) <= 8:
        return "***"
    return f"{key[:6]}...{key[-4:]}"


def verify_env_credentials() -> tuple[bool, str, dict[str, Any]]:
    """
    Verify environment variable loading at process boot.

    Ensures GROQ_API_KEY (or OPENROUTER_API_KEY) is populated,
    not None, not empty, and not an unconfigured placeholder.
    """
    groq_key = os.getenv("GROQ_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    # Also check pydantic settings if available
    if get_settings:
        try:
            settings = get_settings()
            groq_key = groq_key or settings.GROQ_API_KEY
            openrouter_key = openrouter_key or settings.OPENROUTER_API_KEY
        except Exception:
            pass

    details = {
        "GROQ_API_KEY_present": bool(groq_key),
        "GROQ_API_KEY_masked": mask_key(groq_key),
        "OPENROUTER_API_KEY_present": bool(openrouter_key),
        "OPENROUTER_API_KEY_masked": mask_key(openrouter_key),
    }

    # Validate non-empty and non-placeholder
    has_valid_groq = bool(groq_key and groq_key.strip() and groq_key.strip() not in PLACEHOLDER_KEYS)
    has_valid_openrouter = bool(openrouter_key and openrouter_key.strip() and openrouter_key.strip() not in PLACEHOLDER_KEYS)

    if not has_valid_groq and not has_valid_openrouter:
        msg = (
            "CREDENTIAL ERROR: Neither GROQ_API_KEY nor OPENROUTER_API_KEY is populated with a valid key!\n"
            f"  GROQ_API_KEY: {details['GROQ_API_KEY_masked']}\n"
            f"  OPENROUTER_API_KEY: {details['OPENROUTER_API_KEY_masked']}\n"
            "Please check your .env file or environment variables."
        )
        return False, msg, details

    return True, "Credentials verified successfully.", details


def resolve_provider_config() -> dict[str, str]:
    """
    Resolve active provider and verify explicit base_url configuration.

    - Groq: base_url="https://api.groq.com/openai/v1"
    - OpenRouter: base_url="https://openrouter.ai/api/v1"
    """
    if get_llm_config and get_settings:
        cfg = get_llm_config()
        return cfg

    # Fallback resolution from raw environment variables
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    provider_env = os.getenv("LLM_PROVIDER", "").strip().lower()

    if provider_env == "openrouter" or (not groq_key and openrouter_key) or groq_key.startswith("sk-or-"):
        return {
            "provider": "openrouter",
            "api_key": openrouter_key or groq_key,
            "base_url": os.getenv("OPENROUTER_BASE_URL", OPENROUTER_DEFAULT_BASE_URL).strip(),
            "model": os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct").strip(),
        }

    return {
        "provider": "groq",
        "api_key": groq_key,
        "base_url": os.getenv("GROQ_BASE_URL", GROQ_DEFAULT_BASE_URL).strip(),
        "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip(),
    }


async def ping_llm(
    config: dict[str, str] | None = None,
    client: openai.AsyncOpenAI | None = None,
) -> dict[str, Any]:
    """
    Initialize AsyncOpenAI client configuration and dispatch a 1-token test prompt ("ping").

    Logs the upstream raw HTTP status code and response payload.
    """
    if config is None:
        config = resolve_provider_config()

    provider = config.get("provider", "groq")
    base_url = config.get("base_url", GROQ_DEFAULT_BASE_URL)
    api_key = config.get("api_key", "")
    model = config.get("model", "llama-3.1-8b-instant")

    print(f"\n[INIT] Active Provider: {provider.upper()}")
    print(f"[INIT] Base URL:        {base_url}")
    print(f"[INIT] Model:           {model}")
    print(f"[INIT] API Key:         {mask_key(api_key)}")
    print(f"[INIT] Client Timeout:  8.0s")

    # Verify expected base_url per provider
    if provider == "openrouter" and not base_url.startswith("https://openrouter.ai"):
        print(f"[WARNING] OpenRouter base_url does not start with https://openrouter.ai (got {base_url})")
    elif provider == "groq" and not base_url.startswith("https://api.groq.com"):
        print(f"[WARNING] Groq base_url does not start with https://api.groq.com (got {base_url})")

    # Initialize exact AsyncOpenAI client configuration
    if client is None:
        http_client = httpx.AsyncClient(timeout=8.0)
        client = openai.AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            http_client=http_client,
        )

    print("\n[DISPATCH] Sending 1-token test prompt ('ping') to upstream provider...")
    result: dict[str, Any] = {
        "provider": provider,
        "base_url": base_url,
        "model": model,
        "success": False,
        "status_code": None,
        "response_payload": None,
        "error": None,
    }

    try:
        raw_response = await client.chat.completions.with_raw_response.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
            timeout=8.0,
        )

        status_code = raw_response.status_code
        payload_text = raw_response.text
        parsed = raw_response.parse()
        reply_content = parsed.choices[0].message.content if parsed.choices else ""

        result["success"] = True
        result["status_code"] = status_code
        result["response_payload"] = payload_text
        result["reply"] = reply_content

        print(f"\n[SUCCESS] Upstream HTTP Status Code: {status_code}")
        print(f"[SUCCESS] Upstream Raw Response Payload:\n{payload_text}")
        print(f"[SUCCESS] Parsed Reply: '{reply_content}'")
        return result

    except openai.APIStatusError as exc:
        result["status_code"] = exc.status_code
        result["response_payload"] = getattr(exc.response, "text", str(exc))
        result["error"] = str(exc)
        print(f"\n[UPSTREAM HTTP ERROR] Status Code: {exc.status_code}")
        print(f"[UPSTREAM HTTP ERROR] Response Payload:\n{result['response_payload']}")
        return result

    except openai.APITimeoutError as exc:
        result["error"] = f"Request timed out after 8.0s: {str(exc)}"
        print(f"\n[TIMEOUT ERROR] {result['error']}")
        return result

    except openai.APIConnectionError as exc:
        result["error"] = f"Network/DNS/SSL connection error: {str(exc)}"
        print(f"\n[CONNECTION ERROR] {result['error']}")
        return result

    except Exception as exc:
        result["error"] = f"Unexpected failure: {type(exc).__name__}: {str(exc)}"
        print(f"\n[UNEXPECTED ERROR] {result['error']}")
        return result


def main() -> int:
    """CLI execution entrypoint."""
    print("=" * 70)
    print("AI Jailbreak Arena: Provider Base URL & Credential Verification")
    print("=" * 70)

    # 1. Environment Variable Loading Check
    valid_creds, cred_msg, details = verify_env_credentials()
    print(f"\n[STEP 1] Environment Variable Loading Verification:")
    for k, v in details.items():
        print(f"  - {k}: {v}")

    if not valid_creds:
        print(f"\n[FAILED] {cred_msg}")
        return 1

    print("[PASSED] Environment variables loaded successfully.")

    # 2. Provider Base URL Verification
    print(f"\n[STEP 2] Provider Base URL Configuration Check:")
    config = resolve_provider_config()
    print(f"  - Provider: {config['provider']}")
    print(f"  - Base URL: {config['base_url']}")
    print(f"  - Model:    {config['model']}")
    print("[PASSED] Provider configuration resolved.")

    # 3 & 4. Standalone 1-Token Ping & Raw HTTP Logging
    print(f"\n[STEP 3] Upstream 1-Token Connectivity Ping:")
    result = asyncio.run(ping_llm(config))

    if result.get("success"):
        print("\n" + "=" * 70)
        print("RESULT: ALL PROVIDER HEALTH CHECKS PASSED (200 OK)")
        print("=" * 70)
        return 0
    else:
        print("\n" + "=" * 70)
        print(f"RESULT: HEALTH CHECK FAILED (Status Code: {result.get('status_code')})")
        print(f"Error: {result.get('error')}")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
