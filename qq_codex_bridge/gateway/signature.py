"""
QQ Official Bot webhook signature validation.

QQ uses Ed25519 signatures on the raw request body:
  - Header X-Signature-Ed25519 : hex-encoded signature
  - Header X-Signature-Timestamp: unix timestamp string

Verification:
  message = timestamp_bytes + body_bytes
  verify(public_key=bot_secret, message=message, signature=sig)

The bot_secret here is the 32-byte Ed25519 public key provided by the
QQ developer console (NOT the app secret used for OAuth).
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Optional

log = logging.getLogger(__name__)

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    from cryptography.exceptions import InvalidSignature
    _CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    _CRYPTOGRAPHY_AVAILABLE = False


def verify_signature(
    *,
    bot_secret: str,
    timestamp: str,
    body: bytes,
    signature: str,
) -> bool:
    """
    Verify Ed25519 signature from QQ webhook headers.

    Parameters
    ----------
    bot_secret:
        Hex-encoded Ed25519 public key from QQ developer console.
    timestamp:
        Value of X-Signature-Timestamp header.
    body:
        Raw request body bytes.
    signature:
        Value of X-Signature-Ed25519 header (hex).

    Returns True if valid, False otherwise.
    """
    if not bot_secret:
        log.warning("bot_secret not configured — skipping signature check")
        return True  # dev mode: allow all

    if not _CRYPTOGRAPHY_AVAILABLE:
        log.error(
            "cryptography package not installed; cannot verify signatures. "
            "Install with: pip install cryptography"
        )
        # Fail open only in dev; in prod raise or return False
        return False

    try:
        pub_key_bytes = bytes.fromhex(bot_secret)
        pub_key = Ed25519PublicKey.from_public_bytes(pub_key_bytes)

        message = timestamp.encode() + body
        sig_bytes = bytes.fromhex(signature)

        pub_key.verify(sig_bytes, message)
        return True
    except InvalidSignature:
        log.warning("Signature verification failed — invalid signature")
        return False
    except Exception as exc:
        log.error("Signature verification error: %s", exc)
        return False


def build_challenge_response(challenge: str) -> dict:
    """
    QQ sends a URL verification challenge on first webhook registration.
    Respond with {"plain": challenge}.
    """
    return {"plain": challenge}
