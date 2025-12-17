import time
from uuid import uuid4
from typing import Dict, Any, Optional

import httpx
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field

TORCH_BASE_URL = "https://torch-handson-5403bd9ca59f.herokuapp.com"
TORCH_AUTH = "teeth"

POLL_INTERVAL_SECONDS = 0.5
POLL_TIMEOUT_SECONDS = 10

app = FastAPI()

# In-memory store for idempotency / results
STATE: Dict[str, Any] = {}


class PaymentRequest(BaseModel):
    amount: int = Field(..., gt=0, description="Amount in cents")


def torch_headers() -> Dict[str, str]:
    return {
        "X-Torch-Auth": TORCH_AUTH,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def torch_request(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    body: Optional[dict] = None,
) -> httpx.Response:
    url = f"{TORCH_BASE_URL}{path}"
    return await client.request(
        method,
        url,
        headers=torch_headers(),
        json=body,
        timeout=10,
    )


@app.post("/card/{card_id}/payment")
async def create_card_payment(
    card_id: int,
    body: PaymentRequest,
    idempotency_key: Optional[str] = Header(default=None),
):
    key = idempotency_key or str(uuid4())
    if key in STATE:
        return STATE[key]

    async with httpx.AsyncClient() as client:
        # (a) Place hold
        hold_resp = await torch_request(
            client,
            "POST",
            f"/card/{card_id}/hold",
            {"amount": body.amount},
        )
        if hold_resp.status_code != 200:
            # hold creation failure - If we cannot secure funds, nothing else should proceed
            raise HTTPException(status_code=hold_resp.status_code, detail=hold_resp.text)
        hold = hold_resp.json()

        # (b) Initiate payment
        payment_resp = await torch_request(
            client,
            "POST",
            "/payment",
            {"amount": body.amount},
        )
        if payment_resp.status_code != 200:
            # payment creation failure - do not attempt capture - let hold expire 
            raise HTTPException(status_code=payment_resp.status_code, detail=payment_resp.text)
        payment = payment_resp.json()
        payment_id = payment.get("id")

        # (c) Poll for settlement
        deadline = time.time() + POLL_TIMEOUT_SECONDS
        while time.time() < deadline:
            status_resp = await torch_request(client, "GET", f"/payment/{payment_id}")
            if status_resp.status_code != 200:
                raise HTTPException(status_code=status_resp.status_code, detail=status_resp.text)

            payment = status_resp.json()
            status = payment.get("status")
        
            if status in ("settled", "failed"):
                break

            time.sleep(POLL_INTERVAL_SECONDS)

        if payment.get("status") == "failed":
            # payment settlement failure - do not procede to capture funds if settlement failed
            result = {"status": "failed", "hold": hold, "payment": payment}
            STATE[key] = result
            return result

        if payment.get("status") != "settled":
            # otherwise, av
            raise HTTPException(status_code=504, detail="Payment did not settle in time")

        # (d) Capture funds
        capture_resp = await torch_request(
            client,
            "POST",
            f"/card/{card_id}/hold/{hold['id']}/capture",
            {"amount": body.amount},
        )
        if capture_resp.status_code != 200:
            raise HTTPException(status_code=capture_resp.status_code, detail=capture_resp.text)
        capture = capture_resp.json()

        result = {
            "status": "success",
            "card_id": card_id,
            "amount": body.amount,
            "hold": hold,
            "payment": payment,
            "capture": capture,
        }
        STATE[key] = result
        return result

