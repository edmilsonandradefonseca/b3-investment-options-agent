# Focused real local worker comparison

Same reviewed XP public ITUB4 and BBDC4 reports, schema with permitted reference enum, temperature 0, context 4096, max output 2048, requested think=false, keep_alive=0. DeepSeek 8B: one READY in 108.4235 seconds; second DEGRADED after 387.487 seconds with INVALID_JSON and OUTPUT_LIMIT_REACHED. Runs 37164794101 and 37165035875.

Qwen3 4B Instruct 2507 Q4_K_M: BBDC4 READY 23.1787 seconds, 165 output tokens; ITUB4 READY 27.0712 seconds, 152 tokens; zero thinking characters and no quality flags for either. Run 37165546420. Model acquisition succeeded. This is two-case structural/source admission, not broad expert quality or sustained queue acceptance.

Default worker now uses Qwen via dedicated B3_LOCAL_EVIDENCE_MODEL; global DeepSeek setting and other project routing unchanged. Dedicated context 4096, output 2048 and timeout 600 remain configurable. Prompt v6 distinguishes new worker requests without deleting failed audit records. Local suite 898 passed.

Chart gate diagnostic: 84 bars, history_count 84, quant data_points 84, COTAHIST and OPLAB sources. Fixed 85 threshold does not reflect the rolling 120-calendar-day window. Candidate validator now verifies at least 60 sessions for indicators, all available persisted COTAHIST dates, unique sessions, requested bounds and fresh tail. Active HTTP verifies count consistency and indicator minimum; candidate persisted coverage gate remains required before checkout update.

Activation and senior regression pending. No production restart claimed.
