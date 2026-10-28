# Follow-on assessment — 29 October 2026

Read-only source assessment; migrations remain deferred until shared contracts pass.

| Repository / inspected revision | Source evidence | Follow-on boundary |
| --- | --- | --- |
| Lifecourse / be4e4878a24b8f174c0e15158057d9034eca79ed | pyproject declares NumPy, Pandas, Dask, Arrow and plotting; src/lifecourse/model/rng_utils.py implements per-person simulation draws | Candidate Kairos simulation consumer. Preserve epidemiology and cost/QALY calculations in Lifecourse. First qualify cross-process RNG/replay: current seed helper uses Python hash(tag), so its process-independence claim needs a controlled witness. Do not silently replace accepted fixtures. |
| Revalue / c8186e1e02f8153b7533e134e2ad189ca039df68 | requirements.txt pins ASReview2.1.1 and otherwise mixes numerical/plot/test dependencies; voi_logic/metrics/voi_calculators.py implements screening recall, precision and work saved | Retain screening and ASReview diagnostics here. These are not evidence of duplicate VOI estimators merely because the folder is named voi_logic. Inspect decision-theoretic utility semantics before proposing Voiage extraction. Separate packaging/runtime qualification precedes migration. |
| new-drug-reimbursement-game / 696942d8548699d0a139273e85112e746c54398d | ecosystem.lock.toml pins Kairos and Voiage; adapters/voiage.py validates net-benefit samples and calls DecisionAnalysis/ValueArray; pyproject has empty core deps and optional voiage | Genuine existing Voiage consumer, suitable next installed-consumer witness after first-wave contracts. Keep price/reimbursement assumptions and adapter here. Requalify archived integration receipts against new provider pins, rather than assume freshness. |

All three have older Python declarations and need future explicit 3.15 qualification.
No repository was changed. Reimbursement Atlas and terminology/evidence systems
remain outside this migration wave; the game's reviewed evidence import is only
an interface, not authority to migrate the atlas.

Sources were read through GitHub API at the revisions above: package manifests,
source paths and game ecosystem.lock.toml. README similarity was not used as proof
of shared implementation. No numerical equivalence has yet been demonstrated.
