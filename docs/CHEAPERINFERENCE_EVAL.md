# Cheaper Inference evaluation adapter

This optional source-checkout adapter evaluates prompt behavior through a third-party text API. It does not generate Seedance videos and is excluded from the installed skill payload.

The [API reference](https://cheaperinference.com/docs), reviewed 2026-10-01, documents an Anthropic-compatible `https://api.cheaperinference.com/v1/messages` endpoint with `x-api-key` authentication. The adapter accepts only `claude-sonnet-5` and `gpt-5.4-mini`, listed in the live `GET /v1/models` catalog on that date. Catalog rows are not proof of account access or future availability. Other catalog models need separate response-contract review before being enabled here.

Preview without credentials, network activity, or ledger writes:

```bash
python scripts/eval_run.py --provider cheaperinference --limit 1
```

After confirming account access, pricing, and permission to send the selected source material, supply `CHEAPER_INFERENCE_API_KEY` through the environment. An explicitly authorized, bounded run is:

```bash
python scripts/eval_run.py --provider cheaperinference --live --limit 1 \
  --max-calls 3 --max-output-tokens 3300 --ledger eval-runs/ci-smoke.md
```

These ceilings limit requests and reserved output tokens, not currency. Response model names must match the request exactly. Every response carries a `cheaper_inference` receipt object; the adapter accepts only its `request_id` and `billing` fields. Unknown envelope fields fail validation. Model names remain provider-controlled and are not immutable version pins.

Validation uses offline response fixtures and transport mocks. One live request per allowed model confirmed the response envelope; no output-quality comparison was performed.
