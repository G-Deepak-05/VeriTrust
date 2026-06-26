"""
Input validators for the verification pipeline.
"""
import ipaddress
import re

# ─── PAN Validation ───────────────────────────────────────────────────────────
_PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def is_valid_pan(pan: str) -> bool:
    """Validate Indian PAN number format: AAAAA9999A"""
    return bool(_PAN_PATTERN.match(pan.strip()))


# ─── Phone Validation ─────────────────────────────────────────────────────────
def is_valid_phone(phone: str) -> bool:
    """Validate E.164 phone number format using phonenumbers library."""
    try:
        import phonenumbers
        parsed = phonenumbers.parse(phone, None)
        return phonenumbers.is_valid_number(parsed)
    except Exception:
        return False


# ─── Email / Disposable Domains ───────────────────────────────────────────────
_DISPOSABLE_DOMAINS = frozenset(
    {
        # Common disposable email providers
        "mailinator.com", "guerrillamail.com", "10minutemail.com", "throwam.com",
        "sharklasers.com", "guerrillamailblock.com", "grr.la", "guerrillamail.info",
        "guerrillamail.biz", "guerrillamail.de", "guerrillamail.net", "guerrillamail.org",
        "spam4.me", "trashmail.at", "trashmail.com", "trashmail.me", "trashmail.net",
        "trashmail.org", "yopmail.com", "yopmail.fr", "cool.fr.nf", "jetable.fr.nf",
        "nospam.ze.tc", "nomail.xl.cx", "mega.zik.dj", "speed.1s.fr", "courriel.fr.nf",
        "moncourrier.fr.nf", "monemail.fr.nf", "monmail.fr.nf", "tempr.email",
        "dispostable.com", "mailnull.com", "spamgourmet.com", "spamgourmet.net",
        "spamgourmet.org", "binkmail.com", "bob.espressomail.com", "putthisinyourspamdatabase.com",
        "sendspamhere.com", "spamthisplease.com", "thisisnotmyrealemail.com", "throwam.com",
        "wegwerfmail.de", "wegwerfmail.net", "wegwerfmail.org", "tempmail.com",
        "temp-mail.org", "fakeinbox.com", "discard.email", "spamex.com",
        "mailexpire.com", "mailmetrash.com", "maileater.com", "mailscrap.com",
        "deadaddress.com", "anonbox.net", "filzmail.com", "spamfree24.org",
        "spamfree24.de", "spamfree24.eu", "spamfree24.net", "spamfree24.info",
        "kasmail.com", "spammotel.com", "maildrop.cc", "spamgob.com",
        "mailnesia.com", "nwldx.com", "amilegit.com", "rtrtr.com",
        "throwam.com", "getnada.com", "moakt.com", "mohmal.com",
        "dispostable.com", "spamcowboy.com", "spamcowboy.net", "spamcowboy.org",
        "bumpymail.com", "mt2009.com", "klzlk.com", "throwam.com",
    }
)


def is_disposable_email(email: str) -> bool:
    """Check if an email domain is a known disposable/throwaway provider."""
    if not email or "@" not in email:
        return False
    domain = email.split("@", 1)[1].lower().strip()
    return domain in _DISPOSABLE_DOMAINS


# ─── IP Address ───────────────────────────────────────────────────────────────
def is_private_ip(ip: str) -> bool:
    """Check if an IP address is in a private/reserved range."""
    try:
        addr = ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback or addr.is_reserved
    except ValueError:
        return False


def is_valid_ip(ip: str) -> bool:
    """Check if a string is a valid IP address (v4 or v6)."""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False
