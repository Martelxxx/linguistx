"""Local, single-user Linguist-X flight-data testing proxy. Python 3.10+, no dependencies.
Run: python run.py, then open http://127.0.0.1:8765
The API key stays on this local server; it is never sent to the browser.
"""
from __future__ import annotations
import datetime as dt
import base64
import hashlib
import tempfile
import json
import os
import re
import threading
import time
import sys
import getpass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from http.cookies import SimpleCookie
from integration_bridge import GATEWAY, GatewayError
from runtime_security import read_settings, guest_cookie, response_headers
from app_logging import audit
from fixture_gateway import Fixture, start_fixture, SCENARIOS
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
KEY_FILE = HERE / '.env'
# Stable, per-user credentials are loaded only in non-production runtimes.
from local_service_setup import read_user_keys, save_user_keys
VALID_KEYS = ('AVIATIONSTACK_KEY','OPENAI_API_KEY','WEATHERAPI_KEY')

def _valid(value: str) -> bool:
    """Return True only for non-placeholder local secret values; never logs or normalizes the secret beyond trimming."""
    value = value.strip().strip('\"\'')
    return bool(value and not value.startswith('YOUR_') and value not in ('CHANGEME','<KEY>'))

def _read_env(content: str) -> dict[str,str]:
    """Parse only the three legacy optional provider keys from .env text; unrelated variables are preserved elsewhere and ignored here."""
    values = {}
    for raw in content.splitlines():
        line = raw.strip().lstrip('\ufeff')
        if line.startswith('export '): line = line[7:]
        if not line or line.startswith('#') or '=' not in line: continue
        key,value = line.split('=',1)
        key=key.strip()
        value=value.strip().strip('\"\'')
        if key in VALID_KEYS and _valid(value): values[key]=value
    return values

def _local_config() -> dict[str,str]:
    """Load environment/current .env keys and optionally enter missing ones.

    DEVNOTE (v79): Never persist environment-injected secrets to .env. Only
    locally typed values are persisted. The one-command start.py launcher
    now handles local hidden entry itself and passes LX_NO_SETUP=1 here.
    Direct run.py retains its original interactive fallback.
    """
    values = {k: os.getenv(k, '').strip() for k in VALID_KEYS if _valid(os.getenv(k, ''))}
    if not SETTINGS.production:
        # Environment overrides persisted defaults. The HOME store wins over an
        # old per-release .env; both remain entirely server-side.
        for k, v in read_user_keys().items():
            values.setdefault(k, v)
        if KEY_FILE.exists():
            for k, v in _read_env(KEY_FILE.read_text(encoding='utf-8')).items():
                values.setdefault(k, v)
    missing = set(VALID_KEYS) - set(values)
    entered = {}
    if missing and sys.stdin.isatty() and os.getenv('LX_NO_SETUP') != '1':
        print('One-time setup: enter any missing keys. Input is hidden and stored locally.', flush=True)
        for key in VALID_KEYS:
            if key in missing:
                try:
                    entry = getpass.getpass(key + ' (press Enter to skip): ').strip()
                except (EOFError, KeyboardInterrupt):
                    entry = ''
                if _valid(entry):
                    values[key] = entry
                    entered[key] = entry
    if not SETTINGS.production and entered:
        try:
            save_user_keys(entered)
        except (OSError, ValueError):
            print('Could not save private credentials; using locally entered keys for this run only.', flush=True)
    return values

SETTINGS = read_settings()
_config=_local_config()
API_KEY=_config.get('AVIATIONSTACK_KEY','')
OPENAI_KEY=_config.get('OPENAI_API_KEY','')
WEATHER_KEY=_config.get('WEATHERAPI_KEY','')
VISION_MODEL = os.getenv('LX_VISION_MODEL', 'gpt-4o-mini')  # Vision-enabled; override via environment if required.
TTS_MODEL = 'gpt-4o-mini-tts'
TTS_VOICE = 'coral'
TTS_INSTRUCTIONS = 'Speak in the language of the supplied text, with a reassuring, clear, natural airport announcement delivery. Maintain the exact supplied wording. Do not add or omit information.'
DEMO_MESSAGES = json.loads((HERE / 'demo_messages.json').read_text(encoding='utf-8'))
AUDIO_CACHE = HERE / 'audio_cache'
AUDIO_CACHE.mkdir(exist_ok=True)
AUDIO_LOCK = threading.Lock()
# OpenAI key is loaded from .env below
PORT = SETTINGS.port
FIXTURE_ENABLED = SETTINGS.enable_fixture
FIXTURE=None
FIXTURE_SERVER=None
if FIXTURE_ENABLED:
    if os.getenv('LX_LAN')=='1':raise RuntimeError('Local fixture must not be enabled in LAN mode.')
    import secrets as _lx_secrets
    FIXTURE=Fixture(_lx_secrets.token_urlsafe(32))
    # Fixture binds to an OS-selected ephemeral loopback port at startup.
    GATEWAY.token=FIXTURE.service_token
    GATEWAY.fixture=True

CACHE_SECONDS = 300
CACHE: dict[str, tuple[float, dict]] = {}
LOCK = threading.Lock()
CORS_ALLOW = None  # Same-origin requests only.
WEATHER_LOCK=threading.Lock()
WEATHER_CACHE={}
WEATHER_TTL=600
WEATHER_SCENES={'clear','cloudy','mist','rain','snow','storm','night'}

def weather_scene(code: int) -> str:
    """Map WeatherAPI condition codes to the small visual-scene vocabulary understood by the passenger frontend."""
    if code in (1087,1273,1276,1279,1282): return 'storm'
    if code in (1066,1069,1072,1114,1117,1210,1213,1216,1219,1222,1225,1237,1255,1258,1261,1264): return 'snow'
    if code in (1063,1150,1153,1168,1171,1180,1183,1186,1189,1192,1195,1198,1201,1204,1207,1240,1243,1246,1249,1252): return 'rain'
    if code in (1030,1135,1147): return 'mist'
    if code in (1006,1009): return 'cloudy'
    return 'clear'

def destination_weather(code: str, lang: str = 'en') -> dict:
    """Fetch and normalize current destination weather with a short in-process cache and bounded, sanitized upstream handling."""
    code=code.upper().strip()
    if not re.fullmatch('[A-Z]{3}', code): raise APIError('Invalid destination airport code.', 400)
    if lang not in ('en','fr','es','zh','ar','pt'): lang='en'
    if not WEATHER_KEY: raise APIError('WeatherAPI is not configured in the local server.', 503)
    cachekey=(code,lang)
    with WEATHER_LOCK:
        entry=WEATHER_CACHE.get(cachekey)
        if entry and time.time()-entry[0]<WEATHER_TTL: return {**entry[1], 'cache':True}
    url='https://api.weatherapi.com/v1/current.json?'+urlencode({'key':WEATHER_KEY,'q':code,'aqi':'no','lang':lang})
    req=Request(url,headers={'Accept':'application/json','User-Agent':'Linguist-X-Demo/1.0'})
    try:
        with urlopen(req,timeout=12) as response: raw=response.read(150000)
    except HTTPError as exc:
        if exc.code in (400,404): raise APIError('Destination weather is unavailable for this airport.', 404) from None
        if exc.code in (401,403): raise APIError('WeatherAPI rejected the configured key.', 502) from None
        if exc.code==429: raise APIError('WeatherAPI rate limit reached.',429) from None
        raise APIError('WeatherAPI returned an error.',502) from None
    except (URLError,TimeoutError,OSError):
        raise APIError('Could not connect to WeatherAPI.',502) from None
    try: data=json.loads(raw)
    except (ValueError,UnicodeDecodeError): raise APIError('Unexpected WeatherAPI response.',502) from None
    current=data.get('current') if isinstance(data,dict) else None
    location=data.get('location') if isinstance(data,dict) else None
    if not isinstance(current,dict) or not isinstance(location,dict): raise APIError('WeatherAPI did not return current conditions.',502)
    condition=current.get('condition') or {}
    code_id=int(condition.get('code') or 0)
    scene=weather_scene(code_id)
    if not bool(current.get('is_day',1)): scene='night'
    try: temp=float(current.get('temp_c'))
    except (TypeError,ValueError):temp=None
    result={'source':'weatherapi','airport':code,'location':str(location.get('name') or '')[:80],
       'region':str(location.get('region') or '')[:80], 'condition':str(condition.get('text') or '')[:100],
       'code':code_id,'tempC':temp,'isDay':bool(current.get('is_day',1)),'scene':scene,
       'updated':str(current.get('last_updated') or '')[:40], 'cache':False}
    with WEATHER_LOCK: WEATHER_CACHE[cachekey]=(time.time(),result)
    return result



def api_request(url: str, *, params: dict) -> dict:
    """Perform a bounded HTTPS JSON request to a provider; this helper intentionally has no plaintext downgrade path."""
    full_url = f'{url}?{urlencode(params)}'
    req = Request(full_url, headers={'Accept': 'application/json', 'User-Agent': 'Linguist-X-Demo/1.0'})
    try:
        with urlopen(req, timeout=13) as response:
            blob = response.read(3_000_000)
    except HTTPError as exc:
        # Provider errors are parsed for a sanitized status; no HTTP downgrade.
        raw = exc.read(300_000)
        try:
            parsed_error = json.loads(raw)
            if isinstance(parsed_error, dict) and parsed_error.get('error'):
                return parsed_error
        except (ValueError, UnicodeDecodeError):
            pass
        raise APIError(f'Aviationstack returned HTTP {exc.code}', exc.code) from None
    except (URLError, TimeoutError, OSError):
        raise APIError('Could not reach Aviationstack. Check the connection and try again.', 502) from None
    try:
        value = json.loads(blob)
    except (ValueError, UnicodeDecodeError):
        raise APIError('The flight provider returned an unreadable response.', 502) from None
    if not isinstance(value, dict):
        raise APIError('Unexpected flight-provider response.', 502)
    return value


class APIError(Exception):
    """Sanitized application error carrying an HTTP status suitable for the browser-facing API boundary."""
    def __init__(self, message: str, status: int = 502):
        """Store only a sanitized client-facing message and intended HTTP status."""
        self.message = message
        self.status = status
        super().__init__(message)


def provider_data(query: str) -> dict:
    """Call Aviationstack for one flight code and return its provider payload after transport-level validation."""
    params = {'access_key': API_KEY, 'flight_iata': query, 'limit': 25}
    # Credentials must never be downgraded to plaintext HTTP.
    result = api_request('https://api.aviationstack.com/v1/flights', params=params)
    error = result.get('error')
    if error:
        # Provider error codes are safe; do not echo arbitrary text in case it contains a secret.
        code = str(error.get('code', 'provider_error')) if isinstance(error, dict) else 'provider_error'
        if code in ('rate_limit_reached', 'usage_limit_reached', 'monthly_limit_reached'):
            raise APIError('Monthly Aviationstack request allowance reached.', 429)
        if code in ('invalid_access_key', 'missing_access_key', 'user_inactive'):
            raise APIError('Flight provider rejected the configured access key.', 502)
        raise APIError('Flight provider could not complete the lookup (' + re.sub('[^a-zA-Z0-9_]', '', code)[:50] + ').', 502)
    return result


def normalize_flight(f: dict) -> dict | None:
    """Convert one provider flight record into the stable, minimal flight shape consumed by the passenger UI."""
    dep, arr, flight = f.get('departure') or {}, f.get('arrival') or {}, f.get('flight') or {}
    airline = f.get('airline') or {}
    iata = str(flight.get('iata') or '').upper().replace(' ', '')
    if not re.fullmatch(r'[A-Z0-9]{2,3}\d{1,5}[A-Z]?', iata):
        return None
    dep_iata = str(dep.get('iata') or '').upper()
    arr_iata = str(arr.get('iata') or '').upper()
    if not re.fullmatch(r'[A-Z]{3}', dep_iata) or not re.fullmatch(r'[A-Z]{3}', arr_iata):
        return None
    date = f.get('flight_date') if isinstance(f.get('flight_date'), str) else ''
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date):
        date = ''
    airline_iata = str(airline.get('iata') or '').upper()
    display_code = iata.replace(airline_iata, airline_iata + ' ', 1) if airline_iata and iata.startswith(airline_iata) else iata
    def date_time(value):
        """Parse a provider timestamp into an aware datetime when possible; malformed values remain nonfatal."""
        if not isinstance(value, str):
            return ''
        try:
            return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).strftime('%H:%M')
        except ValueError:
            return ''
    return {
        'id': '|'.join((iata, dep_iata, arr_iata, date)),
        'code': display_code, 'iata': iata,
        'airline': str(airline.get('name') or airline_iata or 'Airline')[:100],
        'dep': dep_iata, 'arr': arr_iata,
        'depAirport': str(dep.get('airport') or dep_iata)[:120],
        'arrAirport': str(arr.get('airport') or arr_iata)[:120],
        'date': date, 'status': str(f.get('flight_status') or 'unknown')[:30],
        'gate': str(dep.get('gate') or '').strip()[:20] or None,
        'terminal': str(dep.get('terminal') or '').strip()[:32] or None,
        'boarding': date_time(dep.get('estimated') or dep.get('scheduled')) or None,
        # Aviationstack does not report a boarding timestamp here. Do not relabel departure as boarding.
        'boardingTime': None,
        'scheduledDeparture': str(dep.get('scheduled') or '')[:40],
        'estimatedDeparture': str(dep.get('estimated') or '')[:40],
        'scheduledArrival': str(arr.get('scheduled') or '')[:40],
        'estimatedArrival': str(arr.get('estimated') or '')[:40],

    }



def departure_service_date(raw: dict) -> str:
    """Local departure date: provider flight_date first, scheduled departure fallback.

    Never infer a service date from a UTC arrival or the time of the API request.
    """
    date = raw.get('flight_date')
    if isinstance(date, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', date):
        try:
            dt.date.fromisoformat(date)
            return date
        except ValueError:
            pass
    dep = raw.get('departure') or {}
    scheduled = dep.get('scheduled')
    if isinstance(scheduled, str):
        try:
            return dt.datetime.fromisoformat(scheduled.replace('Z', '+00:00')).date().isoformat()
        except ValueError:
            pass
    return ''


def airport_today(raw: dict, fallback: dt.date, now_utc: dt.datetime) -> str:
    """Prefer origin-airport local date; fallback to device date if unresolvable."""
    dep = raw.get('departure') or {}
    zone = dep.get('timezone')
    if isinstance(zone, str) and zone:
        try:
            return now_utc.astimezone(ZoneInfo(zone)).date().isoformat()
        except (ZoneInfoNotFoundError, ValueError, KeyError):
            pass
    # When no IANA timezone exists, the scheduled departure's ISO offset gives
    # a useful airport-local approximation even around midnight.
    scheduled = dep.get('scheduled')
    if isinstance(scheduled, str):
        try:
            stamp = dt.datetime.fromisoformat(scheduled.replace('Z', '+00:00'))
            if stamp.utcoffset() is not None:
                return now_utc.astimezone(stamp.tzinfo).date().isoformat()
        except ValueError:
            pass
    return fallback.isoformat()


def only_todays_departures(raw_flights: list, requested_day: dt.date, now_utc: dt.datetime) -> list:
    """Filter by origin airport's calendar day, never by arrival or UTC day."""
    return [f for f in raw_flights if isinstance(f, dict)
            and departure_service_date(f)
            and departure_service_date(f) == airport_today(f, requested_day, now_utc)]


def lookup(query: str, *, refresh: bool = False, local_date: str = "") -> dict:
    """Validate a passenger flight query, reuse the short cache when allowed, fetch provider data, normalize it, and return only usable current departures."""
    if not API_KEY:
        raise APIError('The local flight proxy is missing its Aviationstack configuration.', 503)
    cleaned = re.sub(r'\s+', '', query.upper())
    if not re.fullmatch(r'[A-Z0-9]{2,3}\d{1,5}[A-Z]?', cleaned):
        raise APIError('Enter a flight number such as AA 100 or BA 178.', 400)
    # Date is supplied in the browser's local calendar, not UTC. Prefer the
    # departure airport's own timezone whenever Aviationstack supplies it.
    if local_date:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', local_date):
            raise APIError('Invalid local departure date.', 400)
        try:
            browser_day = dt.date.fromisoformat(local_date)
        except ValueError:
            raise APIError('Invalid local departure date.', 400) from None
    else:
        browser_day = dt.datetime.now().date()
    now = time.time()
    cache_key = cleaned + '|' + browser_day.isoformat()
    with LOCK:
        cached = CACHE.get(cache_key)
    # Even manual refresh uses 5-minute cache to protect the 100/month test quota.
    if cached and now - cached[0] < CACHE_SECONDS:
        return {**cached[1], 'cache': True}
    data = provider_data(cleaned)
    checked_now = dt.datetime.now(dt.timezone.utc)
    # Some flight numbers are reused on different days or even routes. Keep
    # today's departure only, for each record's departure-airport local day.
    raw = only_todays_departures(data.get('data', []), browser_day, checked_now)
    flights = [item for f in raw if (item := normalize_flight(f)) and item['iata'] == cleaned]
    # Avoid multiple records for duplicate upstream rows, but retain distinct
    # same-day routes: the user still needs to choose the correct journey.
    unique = list({f['id']: f for f in flights}.values())
    checked = checked_now.isoformat(timespec='seconds')
    payload = {'flights': unique[:25], 'checkedAt': checked, 'cache': False,
               'source': 'aviationstack', 'dateScope': 'departure-local',
               'requestedDate': browser_day.isoformat()}
    with LOCK:
        CACHE[cache_key] = (now, payload)
    return payload


def demo_audio(lang: str, announcement_id: str) -> bytes:
    """Generate or reuse sample announcement audio for Demo mode; cache key is deterministic and must not include passenger identity."""
    # Fixed 5 x 6 sample strings: never accept arbitrary user text from a request.
    if lang not in DEMO_MESSAGES or announcement_id not in DEMO_MESSAGES[lang]:
        raise APIError('Unknown sample announcement or language.', 400)
    if not OPENAI_KEY:
        raise APIError('OpenAI voice is not configured in the local server.', 503)
    content = DEMO_MESSAGES[lang][announcement_id]
    cache_identity = json.dumps([TTS_MODEL, TTS_VOICE, TTS_INSTRUCTIONS, lang, content], ensure_ascii=False)
    digest = hashlib.sha256(cache_identity.encode('utf-8')).hexdigest()
    target = AUDIO_CACHE / (digest + '.mp3')
    # A per-process lock prevents simultaneous listeners from purchasing duplicate generations.
    with AUDIO_LOCK:
        if target.exists() and target.stat().st_size > 128:
            return target.read_bytes()
        body = json.dumps({
            'model': TTS_MODEL, 'voice': TTS_VOICE, 'input': content,
            'instructions': TTS_INSTRUCTIONS, 'response_format': 'mp3'
        }, ensure_ascii=False).encode('utf-8')
        req = Request('https://api.openai.com/v1/audio/speech', data=body, headers={
            'Authorization': 'Bearer ' + OPENAI_KEY,
            'Content-Type': 'application/json', 'Accept': 'audio/mpeg',
            'User-Agent': 'Linguist-X-Demo/1.0'
        }, method='POST')
        try:
            with urlopen(req, timeout=55) as response:
                result = response.read(3_000_001)
                mimetype = response.headers.get('Content-Type', '')
        except HTTPError as exc:
            # Never echo OpenAI's response or request headers (which may contain sensitive data).
            if exc.code == 401:
                raise APIError('OpenAI rejected the configured API key.', 502) from None
            if exc.code == 429:
                raise APIError('OpenAI rate or spending limit reached.', 429) from None
            raise APIError(f'OpenAI audio service returned HTTP {exc.code}.', 502) from None
        except (URLError, TimeoutError, OSError):
            raise APIError('Could not reach OpenAI speech service.', 502) from None
        if len(result) < 128 or len(result) > 3_000_000 or 'audio' not in mimetype.lower():
            raise APIError('OpenAI returned unexpected audio data.', 502)
        # Atomic write. File survives server restart; identical request is never re-billed locally.
        with tempfile.NamedTemporaryFile(dir=AUDIO_CACHE, suffix='.tmp', delete=False) as temp:
            temp.write(result)
            temp_path = Path(temp.name)
        temp_path.replace(target)
        return result


def extract_flight_number_vision(image: str) -> dict:
    """Read ONE printed flight number from a cropped JPEG; never save or log the image."""
    if not OPENAI_KEY:
        raise APIError('OpenAI vision is not configured in the local server.', 503)
    if not isinstance(image, str) or not image.startswith('data:image/jpeg;base64,') or len(image) > 500_000:
        raise APIError('Expected a small cropped JPEG frame.', 400)
    try:
        binary = base64.b64decode(image.partition(',')[2], validate=True)
    except (ValueError, base64.binascii.Error):
        raise APIError('Invalid JPEG frame.', 400) from None
    if not (1000 <= len(binary) <= 350_000 and binary[:3] == b'\xff\xd8\xff'):
        raise APIError('Invalid JPEG frame size or format.', 400)
    instructions = (
        'You are a strict optical reader, not an itinerary planner. '
        'Inspect only VISIBLE printed characters in the photo. Look for ONE airline flight number: '
        'an IATA airline prefix (two alphanumeric characters, sometimes a three-letter ICAO prefix) '
        'plus 1–5 digits, optionally one trailing letter, e.g. DL 216, AF 718, BAW 178. '
        'A label such as FLIGHT / FLT / VOL / VUELO / VOO may help. '
        'Do NOT infer missing characters, guess from airports, or substitute a booking reference, date, seat, gate, terminal, or ticket number. '
        'If exactly one unambiguous flight number is readable, reply ONLY with its uppercase compact form, like DL216. '
        'If several different flight numbers are visible, reply MULTIPLE. '
        'If no flight number is confidently readable, reply NONE. '
        'No explanations or other text.'
    )
    payload = json.dumps({
        'model': VISION_MODEL,
        'instructions': instructions,
        'input': [{'role':'user','content':[
            {'type':'input_text','text':'Read the single printed flight number, if clearly visible.'},
            {'type':'input_image','image_url':image,'detail':'high'}
        ]}],
        'max_output_tokens':32,
        'store':False
    },ensure_ascii=False).encode('utf-8')
    request=Request('https://api.openai.com/v1/responses',data=payload,headers={
        'Authorization':'Bearer '+OPENAI_KEY,
        'Content-Type':'application/json',
        'Accept':'application/json',
        'User-Agent':'Linguist-X-Local/1.0'
    },method='POST')
    try:
        with urlopen(request,timeout=23) as response: result=json.loads(response.read(150_000))
    except HTTPError as exc:
        if exc.code == 401: raise APIError('OpenAI rejected the configured API key.',502) from None
        if exc.code == 429: raise APIError('OpenAI rate or spending limit reached.',429) from None
        raise APIError(f'OpenAI vision service returned HTTP {exc.code}.',502) from None
    except (URLError,TimeoutError,OSError):
        raise APIError('Could not connect to OpenAI vision.',502) from None
    except (ValueError,UnicodeDecodeError):
        raise APIError('OpenAI returned an unexpected vision response.',502) from None
    output=[]
    for item in result.get('output',[]):
        if item.get('type')=='message':
            output.extend(piece.get('text','') for piece in item.get('content',[]) if piece.get('type')=='output_text')
    text=''.join(output).strip().upper()
    # Hard validation prevents accidentally accepting extra tokens or metadata as a flight number.
    if re.fullmatch(r'[A-Z0-9]{2,3}[0-9]{1,5}[A-Z]?',text) and re.search('[A-Z]', text[:3]):
        return {'code':text}
    return {'code':None,'ambiguous':text=='MULTIPLE'}


# The API key and GPT-Live instructions stay on this local single-user server.
LIVE_MODEL = os.getenv('LX_LIVE_MODEL', 'gpt-live-1')
LIVE_REQUESTS: list[float] = []
LIVE_REQUEST_LOCK = threading.Lock()
LIVE_SUPPORTED_LANGUAGES = {'English', 'Français', 'Español', '中文', 'العربية', 'Português'}

def create_live_session(data: dict) -> dict:
    """Create the existing voice/session helper payload while keeping provider credentials server-side; this is separate from venue translation media."""
    if not OPENAI_KEY:
        raise APIError('OpenAI voice is not configured on the local server.', 503)
    sdp = data.get('sdp')
    if not isinstance(sdp, str) or not (100 < len(sdp) <= 50000) or not sdp.startswith('v=0'):
        raise APIError('A valid WebRTC offer is required.', 400)
    language = data.get('language', 'English')
    if language not in LIVE_SUPPORTED_LANGUAGES:
        raise APIError('Unsupported conversation language.', 400)
    announcement = data.get('announcementId')
    if announcement is not None and announcement not in DEMO_MESSAGES[language]:
        raise APIError('Unknown announcement.', 400)
    flight = data.get('flight') or {}
    if not isinstance(flight, dict):
        raise APIError('Invalid flight context.', 400)
    code = str(flight.get('code') or '').strip().upper()
    if not re.fullmatch(r'[A-Z0-9]{2,3} ?\d{1,5}[A-Z]?', code):
        raise APIError('Select a valid flight first.', 400)
    def field(key, limit=80):
        """Read one bounded text field from an external model response without trusting arbitrary output length."""
        return re.sub(r'[\x00-\x1f]', ' ', str(flight.get(key) or ''))[:limit].strip()
    # The selected flight was resolved in the app; these are snapshot values,
    # not an airport data feed. No answers may invent missing airline facts.
    context = {'flight': code, 'origin': field('dep', 8), 'destination': field('arr', 8),
               'destinationName': field('dest'), 'currentGate': field('gate', 12),
               'terminal': field('terminal'), 'status': field('status'),
               'departure': field('departure', 45), 'arrival': field('arrival', 45),
               'checkedAt': field('checkedAt', 45), 'source': field('source', 25)}
    note = DEMO_MESSAGES[language][announcement] if announcement else None
    instructions = (
        'You are Linguist-X, a concise, warm airport passenger voice guide. '
        'Speak ONLY in ' + language + ' unless the passenger explicitly asks to change languages. '
        'This is a PROTOTYPE: its rotating announcements are simulated, never a real airport broadcast. '
        'Use the supplied flight snapshot ONLY for flight details; it might be cached or stale. '
        'Do not assert an unprovided status, departure time, delay reason, gate or policy. '
        'If uncertain, say it has not been confirmed and direct the passenger to airline staff or airport displays. '
        'Never imply you can change a booking or that the microphone is always on. '
        'Do not greet unsolicitedly; wait for the passenger to speak. '
        'If asked to repeat an announcement, recite the supplied announcement exactly; never paraphrase its details. '
        'Keep responses short, direct, easy to follow in a busy airport. '
        'Selected flight snapshot: ' + json.dumps(context, ensure_ascii=False) + '. '
        + ('Selected sample announcement to discuss: ' + json.dumps(note, ensure_ascii=False) + '.' if note else
           'No announcement is selected; say so if asked to repeat an announcement.')
    )
    now=time.monotonic()
    with LIVE_REQUEST_LOCK:
        LIVE_REQUESTS[:] = [t for t in LIVE_REQUESTS if now-t < 3600]
        if len(LIVE_REQUESTS) >= 60:
            raise APIError('Voice session limit reached for this local prototype.',429)
        LIVE_REQUESTS.append(now)
    payload=json.dumps({'session': {'model': LIVE_MODEL, 'instructions': instructions,
                                    'audio': {'output': {'voice': 'coral'}}},
                        'transport': {'type':'webrtc','sdp':sdp}},ensure_ascii=False).encode('utf-8')
    req=Request('https://api.openai.com/v1/live/sessions', data=payload,
        headers={'Authorization':'Bearer '+OPENAI_KEY,'Content-Type':'application/json',
                 'Accept':'application/json','User-Agent':'Linguist-X-Local/1.0'}, method='POST')
    try:
        with urlopen(req, timeout=35) as result:
            answer=json.loads(result.read(180000))
    except HTTPError as exc:
        if exc.code in (401,403): raise APIError('OpenAI rejected the key or GPT-Live access.',502) from None
        if exc.code==429: raise APIError('OpenAI voice rate or spending limit reached.',429) from None
        raise APIError(f'GPT-Live session returned HTTP {exc.code}.',502) from None
    except (URLError,TimeoutError,OSError):
        raise APIError('Could not connect to GPT-Live.',502) from None
    except (ValueError,UnicodeDecodeError):
        raise APIError('GPT-Live returned an unexpected response.',502) from None
    transport=answer.get('transport') or {}
    session=answer.get('session') or {}
    if transport.get('type')!='webrtc' or not isinstance(transport.get('sdp'),str) or not transport['sdp']:
        raise APIError('GPT-Live did not return a WebRTC answer.',502)
    return {'session': {'id':str(session.get('id') or '')}, 'transport': {'type':'webrtc','sdp':transport['sdp']}}

# v58: quality-gated airline identity. Trusted local SVGs and a curated verified
# vector upstream take priority; remote PNGs must meet a minimum raster size.
# An absent/undersized logo returns 404, preserving the airline name in the UI.
AIRLINE_CACHE = HERE / '.airline-cache'
AIRLINE_CATALOG_URL = 'https://raw.githubusercontent.com/imgmongelli/airlines-logos-dataset/master/airlines.json'
AIRLINE_LOGO_BASE = 'https://raw.githubusercontent.com/imgmongelli/airlines-logos-dataset/master/images/'
AIRLINE_FALLBACK_BASE = 'https://cdn.jsdelivr.net/gh/spydogenesis/airlines-logo@main/airlines-logo/200x200_v2/'
# Wikimedia-hosted vector replaces the known low-resolution Emirates catalog mark.
# Add vetted carrier vectors under airlines/custom/XX.svg for other carriers.
AIRLINE_VECTOR_SOURCES = {
    'EK': 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Emirates_Logo.svg',
}
# v61: checked-in seed keeps major IATA→ICAO mappings available even when
# the external catalog is offline. SVG candidates are curated by airline code,
# then quality-validated and cached on first request. Full remote coverage is
# opportunistic; the app never invents a logo for an unknown carrier.
AIRLINE_LIBRARY = json.loads((HERE/'airlines'/'library.json').read_text(encoding='utf-8'))
AIRLINE_SEED = {key:value['icao'] for key,value in AIRLINE_LIBRARY['seed'].items()}
AIRLINE_REVERSE_SEED = {icao:iata for iata,icao in AIRLINE_SEED.items()}
AIRLINE_VECTOR_FALLBACK = {
    key: ('https://raw.githubusercontent.com/soaring-symbols/soaring-symbols/main/assets/'+slug+'/logo.svg',
          'https://raw.githubusercontent.com/soaring-symbols/soaring-symbols/main/assets/'+slug+'/icon.svg')
    for key,slug in AIRLINE_LIBRARY['svg_candidates'].items() if key != 'AA'
}
# Extra source if the locally bundled AA image is accidentally removed. No untrusted URL input.
AIRLINE_VECTOR_FALLBACK['AA']=('https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/americanairlines.svg',)
# Reuse negative resolution results rather than issuing repeated upstream attempts on re-renders.
AIRLINE_MISSES: dict[str,float]={}
AIRLINE_MISS_LOCK=threading.Lock()
_airline_catalog_lock = threading.Lock()
_airline_catalog = None

def _bounded_download(url: str, max_bytes: int, timeout=7) -> bytes:
    """Download a remote asset with strict byte and timeout limits so logo discovery cannot become an unbounded proxy."""
    request = Request(url, headers={'User-Agent':'Linguist-X-Airline-Identity/1.1', 'Accept':'image/svg+xml,image/png,application/json;q=0.9,*/*;q=0.4'})
    with urlopen(request, timeout=timeout) as response:
        if int(response.status) != 200: raise ValueError('Logo source unavailable')
        result = response.read(max_bytes + 1)
        if len(result) > max_bytes: raise ValueError('Logo source too large')
        return result

def _get_airline_catalog() -> dict[str,str]:
    """Resolve and cache the external airline-code catalog used only as a logo-discovery aid, falling back safely when unavailable."""
    global _airline_catalog
    with _airline_catalog_lock:
        if _airline_catalog is not None: return _airline_catalog
        file= AIRLINE_CACHE / 'catalog.json'
        data=None
        if file.is_file():
            try:
                if file.stat().st_size < 800_000:
                    data=json.loads(file.read_text(encoding='utf-8'))
            except (OSError,UnicodeError,ValueError): data=None
        if not isinstance(data,dict) or not isinstance(data.get('data'),list):
            try:
                payload=_bounded_download(AIRLINE_CATALOG_URL, 800_000, timeout=8)
                data=json.loads(payload)
                if not isinstance(data.get('data'),list):raise ValueError('Invalid catalog')
                AIRLINE_CACHE.mkdir(parents=True,exist_ok=True)
                file.write_bytes(payload)
            except (OSError,ValueError,URLError,HTTPError,TimeoutError):
                data={'data':[]}
        mapping=dict(AIRLINE_SEED)
        for record in data['data']:
            if not isinstance(record,dict):continue
            iata=str(record.get('iata_code') or '').upper()
            icao=str(record.get('icao_code') or '').upper()
            logo=str(record.get('logo') or '')
            if re.fullmatch(r'[A-Z0-9]{2,3}',iata) and re.fullmatch(r'[A-Z0-9]{3}',icao) and logo=='./images/'+icao+'.png':
                mapping.setdefault(iata,icao)
        _airline_catalog=mapping
        return mapping

def _clean_svg(body: bytes) -> bytes | None:
    """Reject unsafe/oversized SVG content and return only artwork suitable for same-origin rendering."""
    # Reject active, linked or embedded content before sending external SVG to browser.
    if not 80 < len(body) < 180_000:return None
    try: text=body.decode('utf-8-sig')
    except UnicodeDecodeError:return None
    if not re.search(r'<svg(?:\s|>)',text,re.I):return None
    if re.search(r'<(?:script|foreignObject|image|iframe|video|audio|animate|set)(?:\s|>)',text,re.I):return None
    if re.search(r'\bon\w+\s*=|\b(?:href|xlink:href)\s*=\s*[\"\'](?!#)|@import',text,re.I):return None
    for match in re.finditer(r'url\s*\(([^)]*)\)',text,re.I):
        if not match.group(1).strip().strip('\"\'').startswith('#'):return None
    # Ensure XML is well formed. Ordinary vector paths and internal #id uses remain valid.
    try:
        import xml.etree.ElementTree as ET
        root=ET.fromstring(text)
        if root.tag.split('}')[-1].lower()!='svg':return None
    except (ValueError,ET.ParseError):return None
    return body

def _usable_png(body: bytes) -> bool:
    """Apply lightweight validation to candidate raster logos before they can be served or cached."""
    if not 80<len(body)<=1_500_000 or not body.startswith(b'\x89PNG\r\n\x1a\n'):return False
    if body[12:16]!=b'IHDR':return False
    width,height=int.from_bytes(body[16:20],'big'),int.from_bytes(body[20:24],'big')
    # At the rendered 60px high, 180px source height covers a 3x phone; width
    # needs room for wide marks. Remaining transparent-padding quality is
    # checked in the browser using the visible-alpha bounding box.
    return width>=180 and height>=180 and width<=4000 and height<=4000

def airline_logo(code: str) -> tuple[bytes,str] | None:
    """Resolve a carrier mark from bundled, cached, curated-vector, or bounded remote sources in that order."""
    code=code.strip().upper()
    if not re.fullmatch(r'[A-Z0-9]{2,3}',code):return None
    # Flight feeds may supply an ICAO code (KAL) rather than the IATA code (KE).
    # Normalize known carrier aliases before selecting the on-device identity.
    if len(code)==3:code=AIRLINE_REVERSE_SEED.get(code,code)  # Tested alias: AAL -> AA; DAL -> DL; KAL -> KE
    customdir=HERE/'airlines'/'custom'
    custom_svg=customdir/(code+'.svg')
    if custom_svg.is_file():
        try:
            svg=_clean_svg(custom_svg.read_bytes())
            if svg:return svg,'image/svg+xml'
        except OSError:pass
    custom_png=customdir/(code+'.png')
    if custom_png.is_file():
        try:
            body=custom_png.read_bytes()
            if _usable_png(body):return body,'image/png'
        except OSError:pass
    vector_cache=AIRLINE_CACHE/(code+'.svg')
    if vector_cache.is_file():
        try:
            svg=_clean_svg(vector_cache.read_bytes())
            if svg:return svg,'image/svg+xml'
        except OSError:pass
    # Keep already bundled/cached marks accessible, even during a transient outage.
    # Throttle remote failures; the app continues with its neutral code identity.
    with AIRLINE_MISS_LOCK:
        if time.monotonic() < AIRLINE_MISSES.get(code,0):return None
    # Only a fixed whitelist of known vectors may be fetched; no user URL input.
    vector_url=AIRLINE_VECTOR_SOURCES.get(code)
    if vector_url:
        try:
            svg=_clean_svg(_bounded_download(vector_url,180_000))
            if svg:
                AIRLINE_CACHE.mkdir(parents=True,exist_ok=True)
                vector_cache.write_bytes(svg)
                return svg,'image/svg+xml'
        except (OSError,URLError,HTTPError,ValueError,TimeoutError):pass
    for vector_source in AIRLINE_VECTOR_FALLBACK.get(code,()):
        try:
            svg=_clean_svg(_bounded_download(vector_source,180_000,timeout=4))
            if svg:
                AIRLINE_CACHE.mkdir(parents=True,exist_ok=True)
                vector_cache.write_bytes(svg)
                return svg,'image/svg+xml'
        except (OSError,URLError,HTTPError,ValueError,TimeoutError):continue
    target=AIRLINE_CACHE/(code+'.png')
    if target.is_file():
        try:
            body=target.read_bytes()
            if _usable_png(body):return body,'image/png'
        except OSError:pass
    icao=code if len(code)==3 else _get_airline_catalog().get(code)
    candidates=[]
    if icao:candidates.append(AIRLINE_LOGO_BASE+icao+'.png')
    candidates.append(AIRLINE_FALLBACK_BASE+code+'.png')
    for url in candidates:
        try:
            body=_bounded_download(url,1_500_000)
            if not _usable_png(body):continue
            AIRLINE_CACHE.mkdir(parents=True,exist_ok=True)
            target.write_bytes(body)
            return body,'image/png'
        except (OSError,URLError,HTTPError,ValueError,TimeoutError):continue
    with AIRLINE_MISS_LOCK:AIRLINE_MISSES[code]=time.monotonic()+30
    return None

class Handler(BaseHTTPRequestHandler):
    """Local-development HTTP boundary. Keep its application semantics aligned with passenger_asgi.py; never expose this server as production."""
    # Normal cancellations (navigation/reload) must not flood the terminal.
    def handle(self):
        """Wrap BaseHTTPRequestHandler processing so broken clients do not turn expected disconnects into noisy tracebacks."""
        try: super().handle()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError): pass

    def _same_origin(self):
        """Allow same-origin browser mutations; local development may omit Origin, but cross-origin POSTs are rejected."""
        origin=self.headers.get('Origin','')
        host=self.headers.get('Host','')
        return not origin or origin in ('http://'+host,'https://'+host)

    def _json_body(self,maximum=2048):
        """Read a bounded JSON request body and require an object payload before any mutation endpoint runs."""
        if self.headers.get('Content-Type','').split(';')[0].strip().lower()!='application/json':
            raise GatewayError('Expected JSON.',415)
        try:size=int(self.headers.get('Content-Length','0'))
        except ValueError:size=0
        if not 0<size<=maximum:raise GatewayError('Invalid request size.',413)
        try:parsed=json.loads(self.rfile.read(size))
        except (ValueError,UnicodeError):raise GatewayError('Invalid JSON.',400) from None
        if not isinstance(parsed,dict):raise GatewayError('Expected object.',400)
        return parsed

    def _guest_cookie(self):
        """Read only the opaque browser guest handle; the upstream guest token is never stored in browser cookies."""
        jar=SimpleCookie()
        try:jar.load(self.headers.get('Cookie',''))
        except Exception:return ''
        val=jar.get('lx_guest')
        return val.value if val else ''


    def log_message(self, format, *args):
        """Suppress default access logging because URLs and query strings may contain operational context that is not needed in logs."""
        # No URL logging. On this local-only demo no requests are logged at all.
        return

    def send_response(self, code, message=None):
        """Attach baseline security headers to every local-server response before endpoint-specific headers are added."""
        super().send_response(code, message)
        for name, value in response_headers(SETTINGS.production).items():
            self.send_header(name, value)
        if code >= 400 and self.path.startswith('/api/'):
            audit('api_request_denied', status=code)

    def json_response(self, status: int, data: dict):
        """Serialize a bounded application JSON response with no-store semantics for API data."""
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        """Route local browser mutations: developer controls, guest join/leave, live-session helper, and optional printed-flight vision."""
        path=urlsplit(self.path).path
        if path in ('/api/dev/mode','/api/dev/fixture','/api/integration/join','/api/integration/leave'):
            if SETTINGS.production and path.startswith('/api/dev/'):
                self.json_response(404,{'error':'Unknown endpoint.'});return
            try:
                if not self._same_origin():raise GatewayError('Unexpected request origin.',403)
                if path=='/api/dev/mode':
                    # Host binding alone is insufficient; only local owner can change a global test mode.
                    if self.client_address[0] not in ('127.0.0.1','::1'):
                        raise GatewayError('Use the loopback-only local server to change test mode.',403)
                    data=self._json_body()
                    self.json_response(200,GATEWAY.set_mode(data.get('mode')))
                    return
                if path=='/api/dev/fixture':
                    if self.client_address[0] not in ('127.0.0.1','::1') or FIXTURE is None:
                        raise GatewayError('Fixture not enabled for this local owner.',403)
                    self.json_response(200,FIXTURE.set_scenario(self._json_body().get('scenario')))
                    return
                if path=='/api/integration/leave':
                    self._json_body();GATEWAY.clear_guest(self._guest_cookie())
                    self.send_response(204);self.send_header('Set-Cookie',guest_cookie('', production=SETTINGS.production))
                    self.send_header('Content-Length','0');self.send_header('Cache-Control','no-store');self.end_headers();return
                data=self._json_body()
                # A failed replacement join may never leave an earlier authorized grant active.
                GATEWAY.clear_guest(self._guest_cookie())
                handle,result=GATEWAY.join(data.get('sessionId'),data.get('language'),data.get('inviteCode'))
                body=json.dumps(result,ensure_ascii=False).encode('utf-8')
                self.send_response(201);self.send_header('Content-Type','application/json; charset=utf-8')
                self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
                self.send_header('X-Content-Type-Options','nosniff')
                self.send_header('Set-Cookie',guest_cookie(handle, max_age=result['expiresIn'], production=SETTINGS.production))
                self.end_headers();self.wfile.write(body)
            except GatewayError as exc:
                if path=='/api/integration/join':
                    # Clear the browser handle even on denied joins.
                    blob=json.dumps({'error':exc.message}).encode('utf-8')
                    self.send_response(exc.status);self.send_header('Content-Type','application/json; charset=utf-8')
                    self.send_header('Content-Length',str(len(blob)));self.send_header('Cache-Control','no-store')
                    self.send_header('Set-Cookie',guest_cookie('', production=SETTINGS.production))
                    self.end_headers();self.wfile.write(blob)
                else:self.json_response(exc.status,{'error':exc.message})
            return
        if path == '/api/live/session':
            # Browser sends SDP to this server; the project API key is never returned.
            origin=self.headers.get('Origin','')
            host=self.headers.get('Host','')
            if origin and origin not in ('http://'+host,'https://'+host):
                self.json_response(403,{'error':'Unexpected request origin.'});return
            if self.headers.get('Content-Type','').split(';')[0].strip().lower()!='application/json':
                self.json_response(415,{'error':'Expected JSON.'});return
            try: size=int(self.headers.get('Content-Length','0'))
            except ValueError: size=0
            if not 0<size<=65536:
                self.json_response(413,{'error':'Invalid voice request size.'});return
            try:
                request_data=json.loads(self.rfile.read(size))
                if not isinstance(request_data,dict): raise ValueError('body')
                self.json_response(201,create_live_session(request_data))
            except (ValueError,UnicodeDecodeError): self.json_response(400,{'error':'Invalid voice request.'})
            except APIError as exc: self.json_response(exc.status,{'error':exc.message})
            return
        if urlsplit(self.path).path != '/api/flight-number-vision':
            self.json_response(404,{'error':'Unknown endpoint.'});return
        if self.headers.get('Content-Type','').split(';')[0].strip().lower() != 'application/json':
            self.json_response(415,{'error':'Expected JSON.'});return
        try:
            size=int(self.headers.get('Content-Length','0'))
        except ValueError:
            self.json_response(400,{'error':'Invalid payload length.'});return
        if not (0 < size <= 550_000):
            self.json_response(413,{'error':'Image payload exceeds size limit.'});return
        try:
            data=json.loads(self.rfile.read(size))
            if not isinstance(data,dict): raise ValueError('body')
            self.json_response(200,extract_flight_number_vision(data.get('image')))
        except (ValueError,UnicodeDecodeError):
            self.json_response(400,{'error':'Invalid image request.'})
        except APIError as exc:
            self.json_response(exc.status,{'error':exc.message})

    def do_GET(self):
        """Route local read APIs and explicitly whitelisted static assets; unknown paths fail closed with 404."""
        parsed = urlsplit(self.path)
        if parsed.path == '/api/dev/status':
            if SETTINGS.production:self.json_response(404,{'error':'Unknown endpoint.'});return
            self.json_response(200,GATEWAY.snapshot());return
        if parsed.path == '/api/integration/health':
            self.json_response(200,GATEWAY.health());return
        if parsed.path == '/api/integration/sessions':
            try:
                flight=(parse_qs(parsed.query).get('flight') or [''])[0]
                self.json_response(200,GATEWAY.sessions(flight))
            except GatewayError as exc:self.json_response(exc.status,{'error':exc.message})
            return
        if parsed.path == '/api/dev/fixture':
            if SETTINGS.production:self.json_response(404,{'error':'Unknown endpoint.'});return
            if self.client_address[0] not in ('127.0.0.1','::1') or FIXTURE is None:
                self.json_response(403,{'error':'Local test fixture is not enabled.'});return
            self.json_response(200,{'enabled':True,'scenario':FIXTURE.scenario,'scenarios':SCENARIOS,'source':'test-fixture'});return
        if parsed.path == '/api/integration/invite':
            try:
                code=(parse_qs(parsed.query).get('code') or [''])[0]
                self.json_response(200,GATEWAY.resolve_invite(code))
            except GatewayError as exc:self.json_response(exc.status,{'error':exc.message})
            return
        if parsed.path == '/api/integration/events':
            try:
                after=int((parse_qs(parsed.query).get('after') or ['0'])[0])
                self.json_response(200,GATEWAY.events(self._guest_cookie(),after))
            except (ValueError,TypeError):self.json_response(400,{'error':'Invalid cursor.'})
            except GatewayError as exc:self.json_response(exc.status,{'error':exc.message})
            return
        if parsed.path == '/api/integration/state':
            try:self.json_response(200,GATEWAY.state(self._guest_cookie()))
            except GatewayError as exc:self.json_response(exc.status,{'error':exc.message})
            return
        if parsed.path == '/api/status':
            self.json_response(200, {'flightConfigured':bool(API_KEY),'voiceConfigured':bool(OPENAI_KEY),'liveVoiceConfigured':bool(OPENAI_KEY),'visionConfigured':bool(OPENAI_KEY),'engine':'gpt-4o-mini-tts','weatherConfigured':bool(WEATHER_KEY)})
            return
        if parsed.path == '/api/demo-audio':
            args = parse_qs(parsed.query)
            try:
                lang = (args.get('lang') or [''])[0]
                announcement_id = (args.get('id') or [''])[0]
                result = demo_audio(lang, announcement_id)
            except APIError as exc:
                self.json_response(exc.status, {'error': exc.message})
                return
            self.send_response(200)
            self.send_header('Content-Type', 'audio/mpeg')
            self.send_header('Content-Length', str(len(result)))
            self.send_header('Cache-Control', 'private, max-age=3600')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(result)
            return
        if parsed.path == '/api/airline-library':
            bundled=sorted(p.stem for p in (HERE/'airlines'/'custom').glob('*.svg'))
            cached=sorted(p.stem for p in AIRLINE_CACHE.glob('*.svg')) if AIRLINE_CACHE.exists() else []
            self.json_response(200,{'bundled_vectors':bundled,'cached_vectors':cached,
                'vector_candidates':AIRLINE_LIBRARY['svg_candidates'],
                'seed_catalog':AIRLINE_LIBRARY['seed'],
                'remote_catalog_eligible':len(_get_airline_catalog()),
                'note':AIRLINE_LIBRARY['note']})
            return
        if parsed.path == '/api/airline-logo':
            args=parse_qs(parsed.query)
            code=(args.get('code') or [''])[0]
            if not re.fullmatch(r'[A-Za-z0-9]{2,3}',code):
                self.send_error(400, 'Invalid airline code');return
            result=airline_logo(code)
            if result is None:
                self.send_response(404)
                self.send_header('Cache-Control','no-store')
                self.send_header('Content-Length','0')
                self.end_headers()
                return
            asset,mime=result
            self.send_response(200)
            self.send_header('Content-Type',mime)
            self.send_header('Content-Length',str(len(asset)))
            self.send_header('Cache-Control','public, max-age=3600')
            self.send_header('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'")
            self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers()
            self.wfile.write(asset)
            return
        if parsed.path == '/api/weather':
            args=parse_qs(parsed.query)
            try:
                q=(args.get('q') or [''])[0]
                lang=(args.get('lang') or ['en'])[0]
                self.json_response(200,destination_weather(q,lang))
            except APIError as exc: self.json_response(exc.status,{'error':exc.message})
            return
        if parsed.path == '/api/flights':
            args = parse_qs(parsed.query)
            try:
                q = (args.get('q') or [''])[0]
                self.json_response(200, lookup(q, refresh=(args.get('refresh') or [''])[0] == '1', local_date=(args.get('date') or [''])[0]))
            except APIError as exc:
                self.json_response(exc.status, {'error': exc.message})
            return
        # Static, explicitly whitelisted local vectors for the service-worker shell.
        # This is separate from /api/airline-logo, which may retrieve remote marks.
        if parsed.path.startswith('/airlines/custom/'):
            name=parsed.path.removeprefix('/airlines/custom/')
            if not re.fullmatch(r'[A-Z0-9]{2,3}\.svg',name):
                self.send_error(404);return
            asset_path=HERE/'airlines'/'custom'/name
            if not asset_path.is_file():
                self.send_error(404);return
            asset=_clean_svg(asset_path.read_bytes())
            if asset is None:
                self.send_error(404);return
            self.send_response(200)
            self.send_header('Content-Type','image/svg+xml')
            self.send_header('Content-Length',str(len(asset)))
            self.send_header('Cache-Control','public, max-age=86400')
            self.send_header('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'")
            self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers()
            self.wfile.write(asset)
            return
        static_files = {
            '/manifest.webmanifest': ('manifest.webmanifest', 'application/manifest+json'),
            '/sw.js': ('sw.js', 'application/javascript; charset=utf-8'),
            '/wayfinder.css': ('wayfinder.css', 'text/css; charset=utf-8'),
            '/wayfinder.js': ('wayfinder.js', 'application/javascript; charset=utf-8'),
            '/icon-192.png': ('icon-192.png', 'image/png'),
            '/icon-512.png': ('icon-512.png', 'image/png'),
            '/icon-180.png': ('icon-180.png', 'image/png'),
            '/living-orb.webp': ('living-orb.webp', 'image/webp'),
            '/wordly-wordmark.png': ('wordly-wordmark.png', 'image/png'),
            '/linguist-x-mark-v54.png': ('linguist-x-mark-v54.png', 'image/png'),
            '/icon-180-v54.png': ('icon-180-v54.png', 'image/png'),
            '/icon-192-v54.png': ('icon-192-v54.png', 'image/png'),
            '/icon-512-v54.png': ('icon-512-v54.png', 'image/png'),
        }
        if parsed.path.startswith('/weather/'):
            name=parsed.path.removeprefix('/weather/')
            if not re.fullmatch(r'(clear|partly|cloudy|mist|rain|showers|drizzle|sleet|snow|storm|night|wind)\.(png|webp)',name):
                self.send_error(404);return
            asset_path=HERE/'weather'/name
            if not asset_path.is_file():
                self.send_error(404);return
            asset=asset_path.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type','image/png' if name.endswith('.png') else 'image/webp')
            self.send_header('Content-Length',str(len(asset)))
            self.send_header('Cache-Control','public, max-age=86400')
            self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers()
            self.wfile.write(asset)
            return
        if parsed.path in static_files:
            filename, mime = static_files[parsed.path]
            asset = (HERE / filename).read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(asset)))
            self.send_header('Cache-Control', 'no-cache' if parsed.path == '/sw.js' else 'public, max-age=3600')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(asset)
            return
        if parsed.path == '/app-logo.png':
            asset = (HERE / 'app-logo.png').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'image/png')
            self.send_header('Content-Length', str(len(asset)))
            self.send_header('Cache-Control', 'public, max-age=86400')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(asset)
            return
        if parsed.path not in ('/', '/index.html', '/passenger-only.html', '/developer-documentation.html'):
            self.send_error(404)
            return
        # Internal documentation is deliberately served only by development runtimes; run.py cannot run in production.
        filename = ('developer-documentation.html' if parsed.path == '/developer-documentation.html'
                    else 'passenger-only.html' if parsed.path == '/passenger-only.html' else 'index.html')
        content = (HERE / filename).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(content)


if __name__ == '__main__':
    host = '0.0.0.0' if os.getenv('LX_LAN') == '1' else '127.0.0.1'
    if SETTINGS.production:
        raise SystemExit('Use the passenger_asgi:app entrypoint in production; run.py is local-only.')
    if FIXTURE is not None:
        FIXTURE_SERVER=start_fixture(0,FIXTURE)
        fixture_port=FIXTURE_SERVER.server_address[1]
        GATEWAY.base=f'http://127.0.0.1:{fixture_port}'
        print('Explicit local TEST FIXTURE enabled on loopback:ephemeral-port; NOT live Wordly.',flush=True)
    server = ThreadingHTTPServer((host, PORT), Handler)
    print(f'Linguist-X testing app: http://127.0.0.1:{PORT}')
    print('Aviationstack: '+('configured' if API_KEY else 'MISSING')+' | OpenAI sample voice: '+('configured' if OPENAI_KEY else 'MISSING')+' | WeatherAPI: '+('configured' if WEATHER_KEY else 'MISSING'))
    if not API_KEY or not OPENAI_KEY or not WEATHER_KEY: print('To configure a missing service, use python3 start.py --configure once; it is retained across upgrades.')
    if host == '0.0.0.0': print('LAN mode enabled: open http://YOUR_MAC_IP:'+str(PORT)+' on your phone, same Wi-Fi.')
    print('Translation integration: '+('gateway configured' if GATEWAY.configured() else 'no gateway configured')+' | starts in DEMO mode.')
    print('Flight lookups are cached 5 minutes. OpenAI sample voices are cached permanently per text, language, model and voice.')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if FIXTURE_SERVER is not None:FIXTURE_SERVER.shutdown();FIXTURE_SERVER.server_close()
