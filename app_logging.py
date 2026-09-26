"""Small privacy-preserving JSON event logger; never include URL, token or content."""
from __future__ import annotations

import json
import logging
import os
import time
import uuid

LOGGER = logging.getLogger('linguist_x')
if not LOGGER.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter('%(message)s'))
    LOGGER.addHandler(h)
LOGGER.setLevel(getattr(logging, os.getenv('LX_LOG_LEVEL', 'INFO').upper(), logging.INFO))


def audit(event: str, *, status: int, elapsed_ms: float = 0, request_id: str | None = None) -> str:
    """Emit one fixed-schema JSON audit event containing metadata only. Do not extend this function with raw request, token, caption, invitation, or passenger fields."""
    request_id = request_id or uuid.uuid4().hex
    # Callers can only pass this fixed, metadata-only schema. Never add raw route
    # query, flight details, invitations, cookies, caption or provider credentials.
    LOGGER.info(json.dumps({'event': event, 'status': status, 'latency_ms': round(elapsed_ms, 2),
                            'request_id': request_id, 'timestamp': round(time.time(), 3)}, separators=(',', ':')))
    return request_id
