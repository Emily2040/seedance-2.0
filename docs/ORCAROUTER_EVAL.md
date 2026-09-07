# OrcaRouter evaluation adapter

This optional source-checkout adapter evaluates prompt behavior through a third-party text API. It does not generate Seedance videos and is excluded from the installed skill payload.

The [native HTTP contract](https://docs.orcarouter.ai/native-formats/anthropic) and [SDK compatibility page](https://docs.orcarouter.ai/compatibility/anthropic-sdk), reviewed 2026-09-07, document `https://api.orcarouter.ai/v1/messages`, the Anthropic message format, and `x-api-key` authentication. The adapter deliberately accepts only `anthropic/claude-sonnet-4.6` and `anthropic/claude-opus-4.7`, listed in the [provider catalog guide](https://docs.orcarouter.ai/getting-started/models). Catalog examples are not proof of account access or live availability. Other providers in that catalog need separate response-contract review before being enabled here.

Preview without credentials, network activity, or ledger writes:

```bash
python scripts/eval_run.py --provider orcarouter --limit 1
```

After confirming account access, pricing, and permission to send the selected source material, supply `ORCAROUTER_API_KEY` through the environment. An explicitly authorized, bounded run is:

```bash
python scripts/eval_run.py --provider orcarouter --live --limit 1 \
  --max-calls 3 --max-output-tokens 3300 --ledger eval-runs/orca-smoke.md
```

These ceilings limit requests and reserved output tokens, not currency. The adapter does not use adaptive routing or fallbacks. Response model names must match exactly or use one of the enumerated equivalent Claude spellings in the source. Undocumented suffixes, switched models, malformed reasoning blocks, and unknown envelope fields fail validation; they are not silently accepted to make a run pass. Model aliases remain provider-controlled and are not immutable version pins.

Validation uses offline response fixtures and transport mocks. No maintainer live call or output-quality comparison was performed for this integration. Provider security marketing is not evidence that this harness or an agent's tool execution is protected.
