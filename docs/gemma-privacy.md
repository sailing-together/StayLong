# Gemma privacy guard

StayLong uses Vertex AI-hosted `gemma-3-27b-it` as a bounded privacy layer in the public sandbox. Before a concern is persisted or reaches an action boundary, the guard asks Gemma to return exactly:

```json
{"redacted_text":"...", "detected_categories":["phone"]}
```

The response is schema-validated. Empty text, unexpected fields, malformed JSON or invalid categories are rejected. Gemma cannot route emergencies, decide eligibility, select providers, grant consent or approve actions; those decisions remain deterministic application policy and human approval.

Enable the integration with `STAYLONG_GEMMA_ENABLED=true`. The sandbox Terraform component also supplies the Vertex project, `global` location and `GOOGLE_GENAI_USE_VERTEXAI=true`. Local tests inject a fake provider and never call Vertex.

This integration is an optional All Things Agentic Hackathon bonus contribution. The required Gemini 3.5+/ADK coordinator remains the primary planning model.

