#!/usr/bin/env python3
"""Authorize an owned Microsoft app for SMTP sending, without a mailbox password.

Requires an app registration supporting personal accounts and public client flows.
No email is sent by this helper. It verifies SMTP authentication before saving.
"""
import argparse
import base64
import json
import os
import re
import smtplib
import ssl
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import set_key


def post(url, values):
    try:
        with urlopen(Request(url, data=urlencode(values).encode()), timeout=25) as response:
            return json.load(response)
    except HTTPError as error:
        # Never print token responses or credentials in exceptions.
        return json.loads(error.read())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client-id', required=True, help='Application client ID (not a secret).')
    parser.add_argument('--tenant', default='consumers')
    parser.add_argument('--mailbox', default='kitaly.official@outlook.com')
    parser.add_argument('--env-file', default=str(Path(__file__).resolve().parents[1] / '.env'))
    parser.add_argument('--token-file', default='/var/lib/kitaly/outlook-dispatch.json')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9-]+', args.tenant):
        raise SystemExit('Invalid Microsoft tenant.')
    base = f'https://login.microsoftonline.com/{args.tenant}/oauth2/v2.0/'
    device = post(base + 'devicecode', dict(client_id=args.client_id,
                  scope='https://outlook.office.com/SMTP.Send offline_access'))
    if not device.get('device_code'):
        raise SystemExit('Microsoft could not start authorization. Check the app registration and public client setting.')
    print('Open this official Microsoft URL:', device['verification_uri'], flush=True)
    print('Enter this one-time sign-in code:', device['user_code'], flush=True)
    print('Sign in as ' + args.mailbox + ' and review the SMTP sending permission. No email will be sent.', flush=True)
    interval = max(5, int(device.get('interval', 5)))
    deadline = time.monotonic() + int(device['expires_in'])
    tokens = None
    while time.monotonic() < deadline:
        time.sleep(interval)
        tokens = post(base + 'token', dict(client_id=args.client_id,
            grant_type='urn:ietf:params:oauth:grant-type:device_code', device_code=device['device_code']))
        if tokens.get('access_token'):
            break
        if tokens.get('error') == 'slow_down':
            interval += 5
        elif tokens.get('error') != 'authorization_pending':
            raise SystemExit('Microsoft authorization did not complete. No credentials saved.')
    if not tokens or not tokens.get('access_token') or not tokens.get('refresh_token'):
        raise SystemExit('Authorization expired or did not grant ongoing access. No credentials saved.')
    try:
        with smtplib.SMTP('smtp-mail.outlook.com', 587, timeout=25) as smtp:
            smtp.ehlo(); smtp.starttls(context=ssl.create_default_context()); smtp.ehlo()
            auth = base64.b64encode(f'user={args.mailbox}\x01auth=Bearer {tokens["access_token"]}\x01\x01'.encode()).decode()
            code, _ = smtp.docmd('AUTH', 'XOAUTH2 ' + auth)
            if code != 235:
                raise ValueError('Authentication rejected.')
    except Exception:
        raise SystemExit('Microsoft did not allow SMTP sending for this mailbox. No credentials saved.') from None
    path = Path(args.token_file)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    data = {'access_token': tokens['access_token'], 'refresh_token': tokens['refresh_token'],
            'expires_at': time.time() + int(tokens.get('expires_in', 3600))}
    fd, temporary = tempfile.mkstemp(prefix='.outlook-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as output:
            json.dump(data, output)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    env = Path(args.env_file)
    if not env.exists():
        raise SystemExit('Token saved privately, but the specified server environment file is missing.')
    import shutil
    from datetime import datetime
    backup = env.with_name('.env.before-outlook-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    shutil.copy2(env, backup); backup.chmod(0o600)
    for key, value in dict(SMTP_HOST='smtp-mail.outlook.com', SMTP_PORT='587',
            SMTP_USER=args.mailbox, SMTP_FROM=args.mailbox, SMTP_PASSWORD='', SMTP_OAUTH_CLIENT_SECRET='',
            SMTP_OAUTH_CLIENT_ID=args.client_id,
            SMTP_OAUTH_TENANT=args.tenant, SMTP_OAUTH_TOKEN_FILE=str(path)).items():
        set_key(str(env), key, value)
    env.chmod(0o600)
    print('Outlook sending access verified and saved securely. Restart Kitaly to use it. No email was sent.')


if __name__ == '__main__':
    main()
