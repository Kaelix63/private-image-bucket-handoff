import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from src import media_delivery


def test_handoff_uses_same_account(monkeypatch):
    monkeypatch.setenv("INFRAI_API_KEY", "test-key")
    calls = []

    class FakeImages:
        def generate(self, **kwargs):
            calls.append(("image", kwargs))
            return type("R", (), {"data": [type("D", (), {"b64_json": base64.b64encode(b"png").decode()})()]})()

    class FakeClient:
        images = FakeImages()

    monkeypatch.setattr(media_delivery, "OpenAI", lambda **kwargs: FakeClient())
    monkeypatch.setattr(media_delivery, "_call", lambda path, payload, method="POST": (calls.append((method, path, payload)) or ({"url": "https://signed"} if "presign" in path else {})))
    assert media_delivery.generate_and_deliver("blue boat", "bucket", "boat.png") == "https://signed"
    assert calls[0][1] == "/storage/bucket/create"
    assert calls[-1][1] == "/storage/object/presign/bucket/boat.png"
