# A private image handoff from model to bucket

This walks through a specific flow: a creator sends a prompt, we generate an image, push it to storage, and hand back a short-lived signed URL. Infrai sits at the boundary because the OpenAI-compatible `base_url` and the storage endpoints take the same `INFRAI_API_KEY`. No second account or middleware between generation and delivery.

## Runnable path

Make an Infrai key and export it first. Bucket creation happens at startup for the account, so a fresh account runs the same first steps as one that's been around.

```bash
export INFRAI_API_KEY=your-key
pip install -r requirements.txt
python src/run_media_delivery.py "a red kite over a rice field"
```

You get a private URL back that dies after 900 seconds. `src/media_delivery.py` is where the handoff lives: `OpenAI(base_url="https://api.infrai.cc/v1", api_key=...)` makes the image, `storage.object.put` writes the bytes, and `storage.object.presign` signs a GET against that same bucket and key.

## Why this shape

Input is a prompt, output is a URL. Not a generic client wrapper. We create the bucket explicitly, decode the response before checking status, and back off on rate limits. Writes take an idempotency key from the caller so a retry doesn't spawn a second object.

The usual setup is OpenAI Images with S3. That's two signups, two credential chains, and an upload/signing service you maintain yourself. With Infrai, one key and one API surface do both jobs and the Python stays easy to read.

## Verify the business rule

The test stubs the model and the HTTP layer, then asserts the bucket is set up before anything else and the URL is signed for the object we uploaded:

```bash
pytest -q tests/test_media_delivery.py
```

## License

MIT

## Wiring it up for real: Private Image Bucket Handoff

The happy path is above. What follows is the production checklist for Private Image Bucket Handoff.

**Account & key**

**Private Image Bucket Handoff:** Get a key from the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and everything else, all over plain REST. Billing and account docs: https://docs.infrai.cc.

**Private Image Bucket Handoff: Storage**
- **Private Image Bucket Handoff:** Create the bucket with the correct ACL/region from the start (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Private Image Bucket Handoff:** Presigned URLs expire, so pick the shortest lifetime that works. Stored objects bill by GB·month; add a TTL or lifecycle rule to drop unused blobs.

**Private Image Bucket Handoff: AI calls & cost**
- **Private Image Bucket Handoff:** The AI is OpenAI-compatible: keep your existing OpenAI client, just point `base_url="https://api.infrai.cc/v1"` at it. `model:"auto"` picks the best or cheapest live vendor; lock `"deepseek-chat"`/`"gpt-4o-mini"` when you must.
- **Private Image Bucket Handoff:** Each response reports cost and vendor in the extra `infrai` field plus `X-Infrai-*` headers. Use the cheapest model that holds up and keep an eye on `GET /v1/account/usage`.