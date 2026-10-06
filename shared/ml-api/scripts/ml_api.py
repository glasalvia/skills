#!/usr/bin/env python3
"""
MercadoLibre API client library.
Reads credentials from workspace/secrets/mercado_libre_token.txt.
"""
import os, json, urllib.request, urllib.parse

# Resolve secrets file path relative to workspace
_HOME_DIR = os.path.expanduser('~')
WORKSPACE_SECRETS = os.path.join(_HOME_DIR, '.openclaw', 'workspace', 'secrets', 'mercado_libre_token.txt')
# Fallback: when script is inside workspace/skills/<skill>/scripts/
_SKILL_DIR = os.path.dirname(os.path.dirname(__file__))
SKILL_REL_SECRETS = os.path.join(_SKILL_DIR, '..', '..', 'secrets', 'mercado_libre_token.txt')

def read_credentials():
    """Read ML_APP_ID and CLIENT_SECRET from secrets file.
    Returns (app_id, client_secret) tuple."""
    for path in [WORKSPACE_SECRETS, SKILL_REL_SECRETS]:
        if os.path.exists(path):
            with open(path) as f:
                creds = {}
                for line in f:
                    line = line.strip()
                    if ':' in line:
                        k, v = line.split(':', 1)
                        creds[k.strip()] = v.strip()
            return creds.get('ML_APP_ID', ''), creds.get('CLIENT_SECRET', '')
    raise FileNotFoundError('No secrets file found. Tried: ' + WORKSPACE_SECRETS + ', ' + SKILL_REL_SECRETS)

def get_token(app_id, client_secret):
    """Get client_credentials access token from MercadoLibre API.
    Returns access_token string (expires in 21600s / 6h)."""
    data = urllib.parse.urlencode({
        'grant_type': 'client_credentials',
        'client_id': app_id,
        'client_secret': client_secret,
    }).encode()
    req = urllib.request.Request('https://api.mercadolibre.com/oauth/token',
        data=data,
        headers={'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=10) as r:
        t = json.loads(r.read())
    return t['access_token']

def api_get(url, token):
    """Make authenticated GET request to MercadoLibre API.
    Returns parsed JSON (dict or list).
    Uses req.add_header() to avoid OpenClaw secret injection issues."""
    req = urllib.request.Request(url)
    req.add_header('Authorization', 'Bearer ' + token)
    with urllib.request.urlopen(req, timeout=10) as r:
        data = r.read()
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return {'_raw': data.decode()}

def get_item_description(item_id, token):
    """Get item description text. Returns plain_text string."""
    data = api_get('https://api.mercadolibre.com/items/' + item_id + '/description', token)
    return data.get('plain_text', '')

def get_item_questions(item_id, token, limit=3, offset=0):
    """Get item questions with answers.
    Returns dict with 'total', 'questions', 'limit', 'offset'."""
    return api_get(
        'https://api.mercadolibre.com/questions/search?item=' + item_id
        + '&limit=' + str(limit) + '&offset=' + str(offset), token)

def get_seller_info(seller_id, token):
    """Get public seller information.
    Returns dict with nickname, address, seller_reputation, etc."""
    return api_get('https://api.mercadolibre.com/users/' + str(seller_id), token)

def discover_seller_id(item_id, token):
    """Get seller_id from the first question of an item.
    Returns seller_id int or None."""
    qs = get_item_questions(item_id, token, limit=1)
    questions = qs.get('questions', [])
    if questions:
        return questions[0].get('seller_id')
    return None