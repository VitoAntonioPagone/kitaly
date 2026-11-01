"""Customer dispatch notices using the store's authenticated SMTP connection."""
import base64
import hashlib
import html
import json
import os
import re
import smtplib
import ssl
import time
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from flask import current_app


class DispatchMailError(Exception):
    def __init__(self, message, uncertain=False):
        super().__init__(message)
        self.uncertain = uncertain


def validate_tracking_url(value):
    value = value.strip()
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme == 'https' and parsed.hostname and '.' in parsed.hostname
                 and not parsed.username and not parsed.password
                 and parsed.port in {None, 443} and len(value) <= 2048
                 and not any(c.isspace() or ord(c) < 32 for c in value))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('Enter a complete HTTPS tracking link, without spaces or login details.')
    return value


def tracking_fingerprint(order):
    return hashlib.sha256(json.dumps([order.shipping_carrier or '', order.tracking_url or ''],
                                    ensure_ascii=True).encode()).hexdigest()


def mail_readiness():
    c = current_app.config
    if not c.get('SMTP_HOST') or not c.get('SMTP_USER'):
        return False, 'Connect the store email account before sending dispatch notices.'
    oauth = bool(c.get('SMTP_OAUTH_CLIENT_ID') and c.get('SMTP_OAUTH_TOKEN_FILE')
                 and Path(c['SMTP_OAUTH_TOKEN_FILE']).is_file())
    outlook = c['SMTP_USER'].lower().rsplit('@', 1)[-1] in {
        'outlook.com', 'hotmail.com', 'live.com', 'msn.com'}
    if (outlook or c.get('SMTP_OAUTH_CLIENT_ID')) and not oauth:
        return False, 'The store Outlook mailbox needs its secure OAuth connection. Tracking can still be saved.'
    if not oauth and not c.get('SMTP_PASSWORD'):
        return False, 'The store email credentials are not configured. Tracking can still be saved.'
    return True, ''


def outlook_access_token():
    # Separate lock survives atomic token-file replacement across Gunicorn workers.
    import fcntl
    c = current_app.config
    path = Path(c['SMTP_OAUTH_TOKEN_FILE'])
    try:
        if path.stat().st_mode & 0o077:
            raise ValueError('Token file must have owner-only permissions.')
        lock_fd = os.open(str(path) + '.lock', os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(lock_fd, 'w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            data = json.loads(path.read_text())
            if data.get('access_token') and data.get('expires_at', 0) > time.time() + 60:
                return data['access_token']
            tenant = c['SMTP_OAUTH_TENANT']
            if not re.fullmatch(r'[A-Za-z0-9-]+', tenant):
                raise ValueError('Invalid OAuth tenant.')
            params = dict(client_id=c['SMTP_OAUTH_CLIENT_ID'], grant_type='refresh_token',
                          refresh_token=data['refresh_token'],
                          scope='https://outlook.office.com/SMTP.Send offline_access')
            if c.get('SMTP_OAUTH_CLIENT_SECRET'):
                params['client_secret'] = c['SMTP_OAUTH_CLIENT_SECRET']
            request = Request(f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token',
                              data=urlencode(params).encode())
            with urlopen(request, timeout=20) as response:
                fresh = json.load(response)
            data.update(access_token=fresh['access_token'],
                        refresh_token=fresh.get('refresh_token', data['refresh_token']),
                        expires_at=time.time() + int(fresh['expires_in']))
            import tempfile
            fd, temp = tempfile.mkstemp(prefix='.mail-token-', dir=path.parent)
            try:
                with os.fdopen(fd, 'w') as output:
                    json.dump(data, output)
                os.replace(temp, path)
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)
            return data['access_token']
    except Exception:
        raise DispatchMailError('The Outlook connection needs attention. Reconnect the store mailbox.') from None


def dispatch_message(order):
    c = current_app.config
    sender = c.get('SMTP_FROM') or c.get('SMTP_USER') or ''
    recipient = order.customer_email or ''
    for address in (sender, recipient):
        if '\r' in address or '\n' in address or parseaddr(address)[1] != address or '@' not in address:
            raise DispatchMailError('A valid sender and customer email address are required.')
    tracking = validate_tracking_url(order.tracking_url or '')
    italian = (order.checkout_params or {}).get('locale') == 'it'
    title = 'Il tuo ordine Kitaly è stato spedito' if italian else 'Your Kitaly order has been dispatched'
    label = 'Traccia la spedizione' if italian else 'Track your delivery'
    greeting = ('Ciao' if italian else 'Hello') + (' ' + order.customer_name if order.customer_name else '') + ','
    intro = 'Il tuo ordine è in viaggio.' if italian else 'Your order is on its way.'
    reference = ('Ordine' if italian else 'Order') + ' ' + order.id
    names = [item.product_name for item in order.items] or [order.product_name]
    body = '\n\n'.join([greeting, intro, reference, '\n'.join(names),
                         order.shipping_carrier or '', label + ': ' + tracking,
                         'Grazie,\nKitaly' if italian else 'Thank you,\nKitaly'])
    e = html.escape
    message = EmailMessage()
    message['From'] = formataddr(('Kitaly', sender))
    message['To'] = recipient
    message['Subject'] = title
    message['Message-ID'] = f'<dispatch-{order.id}-{tracking_fingerprint(order)[:20]}@{sender.rsplit("@", 1)[-1]}>'
    message.set_content(body)
    message.add_alternative(f'''<!doctype html><html><body style="margin:0;background:#f5efe3;color:#302c24;font-family:Arial,sans-serif"><div style="max-width:560px;margin:0 auto;padding:40px 24px"><p style="letter-spacing:3px;font-size:13px">KITALY</p><h1 style="font-size:26px;font-weight:400">{e(title)}</h1><p>{e(greeting)}</p><p>{e(intro)}</p><p style="font-size:12px;color:#756b5b">{e(reference)}</p><ul>{''.join('<li>'+e(name)+'</li>' for name in names)}</ul><p>{e(order.shipping_carrier or '')}</p><p style="margin:28px 0"><a href="{e(tracking, quote=True)}" style="display:inline-block;padding:16px 24px;background:#302c24;color:#f5efe3;text-decoration:none">{e(label)}</a></p><p style="font-size:12px;line-height:1.6;word-break:break-all">{e(tracking)}</p><p>Kitaly</p></div></body></html>''', subtype='html')
    return message


def send_dispatch_email(order):
    ready, reason = mail_readiness()
    if not ready:
        raise DispatchMailError(reason)
    if not order.livemode and not current_app.testing:
        raise DispatchMailError('Sandbox orders cannot send customer emails.')
    message = dispatch_message(order)
    c = current_app.config
    smtp = None
    try:
        port = int(c.get('SMTP_PORT') or 587)
        context = ssl.create_default_context()
        if port == 465:
            smtp = smtplib.SMTP_SSL(c['SMTP_HOST'], port, timeout=25, context=context)
        else:
            smtp = smtplib.SMTP(c['SMTP_HOST'], port, timeout=25)
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
        if c.get('SMTP_OAUTH_CLIENT_ID'):
            token = outlook_access_token()
            auth = base64.b64encode(f'user={c["SMTP_USER"]}\x01auth=Bearer {token}\x01\x01'.encode()).decode()
            code, _ = smtp.docmd('AUTH', 'XOAUTH2 ' + auth)
            if code != 235:
                raise DispatchMailError('The email provider rejected authentication. Reconnect the store mailbox.')
        else:
            smtp.login(c['SMTP_USER'], c['SMTP_PASSWORD'])
    except DispatchMailError:
        if smtp:
            smtp.close()
        raise
    except Exception:
        if smtp:
            smtp.close()
        raise DispatchMailError('Could not connect or authenticate with the email provider. No email was sent.') from None
    try:
        refused = smtp.send_message(message)
        if refused:
            raise DispatchMailError('The email provider rejected the customer address. No email was sent.')
    except (smtplib.SMTPRecipientsRefused, smtplib.SMTPDataError):
        raise DispatchMailError('The email provider rejected the message. No email was sent.') from None
    except DispatchMailError:
        raise
    except Exception:
        raise DispatchMailError('Delivery status is uncertain. Check the mailbox before retrying.', uncertain=True) from None
    finally:
        try:
            smtp.quit()
        except Exception:
            smtp.close()
