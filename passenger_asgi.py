"""v78 supported HTTP stack; same passenger payload contract as v75 local preview.

This is an ASGI *candidate* for an eventual production deployment. Guest state
remains process-local until an authoritative shared store / gateway replaces it;
do not advertise multi-replica scale from this module alone.
"""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

import run as core
from app_logging import audit
from integration_bridge import GatewayError
from runtime_security import guest_cookie, read_settings, response_headers

SETTINGS = read_settings()
FILES = {
    '/manifest.webmanifest': ('manifest.webmanifest', 'application/manifest+json'),
    '/sw.js': ('sw.js', 'application/javascript; charset=utf-8'),
    '/icon-192.png': ('icon-192.png', 'image/png'),
    '/icon-512.png': ('icon-512.png', 'image/png'),
    '/icon-180.png': ('icon-180.png', 'image/png'),
    '/living-orb.webp': ('living-orb.webp', 'image/webp'),
    '/linguist-x-mark-v54.png': ('linguist-x-mark-v54.png', 'image/png'),
    '/wordly-wordmark.png': ('wordly-wordmark.png', 'image/png'),
    '/app-logo.png': ('app-logo.png', 'image/png'),
    '/icon-180-v54.png': ('icon-180-v54.png', 'image/png'),
    '/icon-192-v54.png': ('icon-192-v54.png', 'image/png'),
    '/icon-512-v54.png': ('icon-512-v54.png', 'image/png'),
}


def _json(status: int, body: dict, *, guest: str | None = None, max_age: int = 0) -> JSONResponse:
    """Build no-store JSON responses and, when requested, issue the opaque guest cookie using shared security policy."""
    resp = JSONResponse(body, status_code=status, headers={'Cache-Control': 'no-store'})
    if guest is not None:
        resp.headers['Set-Cookie'] = guest_cookie(guest, max_age=max_age, production=SETTINGS.production)
    return resp


def _bad(error: Exception, *, clear=False) -> JSONResponse:
    """Map a sanitized application/gateway exception to JSON, optionally clearing a previously issued guest handle."""
    return _json(error.status, {'error': error.message}, guest='' if clear else None)


def _local_owner(request: Request) -> bool:
    """Return True only for loopback clients; developer endpoints are never intended for remote or production use."""
    return (not SETTINGS.production and request.client is not None
            and request.client.host in ('127.0.0.1', '::1'))


def _same_origin(request: Request) -> bool:
    """Enforce exact configured production origin for browser mutations while retaining safe local-development behavior."""
    origin = request.headers.get('origin', '')
    host = request.headers.get('host', '')
    if SETTINGS.production:
        # Browser JSON mutations must declare the exact approved origin.
        return origin == SETTINGS.public_origin
    return not origin or origin in ('http://' + host, 'https://' + host)


async def _body(request: Request, *, max_bytes=2048) -> dict:
    """Stream and parse a bounded JSON object so chunked requests cannot bypass request-size limits."""
    if request.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
        raise GatewayError('Expected JSON.', 415)
    if request.headers.get('content-length'):
        try:
            length = int(request.headers['content-length'])
        except ValueError:
            raise GatewayError('Invalid request size.', 413) from None
        if length <= 0 or length > max_bytes:
            raise GatewayError('Invalid request size.', 413)
    # Streaming bound prevents chunked transfers bypassing Content-Length.
    chunks, total = [], 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > max_bytes:
            raise GatewayError('Invalid request size.', 413)
        chunks.append(chunk)
    if not total:
        raise GatewayError('Invalid request size.', 413)
    try:
        data = json.loads(b''.join(chunks))
    except (ValueError, UnicodeDecodeError):
        raise GatewayError('Invalid JSON.', 400) from None
    if not isinstance(data, dict):
        raise GatewayError('Expected object.', 400)
    return data


async def dispatch(request: Request):
    """Top-level method/path router for health, API, and static content with a deliberately small allowed method set."""
    path = request.url.path
    method = request.method
    if method not in ('GET', 'POST'):
        return _json(405, {'error': 'Method not allowed.'})
    if path in ('/healthz', '/readyz'):
        if method != 'GET':
            return _json(405, {'error': 'Method not allowed.'})
        if path == '/readyz' and core.GATEWAY.configured() and core.GATEWAY._distributed:
            try:
                healthy = await run_in_threadpool(core.GATEWAY.guests.client.ping)
                if not healthy:
                    return _json(503, {'status': 'unavailable'})
            except Exception:
                return _json(503, {'status': 'unavailable'})
        return _json(200, {'status': 'ok'})
    if path.startswith('/api/'):
        return await api(request, path, method)
    if method != 'GET':
        return _json(405, {'error': 'Method not allowed.'})
    return await static(request, path)


async def api(request: Request, path: str, method: str):
    """ASGI application API router. Blocking provider/gateway functions are pushed into Starlette threadpool workers."""
    gateway = core.GATEWAY
    cookie = request.cookies.get('lx_guest', '')
    q = request.query_params
    dev = path.startswith('/api/dev/')
    if dev and SETTINGS.production:
        return _json(404, {'error': 'Unknown endpoint.'})
    if dev and not _local_owner(request):
        return _json(403, {'error': 'Loopback-only developer endpoint.'})

    try:
        if method == 'POST':
            if not _same_origin(request):
                raise GatewayError('Unexpected request origin.', 403)
            if path == '/api/dev/mode':
                return _json(200, gateway.set_mode((await _body(request)).get('mode')))
            if path == '/api/dev/fixture':
                if core.FIXTURE is None:
                    raise GatewayError('Fixture not enabled for this local owner.', 403)
                data = await _body(request)
                try:
                    result = core.FIXTURE.set_scenario(data.get('scenario'))
                except ValueError:
                    raise GatewayError('Invalid fixture scenario.', 400) from None
                return _json(200, result)
            if path == '/api/integration/leave':
                await _body(request)
                gateway.clear_guest(cookie)
                resp = Response(status_code=204, headers={'Cache-Control': 'no-store'})
                resp.headers['Set-Cookie'] = guest_cookie('', production=SETTINGS.production)
                return resp
            if path == '/api/integration/join':
                data = await _body(request)
                gateway.clear_guest(cookie)
                handle, result = await run_in_threadpool(gateway.join, data.get('sessionId'),
                                                          data.get('language'), data.get('inviteCode'))
                return _json(201, result, guest=handle, max_age=result['expiresIn'])
            if path == '/api/live/session':
                data = await _body(request, max_bytes=65536)
                return _json(201, await run_in_threadpool(core.create_live_session, data))
            if path == '/api/flight-number-vision':
                data = await _body(request, max_bytes=550000)
                return _json(200, await run_in_threadpool(core.extract_flight_number_vision,
                                                           data.get('image')))
            return _json(404, {'error': 'Unknown endpoint.'})

        if path == '/api/dev/status':
            return _json(200, gateway.snapshot())
        if path == '/api/dev/fixture':
            if core.FIXTURE is None:
                raise GatewayError('Fixture not enabled for this local owner.', 403)
            return _json(200, {'enabled': True, 'scenario': core.FIXTURE.scenario,
                               'scenarios': core.SCENARIOS, 'source': 'test-fixture'})
        if path == '/api/integration/health':
            return _json(200, await run_in_threadpool(gateway.health))
        if path == '/api/integration/sessions':
            return _json(200, await run_in_threadpool(gateway.sessions, q.get('flight', '')))
        if path == '/api/integration/invite':
            return _json(200, await run_in_threadpool(gateway.resolve_invite, q.get('code', '')))
        if path == '/api/integration/state':
            return _json(200, await run_in_threadpool(gateway.state, cookie))
        if path == '/api/integration/events':
            try:
                after = int(q.get('after', '0'))
            except (ValueError, TypeError):
                return _json(400, {'error': 'Invalid cursor.'})
            return _json(200, await run_in_threadpool(gateway.events, cookie, after))
        if path == '/api/status':
            return _json(200, {'flightConfigured': bool(core.API_KEY),
                               'voiceConfigured': bool(core.OPENAI_KEY),
                               'liveVoiceConfigured': bool(core.OPENAI_KEY),
                               'visionConfigured': bool(core.OPENAI_KEY),
                               'engine': 'gpt-4o-mini-tts',
                               'weatherConfigured': bool(core.WEATHER_KEY)})
        if path == '/api/demo-audio':
            data = await run_in_threadpool(core.demo_audio, q.get('lang', ''), q.get('id', ''))
            return Response(data, media_type='audio/mpeg', headers={'Cache-Control': 'private, max-age=3600'})
        if path == '/api/airline-library':
            bundled = sorted(p.stem for p in (core.HERE / 'airlines' / 'custom').glob('*.svg'))
            cached = sorted(p.stem for p in core.AIRLINE_CACHE.glob('*.svg')) if core.AIRLINE_CACHE.exists() else []
            catalog = await run_in_threadpool(core._get_airline_catalog)
            return _json(200, {'bundled_vectors': bundled, 'cached_vectors': cached,
                               'vector_candidates': core.AIRLINE_LIBRARY['svg_candidates'],
                               'seed_catalog': core.AIRLINE_LIBRARY['seed'],
                               'remote_catalog_eligible': len(catalog),
                               'note': core.AIRLINE_LIBRARY['note']})
        if path == '/api/airline-logo':
            code = q.get('code', '')
            if not re.fullmatch('[A-Za-z0-9]{2,3}', code):
                return Response(status_code=400)
            result = await run_in_threadpool(core.airline_logo, code)
            if result is None:
                return Response(status_code=404, headers={'Cache-Control': 'no-store'})
            data, mime = result
            headers = {'Cache-Control': 'public, max-age=3600'}
            if mime == 'image/svg+xml':
                headers['Content-Security-Policy'] = "default-src 'none'; style-src 'unsafe-inline'"
            return Response(data, media_type=mime, headers=headers)
        if path == '/api/weather':
            return _json(200, await run_in_threadpool(core.destination_weather,
                                                       q.get('q', ''), q.get('lang', 'en')))
        if path == '/api/flights':
            return _json(200, await run_in_threadpool(core.lookup, q.get('q', ''),
                              refresh=q.get('refresh', '') == '1', local_date=q.get('date', '')))
        return _json(404, {'error': 'Unknown endpoint.'})
    except GatewayError as exc:
        return _bad(exc, clear=(path == '/api/integration/join'))
    except core.APIError as exc:
        return _bad(exc)


async def static(request: Request, path: str):
    """Serve only reviewed static paths; the internal documentation page is nonproduction-only and passenger root is panel-free in production."""
    if path == '/developer-documentation.html':
        if SETTINGS.production:
            return Response(status_code=404)
        return Response((core.HERE / 'developer-documentation.html').read_bytes(), media_type='text/html',
                        headers={'Cache-Control': 'no-store'})
    if path in ('/', '/index.html', '/passenger-only.html'):
        if SETTINGS.production and path == '/':
            filename = 'passenger-only.html'
        else:
            filename = 'passenger-only.html' if path == '/passenger-only.html' else 'index.html'
        return Response((core.HERE / filename).read_bytes(), media_type='text/html',
                        headers={'Cache-Control': 'no-store'})
    if path.startswith('/airlines/custom/'):
        name = path.removeprefix('/airlines/custom/')
        if not re.fullmatch('[A-Z0-9]{2,3}\\.svg', name):
            return Response(status_code=404)
        file = core.HERE / 'airlines' / 'custom' / name
        if not file.is_file():
            return Response(status_code=404)
        clean = await run_in_threadpool(core._clean_svg, file.read_bytes())
        return Response(clean, media_type='image/svg+xml', headers={
            'Cache-Control': 'public, max-age=86400',
            'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'"}) if clean else Response(status_code=404)
    if path.startswith('/weather/'):
        name = path.removeprefix('/weather/')
        if not re.fullmatch('(clear|partly|cloudy|mist|rain|showers|drizzle|sleet|snow|storm|night|wind)\\.(png|webp)', name):
            return Response(status_code=404)
        file = core.HERE / 'weather' / name
        if not file.is_file():
            return Response(status_code=404)
        mime = 'image/png' if name.endswith('.png') else 'image/webp'
        return Response(file.read_bytes(), media_type=mime, headers={'Cache-Control': 'public, max-age=86400'})
    item = FILES.get(path)
    if item is None:
        return Response(status_code=404)
    file, mime = item
    return Response((core.HERE / file).read_bytes(), media_type=mime,
                    headers={'Cache-Control': 'no-cache' if path == '/sw.js' else 'public, max-age=3600'})


@asynccontextmanager
async def lifespan(_app):
    """Apply startup invariants, wire the optional local fixture, and force configured production gateways into Integration without clearing shared users."""
    if SETTINGS.production and core.FIXTURE is not None:
        raise RuntimeError('Test fixture forbidden in production.')
    if SETTINGS.production and core.GATEWAY.configured() and not core.GATEWAY._distributed:
        raise RuntimeError('Production gateway requires shared guest state.')
    fixture_server = None
    if SETTINGS.enable_fixture:
        fixture_server = core.start_fixture(0, core.FIXTURE)
        port = fixture_server.server_address[1]
        core.GATEWAY.base = f'http://127.0.0.1:{port}'
        print('ASGI local TEST FIXTURE enabled; NOT live Wordly.', flush=True)
    elif SETTINGS.production and core.GATEWAY.configured():
        # No global demo/integration toggle in the production passenger build.
        # A worker starting must not revoke guests admitted by existing workers.
        core.GATEWAY.mode = 'integration'
    try:
        yield
    finally:
        if fixture_server:
            await run_in_threadpool(fixture_server.shutdown)
            fixture_server.server_close()


app = Starlette(routes=[Route('/{path:path}', dispatch, methods=['GET', 'POST'])], lifespan=lifespan)


async def security_and_audit(request: Request, call_next):
    """Apply host policy, metadata-only error auditing, request IDs, baseline headers, and API no-store defaults around every ASGI request."""
    started = time.monotonic()
    rid = uuid.uuid4().hex
    try:
        if SETTINGS.production and request.headers.get('host', '').lower() != SETTINGS.public_origin.removeprefix('https://'):
            response = _json(400, {'error': 'Unexpected host.'})
        else:
            response = await call_next(request)
    except Exception:
        # Do not echo tracebacks, gateway tokens, query strings, or content.
        response = _json(500, {'error': 'Internal service error.'})
        audit('request_internal_error', status=500, elapsed_ms=(time.monotonic()-started)*1000,
              request_id=rid)
    for name, value in response_headers(SETTINGS.production).items():
        response.headers.setdefault(name, value)
    response.headers['X-Request-ID'] = rid
    if request.url.path.startswith('/api/') and 'cache-control' not in response.headers:
        response.headers['Cache-Control'] = 'no-store'
    if response.status_code >= 400 and request.url.path.startswith('/api/'):
        audit('api_request_denied', status=response.status_code,
              elapsed_ms=(time.monotonic()-started)*1000, request_id=rid)
    return response


app.add_middleware(BaseHTTPMiddleware, dispatch=security_and_audit)
