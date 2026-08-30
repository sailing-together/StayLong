# Gemma privacy guard

StayLong uses Vertex Model Garden MaaS `gemma-4-26b-a4b-it-maas` as a bounded privacy layer in the public sandbox. It is a request-based, global model service, so StayLong does not deploy or operate a dedicated GPU endpoint. Before a concern is persisted or reaches an action boundary, the guard asks Gemma to return exactly:

```json
{"redacted_text":"...", "detected_categories":["phone"]}
```

The response is schema-validated. Empty text, unexpected fields, malformed JSON, invalid categories or an unavailable Gemma service are rejected. In every rejection case, StayLong fails closed: it does not persist the concern, start the Gemini/ADK plan, or execute an action. The public API instead returns a plain-language retry response without exposing model or user-text details. Gemma cannot route emergencies, decide eligibility, select providers, grant consent or approve actions; those decisions remain deterministic application policy and human approval.

Enable the integration with `STAYLONG_GEMMA_ENABLED=true`. The sandbox Terraform component also supplies the exact MaaS model ID, Vertex project, `global` location and `GOOGLE_GENAI_USE_VERTEXAI=true`. Before deployment, an authorised operator must enable the model's API from its Model Garden **API Service** card. Local tests inject a fake provider and never call Vertex.

This integration is an optional All Things Agentic Hackathon bonus contribution. The required Gemini 3.6 Flash/ADK coordinator remains the primary planning model. Evidence must show the Model Garden model ID, a synthetic-data public smoke, the strict response tests and the request-based cost boundary; no real personal information, tokens or prompts are retained in evidence.
