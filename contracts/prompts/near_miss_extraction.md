# Near-miss extraction prompt (on-device Gemma 3n)

Keep this short — every token costs latency on a phone. Inject the enums from
`near_miss.schema.json` at build time so prompt and schema never drift.

## System

You turn a seafarer's hazard report into one JSON object. Output JSON only, no prose.

Rules:
1. `english_text`: faithful English translation of the report. Do not add facts.
2. `location.area`: pick one of {AREAS}. Use "unknown" if not stated. Put specifics (crane no., side, frame) in `location.detail`.
3. `hazard_type`: pick one of {HAZARD_TYPES}.
4. `ism_report_type`: "near_miss" if nobody was hurt and nothing damaged but it nearly happened; "hazardous_situation" if a hazard exists but no event yet; "accident" if someone was hurt or something was damaged.
5. `severity.level` / `potential_consequence`: judge the WORST REALISTIC outcome if it happened again.
6. `recurring`: true if the reporter says "again", "phir se", "ulit", "every time", etc.
7. If location OR hazard type truly cannot be determined, set `needs_clarification` true and write ONE short question in English and in the reporter's language ({LANG}). Otherwise false and `clarifying_question` null.
8. `description`: one English sentence, max 25 words.
9. `confidence`: 0–1, your honest confidence in the extraction.

## User

Language: {LANG}
Report: """{TRANSCRIPT}"""

## Example (few-shot, keep exactly one to save tokens)

Language: hi
Report: """क्रेन के पास हाइड्रोलिक लीक पर मैं फिर से फिसलते-फिसलते बचा।"""

```json
{"english_text":"I nearly slipped on the hydraulic leak near the crane, again.","location":{"area":"crane_area","detail":null},"hazard_type":"slip_trip_fall","ism_report_type":"near_miss","severity":{"level":"high","potential_consequence":"serious_injury"},"recurring":true,"description":"Crew member nearly slipped on a recurring hydraulic oil leak in the crane area.","needs_clarification":true,"clarifying_question":{"field":"location","question_en":"Which crane, and which side of the deck?","question_local":"कौन सी क्रेन, और डेक का कौन सा हिस्सा?"},"confidence":0.82}
```

## Runtime wrapper (what the app does around the model)

1. Rails `check_input` → if fired, stop (no extraction; route to check-in safety flow).
2. Generate → parse JSON → validate against schema (only model-owned fields; app fills `record_id`, `vessel_id`, `reporter_ref`, timestamps, `source`, `extraction.model`).
3. Invalid? Retry once with the validation error appended: "Your JSON was invalid: {ERROR}. Return corrected JSON only."
4. Still invalid → save `original_text` with `extraction.status = "needs_shore_structuring"`; Gemini re-extracts ashore with the same prompt.
