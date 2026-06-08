import hashlib

from django.core.cache import cache


def _client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def _clean_key_part(value):
    value = str(value or '').strip().lower()
    if not value:
        return ''
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _increment(key, window):
    if cache.add(key, 0, timeout=window):
        return cache.incr(key)
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window)
        return 1


def is_limited(request, scope, limit, window, identifiers=None):
    identifiers = [identifier for identifier in (identifiers or []) if identifier]
    subjects = [f"ip:{_client_ip(request)}"]

    if request.user.is_authenticated:
        subjects.append(f"user:{request.user.id}")

    subjects.extend(f"id:{identifier}" for identifier in identifiers)

    for subject in subjects:
        key = f"ratelimit:{scope}:{_clean_key_part(subject)}"
        if _increment(key, window) > limit:
            return True
    return False


def limit_message(limit, window):
    if window >= 3600:
        unit = 'hour'
        amount = window // 3600
    elif window >= 60:
        unit = 'minute'
        amount = window // 60
    else:
        unit = 'second'
        amount = window

    unit_text = unit if amount == 1 else f'{unit}s'
    return f"Too many requests. Please try again in {amount} {unit_text}."
