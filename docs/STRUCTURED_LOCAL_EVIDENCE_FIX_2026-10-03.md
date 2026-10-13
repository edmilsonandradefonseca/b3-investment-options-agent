# Local evidence structured output correction

Block 2, step 4: the local worker now builds a fresh per-request JSON schema. evidence_refs items are restricted to the request's exact source references through enum; requests without references permit only an empty array. Model settings and shared schema are preserved. Post-generation validation still rejects unknown references and now rejects extra fields and non-string array items.

Prompt version v4 produces distinct retry identifiers without deleting prior degraded dossiers. The real validator selects current-version price-target requests.

Validation: all 898 local tests passed, including permitted-reference schema, empty-reference schema, configuration isolation and malformed fields. DeepSeek model, temperature and token limits unchanged. This is a code correction, not proof of model accuracy or production activation. Ubuntu admission and deployment remain pending.
