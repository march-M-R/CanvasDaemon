"""Shared V1 utilities; retain the existing individual script entrypoints."""
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlparse, urljoin, unquote

import requests as _requests
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def load_dotenv():
    """Read only this checkout's .env; explicit shell variables take precedence."""
    for key, value in dotenv_values(ROOT / '.env', interpolate=False).items():
        if value is not None:
            os.environ.setdefault(key, value)


def validate_config(base, token, course):
    p = urlparse(base)
    if (p.scheme != 'https' or not p.hostname or p.path or p.query or p.fragment or p.username or p.password):
        raise ValueError('CANVAS_BASE_URL must be an HTTPS origin without a path.')
    if not token or not str(course or '').isdigit() or int(course) < 1:
        raise ValueError('Set CANVAS_TOKEN and a positive COURSE_ID in .env or the shell.')


def bound(data, base, course):
    if str(data.get('course_id')) != str(course) or data.get('base_url', '').rstrip('/') != base.rstrip('/'):
        raise ValueError('Local manifest/config belongs to another course. Pull fresh data in a separate checkout.')
    return data


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path)


def body_hash(body):
    return hashlib.sha256(body.encode('utf-8')).hexdigest()


def add_write_flags(parser):
    parser.add_argument('--apply', action='store_true', help='Apply the planned Canvas change; default is dry-run')
    parser.add_argument('--confirm-course', help='Required with --apply; must equal COURSE_ID')


def authorize(args, base, course):
    print(f'Target: {base}/courses/{course}')
    if not args.apply:
        print(f'DRY RUN: add --apply --confirm-course {course} to write to Canvas.')
        return False
    if args.confirm_course != str(course):
        raise ValueError('--confirm-course must match COURSE_ID.')
    return True


class Requests:
    RequestException = _requests.RequestException
    HTTPError = _requests.HTTPError

    @staticmethod
    def request(method, url, **kwargs):
        p = urlparse(url)
        if p.scheme != 'https' or not p.hostname or p.username or p.password:
            raise ValueError('Refusing a non-HTTPS or credential-bearing URL.')
        headers = kwargs.get('headers') or {}
        if any(k.lower() == 'authorization' for k in headers):
            origin = urlparse(os.environ.get('CANVAS_BASE_URL', '').rstrip('/'))
            if (p.scheme, p.netloc) != (origin.scheme, origin.netloc):
                raise ValueError('Refusing to send a Canvas token to another origin.')
            segments = unquote(p.path).split('/')
            if '..' in segments or '.' in segments or '\\' in unquote(p.path):
                raise ValueError('Refusing an ambiguous authenticated path.')
            if p.path.startswith('/api/v1/courses/'):
                requested_course = p.path.split('/')[4]
                if requested_course != os.environ.get('COURSE_ID'):
                    raise ValueError('Refusing an authenticated request to another course.')
            kwargs['allow_redirects'] = False
        kwargs.setdefault('timeout', (10, 60))
        kwargs.setdefault('allow_redirects', False)
        return _requests.request(method, url, **kwargs)

    def get(self, url, **kwargs): return self.request('GET', url, **kwargs)
    def post(self, url, **kwargs): return self.request('POST', url, **kwargs)
    def put(self, url, **kwargs): return self.request('PUT', url, **kwargs)
    def delete(self, url, **kwargs): return self.request('DELETE', url, **kwargs)


requests = Requests()


def upload_binary(path, info, base, headers, canvas_name=None):
    """Send the signed multipart request without auth; scope callback auth to Canvas."""
    import mimetypes
    import re
    with path.open('rb') as stream:
        response = requests.post(info['upload_url'], data=info['upload_params'],
            files={'file': (canvas_name or path.name, stream, mimetypes.guess_type(path.name)[0] or 'application/octet-stream')})
    if response.status_code in (301, 302, 303, 307, 308) or (response.status_code == 201 and response.headers.get('Location')):
        callback = urljoin(base, response.headers.get('Location', ''))
        parsed = urlparse(callback)
        if (parsed.netloc != urlparse(base).netloc or parsed.scheme != 'https'
                or not re.fullmatch(r'/api/v1/files/\d+(?:/create_success)?', parsed.path)):
            raise ValueError('Unexpected upload callback; inspect Canvas before retrying.')
        response = requests.get(callback, headers=headers)
    response.raise_for_status()
    if not 200 <= response.status_code < 300:
        raise RuntimeError('Upload did not complete; inspect Canvas before retrying.')
    try:
        return response.json()
    except ValueError:
        raise RuntimeError('Upload outcome uncertain; inspect Canvas Files before retrying.') from None


def download(url, headers):
    """Follow download redirects explicitly, without forwarding tokens off-origin."""
    origin = urlparse(os.environ.get('CANVAS_BASE_URL', ''))
    for _ in range(6):
        parsed = urlparse(url)
        auth = headers if (parsed.scheme, parsed.netloc) == (origin.scheme, origin.netloc) else {}
        response = requests.get(url, headers=auth)
        if response.status_code in (301, 302, 303, 307, 308):
            url = urljoin(url, response.headers['Location'])
            continue
        response.raise_for_status()
        return response.content
    raise RuntimeError('Too many download redirects.')
