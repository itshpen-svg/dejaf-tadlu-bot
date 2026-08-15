"""
Chapa payment gateway integration.

Chapa (chapa.co) is an Ethiopian payment aggregator supporting Telebirr,
CBE Birr, HelloCash, and card payments through a single API. This module
handles starting a payment (initialize) and confirming it really happened
(verify) — always trusting verify(), never the webhook body alone, since
webhook payloads can be spoofed by anyone who knows or guesses the URL.

Docs: https://developer.chapa.co
"""

import os
import httpx

CHAPA_SECRET_KEY = os.getenv("CHAPA_SECRET_KEY")
CHAPA_BASE_URL = "https://api.chapa.co/v1"
PUBLIC_URL = os.getenv("PUBLIC_URL", "").rstrip("/")


class ChapaError(Exception):
    """Raised when Chapa can't start or verify a payment."""


def _require_config():
    if not CHAPA_SECRET_KEY:
        raise ChapaError(
            "CHAPA_SECRET_KEY is not set. Add it in your .env or Railway Variables."
        )
    if not PUBLIC_URL:
        raise ChapaError(
            "PUBLIC_URL is not set. Chapa needs a public https URL to send payment "
            "confirmations to (e.g. your Railway domain)."
        )


async def initialize_payment(
    *, amount: float, currency: str, email: str, first_name: str,
    last_name: str, tx_ref: str, order_description: str,
) -> str:
    """Starts a Chapa payment and returns the checkout_url the customer should open."""
    _require_config()

    payload = {
        "amount": f"{amount:.2f}",
        "currency": currency,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "tx_ref": tx_ref,
        "callback_url": f"{PUBLIC_URL}/chapa/webhook",
        "return_url": f"{PUBLIC_URL}/chapa/thank-you",
        "customization[title]": "Dejaf Tadlu",
        "customization[description]": order_description[:100],
    }
    headers = {"Authorization": f"Bearer {CHAPA_SECRET_KEY}"}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{CHAPA_BASE_URL}/transaction/initialize", data=payload, headers=headers
        )

    try:
        data = resp.json()
    except Exception as e:
        raise ChapaError(f"Chapa returned an unreadable response: {e}") from e

    if data.get("status") != "success":
        raise ChapaError(data.get("message", "Chapa initialization failed"))

    checkout_url = data.get("data", {}).get("checkout_url")
    if not checkout_url:
        raise ChapaError("Chapa did not return a checkout_url")

    return checkout_url


async def verify_payment(tx_ref: str) -> dict:
    """
    Asks Chapa directly whether a transaction actually succeeded.
    This is the source of truth — always call this before trusting a webhook.
    """
    _require_config()

    headers = {"Authorization": f"Bearer {CHAPA_SECRET_KEY}"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{CHAPA_BASE_URL}/transaction/verify/{tx_ref}", headers=headers
        )

    try:
        return resp.json()
    except Exception as e:
        raise ChapaError(f"Chapa returned an unreadable response: {e}") from e


def payment_succeeded(verify_result: dict) -> bool:
    """True only if Chapa's verify endpoint confirms a completed, successful payment."""
    return (
        verify_result.get("status") == "success"
        and verify_result.get("data", {}).get("status") == "success"
    )
