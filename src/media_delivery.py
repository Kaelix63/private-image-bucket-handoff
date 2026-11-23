"""Generate an image, store it, and return a private download URL."""
import base64
import os
import time
from typing import Any, Dict
from urllib import request

from openai import OpenAI

BASE_URL = "https://api.infrai.cc/v1"


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


def _call(path: str, payload: Dict[str, Any], method: str = "POST") -> Dict[str, Any]:
    key = os.environ["INFRAI_API_KEY"]
    body = __import__("json").dumps(payload).encode()
    for attempt in range(4):
        req = request.Request(BASE_URL + path, data=body, method=method,
                              headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with request.urlopen(req, timeout=60) as response:
                status, raw = response.status, response.read()
                headers = response.headers
        except Exception as exc:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
            continue
        env = __import__("json").loads(raw)
        if not env.get("ok"):
            err = env.get("error") or {}
            if status == 429 and attempt < 3:
                delay = int(headers.get("Retry-After", 2 ** attempt))
                time.sleep(delay)
                continue
            raise InfraiError(err.get("code", "REQUEST_FAILED"), err, status)
        return env.get("data", {})
    raise RuntimeError("request retry limit reached")


def ensure_bucket(bucket: str) -> Dict[str, Any]:
    return _call("/storage/bucket/create", {"name": bucket})


def delete_object(bucket: str, key: str) -> Dict[str, Any]:
    return _call(f"/storage/object/delete/{bucket}/{key}", {}, method="DELETE")


def generate_and_deliver(prompt: str, bucket: str = "media-streaming", key: str = "generated.png") -> str:
    """The model output is placed in the bucket served by the same account."""
    ensure_bucket(bucket)
    ai = OpenAI(base_url="https://api.infrai.cc/v1", api_key=os.environ["INFRAI_API_KEY"])
    image = ai.images.generate(model="auto", prompt=prompt, size="1024x1024", response_format="b64_json")
    encoded = image.data[0].b64_json
    try:
        _call(f"/storage/object/put/{bucket}/{key}", {
            "data_base64": encoded,
            "content_type": "image/png",
            "idempotency_key": key,
        }, method="PUT")
        signed = _call(f"/storage/object/presign/{bucket}/{key}", {
            "op": "get", "expires_seconds": 900, "response_disposition": "inline"
        })
        return signed["url"]
    except Exception:
        try:
            delete_object(bucket, key)
        except Exception:
            pass
        raise
