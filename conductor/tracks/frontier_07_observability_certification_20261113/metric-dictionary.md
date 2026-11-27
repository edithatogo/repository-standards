# Integration metrics — 27 November 2026

Refs #69 and #192. Bounded, aggregate-only UTC monthly prototype;
independently supplied uniquely identified comparable event observations.
Synthetic and observed scopes may not be pooled. Do not publish event IDs,
repository names, raw logs or private input. The pure aggregator does not
authenticate or collect observations.

| Metric | Numerator or measurement | Denominator or coverage |
| --- | --- | --- |
| Integration success | Merged | Merged plus failed; held/unknown reported separately |
| CI success | Passed | Passed plus failed; unknown/not applicable separate |
| Repair success | Successful | Successful plus failed; not attempted/unknown separate |
| False acceptance | Accepted independently labelled unsafe | Unsafe with observed decision |
| Merge latency | Median seconds | Known among merged events |
| Runner consumption | Sum seconds | Known count / total events |
| Maintenance burden | Sum seconds | Known count / total events |
| Cost | Sum observed USD cents | Known count / total events; no exchange-rate estimate |

Absent denominator or measurement is null, never a zero rate or free
operation. Missing labels/decisions are counted explicitly; observed
event records must not derive their unsafe label from the model being
evaluated. Duplicate IDs, unknown fields, mixed scope and invalid measures
reject. Four synthetic tests passed locally. The actual longitudinal
collector, independently verified observation identity/rights, persistence,
cohort and risk stratification, review cadence and F07 certification
remain open. No changes to live collection, credentials or rollout.
