"""One zero-cost CurlShip creation; confirmed intake and public listing differ.

The only network destinations are the documented anonymous API endpoints below.
The payload is exactly the supplied root URL and contact email. No paid field,
account, environment credentials, redirect, retry, arbitrary webhook or AI copy.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests

SLUG = "curlship.com"
LISTINGS = "https://curlship.com/api/listings"
SUBMIT = "https://curlship.com/api/submit"
LISTING = "https://curlship.com/api/listing/"
MAX_BYTES = 8_000_000
HEADERS = {"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "dirsubmit/0.1"}
PROTECTED = {"submitted", "approved", "unverified"}
FORBIDDEN_HOSTS = {"linktr.ee", "bio.link", "x.com", "linkedin.com", "medium.com"}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _host(url):
    return (urlsplit(url).hostname or "").lower().removeprefix("www.")


def _valid_input(url, email):
    if not isinstance(url, str) or url != url.strip():
        return False
    try:
        u = urlsplit(url)
        if u.scheme != "https" or u.username or u.password or u.port is not None or u.path not in ("", "/") or u.query or u.fragment:
            return False
        host = u.hostname or ""
        if any(host.lower() == h or host.lower().endswith("." + h) for h in FORBIDDEN_HOSTS):
            return False
        if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", host) or "." not in host or host.endswith((".local", ".localhost")):
            return False
        try:
            ipaddress.ip_address(host)
            return False
        except ValueError:
            pass
    except ValueError:
        return False
    return isinstance(email, str) and len(email) <= 254 and re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}", email) is not None


def _request(method, url, payload=None):
    # Each phase has a new anonymous session: no cookie transfer, .netrc or env auth.
    with requests.Session() as session:
        session.trust_env = False
        session.auth = None
        session.cookies.clear()
        session.mount("https://", requests.adapters.HTTPAdapter(max_retries=0))
        return session.request(method, url, data=json.dumps(payload, separators=(",", ":")).encode() if payload is not None else None, headers=HEADERS, timeout=30, allow_redirects=False)


def _body(response, expected_url):
    if response.url != expected_url or len(response.content) > MAX_BYTES:
        raise ValueError("Unexpected URL or bounded-response limit")
    body = response.json()
    if not isinstance(body, dict):
        raise ValueError("Not a JSON object")
    return body


def _listing_matches(entry, url, listing_id=None):
    return isinstance(entry, dict) and type(entry.get("id")) is int and entry["id"] > 0 and (listing_id is None or entry["id"] == listing_id) and entry.get("url") == url and entry.get("tier") == "free"


def _safe_fields(entry):
    # Never save API-returned email, tokens, credentials or arbitrary error text.
    return {k: entry[k] for k in ("id", "url", "tier") if k in entry}


def _save(path, receipt):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as out:
        json.dump(receipt, out, ensure_ascii=False, indent=2)
        out.write("\n")
    temporary.chmod(0o600)
    os.replace(temporary, path)


def submit_curlship(product, store, evidence_dir="runs", dry_run=False):
    def result(status, note, live_url="", receipt=None):
        return {"status": status, "note": note, "live_url": live_url, "receipt": str(receipt) if receipt else ""}
    contact = getattr(product, "submitter_email", "")
    if not _valid_input(product.url, contact):
        return result("blocked", "CurlShip requires an allowed HTTPS root URL and explicit verified submitter_email; product.email is not a fallback")
    key = product.url.rstrip("/")
    if store.product_key != key:
        return result("blocked", "Product-scoped Store does not match the supplied URL; no fields were sent")
    if dry_run:
        return result("dry-run", "CurlShip free URL/email-only request; no network, receipt or Store mutation")
    canonical_key = "https://" + _host(product.url)
    equivalent_keys = (canonical_key, "https://www." + _host(product.url))
    if store.get_status(SLUG) in PROTECTED or store.protected_equivalent_status(SLUG, equivalent_keys):
        return result("skipped", "Already submitted, public, or uncertain for this product; no automatic repeat")
    path = Path(evidence_dir) / (SLUG + "-" + hashlib.sha256(canonical_key.encode()).hexdigest() + ".json")
    # Preserve pre-canonical receipt paths while sharing one future alias marker.
    for old_key in dict.fromkeys((canonical_key, key, *equivalent_keys)):
        previous = Path(evidence_dir) / (SLUG + "-" + hashlib.sha256(old_key.encode()).hexdigest() + ".json")
        if previous.exists():
            return result("skipped", "Existing durable CurlShip attempt receipt; inspect it rather than repeat", receipt=previous)
    try:
        before = _request("GET", LISTINGS)
        body = _body(before, LISTINGS)
        entries = body.get("listings")
        if before.status_code != 200 or body.get("ok") is not True or not isinstance(entries, list) or any(body.get(k) for k in ("has_more", "hasMore", "next", "next_page")) or (type(body.get("total")) is int and body["total"] > len(entries)):
            raise ValueError("Incomplete duplicate check")
        if any(not isinstance(e, dict) or not isinstance(e.get("url"), str) or not _host(e["url"]) for e in entries):
            raise ValueError("Malformed listing URL")
        # Exact host plus optional www only. No PSL/eTLD/private-queue claim.
        if any(_host(e["url"]) == _host(product.url) for e in entries):
            return result("blocked", "Existing public hostname/www-alias match; no new POST, intake or publication claimed")
    except Exception as exc:
        return result("blocked", "Duplicate check unavailable (" + type(exc).__name__ + "); no POST attempted")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic product/directory reservation survives crashes and changed evidence dirs.
    if not store.reserve_attempt(SLUG, "auto", "CurlShip request reserved; result uncertain until exact receipt", equivalent_product_keys=equivalent_keys):
        return result("skipped", "Another protected product-specific attempt exists; no POST attempted")
    receipt = {"schema_version": 1, "recorded_at_utc": _now(), "product": key, "category": "directories", "target_key": SLUG, "endpoint": SUBMIT, "payload_fields": ["url", "email"], "email_source": "explicit_verified_submitter_email", "duplicate_check_scope": "Exact public hostname with optional leading www only; not registered-root/eTLD or sibling-subdomain/private-queue coverage. HTTP200/409 never establish new creation.", "paid_fields_omitted": True, "amount_paid": 0, "email_value_saved": False, "normal_POST_actions": 0, "actual_submission": False, "independent_public_verified": False, "grade": "U", "stage": "reserved_before_POST"}
    try:
        # Exclusive path also prevents differently initialized callers sharing a file.
        with path.open("x", encoding="utf-8") as marker:
            json.dump(receipt, marker)
        path.chmod(0o600)
    except FileExistsError:
        return result("skipped", "Concurrent durable attempt exists; no POST attempted", receipt=path)
    except OSError:
        return result("unverified", "Could not save durable reservation; no POST attempted", receipt=path)
    try:
        receipt["normal_POST_actions"] = 1
        response = _request("POST", SUBMIT, {"url": product.url, "email": contact})
        posted = _body(response, SUBMIT)
        entry = posted.get("listing", {})
        receipt.update({"status_code": response.status_code, "response_body_sha256": hashlib.sha256(response.content).hexdigest(), "stage": "POST_attempted_no_retry"})
        if response.status_code != 201 or posted.get("ok") is not True or not _listing_matches(entry, product.url):
            raise ValueError("No exact 201 free creation")
    except Exception as exc:
        receipt.update({"stage": "uncertain_after_one_POST_attempt", "error_type": type(exc).__name__})
        try:
            _save(path, receipt)
        except OSError:
            pass
        return result("unverified", "POST result uncertain (" + type(exc).__name__ + "); no retry or redirect", receipt=path)
    public_url = LISTING + str(entry["id"])
    receipt.update({"server_new_listing_creation_verified": True, "actual_submission": True, "public_listing_fields": _safe_fields(entry), "canonical_url": public_url, "grade": "A", "stage": "201_creation_public_check_pending"})
    store.set_status(SLUG, "auto", "submitted", "Exact 201 free creation; separate public check pending", public_url)
    try:
        _save(path, receipt)
    except OSError:
        return result("submitted", "Exact 201 intake confirmed; receipt persistence failed, public check pending; do not POST again", public_url, path)
    try:
        public = _request("GET", public_url)
        publicbody = _body(public, public_url)
        observed = publicbody.get("listing", {})
        checks = {"POST201_new_creation": True, "anonymous_GET200": public.status_code == 200, "anonymous_GET_ok": publicbody.get("ok") is True, "exact_public_numeric_id_URL_and_free_tier": _listing_matches(observed, product.url, entry["id"]), "public_title_present": isinstance(observed.get("title"), str) and bool(observed["title"].strip()), "public_description_present": isinstance(observed.get("description"), str) and bool(observed["description"].strip()), "title_and_description_same_as_creation": all(observed.get(k) == entry.get(k) for k in ("title", "description")), "no_paid_fields_submitted": True, "no_auth_or_cookie_transfer": True}
        approved = all(checks.values())
        receipt.update({"public_GET_status": public.status_code, "public_response_sha256": hashlib.sha256(public.content).hexdigest(), "independent_public_listing_fields": _safe_fields(observed) if isinstance(observed, dict) else {}, "checks": checks, "all_checks_pass": approved, "independent_public_verified": approved, "grade": "S" if approved else "A", "stage": "public_checked", "independent_public_checked_at_utc": _now()})
    except Exception as exc:
        approved = False
        receipt.update({"public_check_error_type": type(exc).__name__, "stage": "201_creation_public_check_unverified"})
    try:
        _save(path, receipt)
    except OSError:
        return result("submitted", "Exact 201 intake confirmed; public-proof persistence failed; do not POST again", public_url, path)
    if approved:
        store.update_checked(SLUG, "approved", public_url, "Exact 201 plus separate anonymous public GET matched ID, URL, free tier and metadata")
        return result("approved", "Created once; separate public listing verified", public_url, path)
    return result("submitted", "Exact 201 creation confirmed; public verification pending; do not POST again", public_url, path)
