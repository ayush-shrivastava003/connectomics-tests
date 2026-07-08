# Ir94e → OviDN Sankey Recreation — Project Handoff

## How to use this doc
**Current Status** below is the fast-orientation section — read this first. **Changelog** is the history/reasoning trail, newest entry first — check it if something in Current Status needs justification, or if you're picking this project back up after a major commit. When adding a new changelog entry: only mark something "fixed"/"resolved" if it's been confirmed by actually rerunning and inspecting output, not just described as fixed in conversation — that distinction has caused real confusion in this project's history (see changelog). Don't rewrite past entries except to correct factual errors.

**Process note (how files move around this project):** the code/data live in the `ayush-shrivastava003/connectomics-tests` GitHub repo, connected to this Project. That sync only refreshes at the *start* of a new chat — it won't pick up mid-conversation commits. Workflow: between commits, new data file iterations get uploaded directly into the active chat (provisional, not yet committed); after a major commit, a new chat gets started (often to work a different angle of the project), which picks up the latest repo state fresh. This doc is currently a separate manual Project upload, not part of the repo, so it needs the same manual re-upload treatment as the CSVs whenever it's updated — unless/until the "commit this doc into the repo" open question (see below) gets resolved.

---

## Project overview

**Goal:** Recreate (programmatically, via FlyWire connectomics data) a published Sankey diagram showing how Ir94e neurons (~18 olfactory neurons) connect to OviDN neurons (~5 neurons) through intermediate interneurons in *Drosophila*. The original figure was built from FlyWire materialization **v630**; current work also uses the newer **v783**, which contains additional connectivity not reflected in the original paper. Secondary goal: characterize what's genuinely new in v783 vs. v630, and characterize the ~67 "Other" (unnamed) neurons that participate in the v783 circuit but weren't part of the paper's named groups.

**Target figure structure (ground truth):** 4-tier flow, **Ir94e (ACh) → 5 named groups → 2 pooled interneuron categories → OviDN (ACh)**:

| Edge                                                  | Synapses | Type          |
| ----------------------------------------------------- | -------- | ------------- |
| Ir94e → GNG.SLP.T1 (L)                                | 173      | cholinergic   |
| Ir94e → GNG.SLP.T1 (R)                                | 178      | cholinergic   |
| Ir94e → GNG.SLP.T2 (L)                                | 17       | cholinergic   |
| Ir94e → GNG.SLP.T2 (R)                                | 22       | cholinergic   |
| Ir94e → Earmuff                                       | 20       | cholinergic   |
| GNG.SLP.T1 (L) → ACh interneurons                     | 78       | cholinergic   |
| GNG.SLP.T1 (L) → Glu interneurons                     | 13       | cholinergic   |
| GNG.SLP.T1 (R) → ACh interneurons                     | 33       | cholinergic   |
| GNG.SLP.T1 (R) → Glu interneurons                     | 8        | cholinergic   |
| GNG.SLP.T2 (L) → Glu interneurons                     | 37       | glutamatergic |
| GNG.SLP.T2 (R) → Glu interneurons                     | 25       | glutamatergic |
| Earmuff → ACh interneurons                            | 7        | GABAergic     |
| Earmuff → OviDNs (direct, bypasses interneuron layer) | 83       | GABAergic     |
| ACh interneurons → OviDNs                             | 110      | cholinergic   |
| Glu interneurons → OviDNs                             | 31       | glutamatergic |

Color convention: ACh = excitatory (green); GABA and Glu = inhibitory (pink/red) — Glu is inhibitory here via GluCl receptors, not by neurotransmitter class. No Ir94e→Ir94e self-loop appears in the original figure (resolved — see Changelog); the recreated Sankey excludes it the same way (see Current Status).

**Important structural note on the paper's own grouping convention:** the paper is not internally consistent in how it pools neurons by depth. At hop-1 (immediately downstream of Ir94e), each interneuron/group keeps individual identity: `Earmuff`, `GNG.SLP.T1 (L)/(R)`, `GNG.SLP.T2 (L)/(R)` are all named individually, not simply pooled as "hop-1 ACh interneuron" / "hop-1 GABA interneuron." Only at hop-2 (immediately upstream of OviDN) does the paper collapse everything into bare NT-based pools: `Stanley ACh interneuron`, `Stanley Glu interneuron`, with no further distinction between the neurons inside each pool. **Decision (this session, superseding an earlier plan — see Current Status): rather than mirror this hop-1-individual / hop-2-pooled asymmetry for the "Other" neurons, the recreation now pools almost everything by NT type at both hops, with only two deliberate named exceptions** (see below). This is a simplification, not an attempt to replicate the paper's own inconsistency.

**Data sources:**
- `connections_princeton.csv`: raw directed edge list, `[pre_root_id, post_root_id, neuropil, syn_count, nt_type]`, ~5.3M rows (v783).
- `groups.json`: neuron root ID → group label, keyed by materialization (`"783"` / `"630"`). Paper-derived ground truth for circuit membership. Groups: `Ir94e`, `GNG.SLP.T1 (L)`, `GNG.SLP.T1 (R)`, `GNG.SLP.T2 (L)`, `GNG.SLP.T2 (R)`, `Earmuff`, `Stanley ACh interneuron`, `Stanley Glu interneuron`, `OviDN`. Unmapped → resolved via `bucket_unknown` (see Current Status). **Root IDs are not interchangeable across the `"783"`/`"630"` sections except by coincidence** — they churn on re-proofreading (see Mechanical Note).
- `new.ipynb`: pipeline notebook, both v783 and v630 branches. **Now contains two parallel v783 bucketing sections** — see Current Status / Open Items.
- `filtered_cell_types.csv`: FlyWire Codex cell-type annotations (`root_id`, `primary_type`, `additional_type(s)`) for the 67 v783 "Other" neurons.
- `neurons.csv`: whole-brain per-neuron table from FlyWire, including NT predictions. Columns: `root_id`, `group`, `nt_type`, `nt_type_score`, `da_avg`, `ser_avg`, `gaba_avg`, `glut_avg`, `ach_avg`, `oct_avg`. `nt_type`/`nt_type_score` are FlyWire's own committed per-neuron call (blank/`0.0` when the model doesn't clear FlyWire's internal confidence bar); the `*_avg` columns are the mean per-synapse softmax score for each transmitter class, averaged across that neuron's presynapses brain-wide. **Important: this table's `nt_type` reflects the neuron's entire brain-wide synaptic output, not just its synapses within the filtered Ir94e→OviDN circuit.**
- `neuron_group_edge_list.csv`: neuron-level `filtered_edge_list.csv` with `pre_group`/`post_group` columns attached (new this session) — the input to `classify_group_members` (see Current Status) and to the final `groupby` that produces `grouped_edge_list.csv`.
- `id_to_group.csv` / `group_to_id.csv` (new this session): flat root-ID→group lookup and its reverse (group→list of root IDs), written out for spot-checking which neurons landed in which bucket.
- Outputs: `filtered_edge_list.csv` / `630_filtered_edge_list.csv` (shortest-path-filtered, per-neuron-pair), `grouped_edge_list.csv` / `630_grouped_edge_list.csv` (aggregated to group-pair level, feeds the Sankey).

**Mechanical note (still relevant):** FlyWire root IDs churn whenever a neuron is re-proofread/re-segmented, even if biologically the same neuron. A naive root-ID diff between v630 and v783 neuron sets will overcount "new" neurons. Matching across materializations properly likely requires supervoxel IDs or nucleus IDs via FlyWire's changelog/lineage API, not raw root-ID comparison.

---

## Current Status

**v783 named-group pipeline:** stable, no open bugs. Shortest-path (≤3 hops) → filter → group, correctly using a `DiGraph`. `Ir94e,Ir94e,326` (self-loop) is computed correctly and is deliberately excluded from the rendered Sankey (see below), not from the underlying data.

**v630 named-group pipeline:** validated — all 15 named-group edges match the published paper exactly (see earlier changelog entries).

**v783 "Other"-neuron bucketing scheme — substantially reworked this session.** The plan from the previous session (weight-promote several hop-1 cell types, pure-NT-pool the final hop, mirroring the paper's own asymmetry) has been **superseded**. Current approach, in the `## Highlighting important cell types` section of `new.ipynb` (the more-refined of the two parallel sections — see Open Items):

- **Base rule: pool almost everything by NT type, split by hop** (`1° ACH interneuron`, `1° GABA interneuron`, `1° GLUT interneuron`, `1° SER interneuron`, `2° ACH interneuron`, `2° GABA interneuron`, `2° GLUT interneuron`), rather than the earlier weight-threshold cell-type promotion (`hop1_named`/`hop2_named` computed via a `≥100 synapses` rule are still computed in the notebook but are now unused/commented out — a deliberate simplification, not an oversight).
- **Two, and only two, cell types are still named explicitly as their own singleton nodes:** `CB0159` (by far the heaviest-weight unknown cell type — 1,813 synapses from Ir94e alone) and `VP5+Z_adPN` (the bridge neuron — see below). The earlier candidate list (`CB0159`, `SLP234`, `CB0437`) has been narrowed to just these two.
- **The 5 NT-unresolved ("low-confidence") neurons get a hop-aware split**, not a flat bucket: `1° Unknown` / `2° Unknown` (naming decided this session — the fuller `(NT unresolved)` framing was considered and dropped for brevity, on the reasoning that the methodology is documented elsewhere for anyone who needs it).

**Bug fixed and confirmed this session — self-loop contamination of the hop-1/hop-2 split.** `all_hop1_interneurons` (the set meant to represent "all neurons one hop downstream of Ir94e") was being computed as `set(edge_list[edge_list['pre_root_id'].isin(IR94E)]['post_root_id'])` with no exclusion of `IR94E` itself. Because of the real Ir94e→Ir94e self-loop, **4 Ir94e neurons are themselves targets of other Ir94e neurons**, so they leaked into this set. Since this set seeds the hop-2 edge query (`hop2_edges = edge_list[edge_list['pre_root_id'].isin(all_hop1_interneurons) & ...]`), every ordinary hop-1 edge originating from one of those 4 Ir94e neurons was being re-captured a second time as a "hop-2" edge. Quantified impact: 21 of 90 hop-2-edges rows (526 of 1,884 synapses) were leaked hop-1 edges, and this alone was enough to spuriously promote `CB0159` into `hop2_named` with zero genuine hop-2 signal. **Fix:** `all_hop1_interneurons = set(edge_list[edge_list['pre_root_id'].isin(IR94E)]['post_root_id']) - IR94E`. Confirmed fixed by rerunning: `hop2_named` now correctly resolves to `{AVLP315, CB0550, SMP550, VESa2_P01, SLP236}` with no `CB0159`. Downstream impact on the *final* bucketing turned out to be a lucky non-issue (the `if/elif` priority order meant `CB0159`'s actual neurons were always hop1-classified regardless), but the underlying set was still wrong and is now fixed at the source.

**New diagnostic tool this session — `classify_group_members`.** Given the neuron-level edge list with `pre_group`/`post_group` attached, this function takes a group label and determines, per underlying neuron, whether it plays a single consistent topological role (receives from Ir94e only → "1° role"; receives from an intermediate pool and feeds OviDN → "2°/final-hop role") or spans both ("TRUE BRIDGE" — receives from Ir94e *and* sends to OviDN in the same neuron). Sweeping this across every group in the circuit surfaced exactly two structural problems, which turned out to have **two different root causes**:

- **`VP5+Z_adPN` (root ID `720575940620445062`) is a true single-neuron bridge**, confirmed via the earlier per-edge trace (receives from `CB0437`'s member and directly from `Ir94e`; sends directly to both `OviDN` and `Stanley Glu interneuron`). Before this was carved out as its own node, it was inflating the `1° ACH interneuron` pool with a spurious internal self-loop (`CB0437 → 1° ACH interneuron` became `1° ACH interneuron → 1° ACH interneuron` once `CB0437`'s members were folded into the generic pool). **Fixed by pulling it out as its own named node** — see above.
- **`Unknown` (the 5 NT-unresolved neurons) was heterogeneous, not a true bridge** — none of its 5 individual neurons plays a dual role; rather, 2 of the 5 are purely hop-1 (fed only by Ir94e) and 3 are purely hop-2/final-hop (fed by intermediate pools, feeding OviDN), so the *group* spanned two roles even though no single member did. **Fixed by splitting into `1° Unknown` / `2° Unknown`** using each neuron's own hop-1/hop-2 membership (from `unknown_hop1_interneurons` / `unknown_hop2_interneurons`) rather than a flat catch-all label.
- **`Earmuff` was also flagged as `TRUE BRIDGE`, correctly and expectedly** — this is the paper-documented direct-to-OviDN bypass (already in `groups.json`, not something requiring a code fix). Its flag by the same classifier is a good sign the tool is working, not a new finding.
- **`Ir94e` was also flagged as multi-role**, attributable to the same self-loop mechanism described above (some Ir94e neurons are simultaneously "Ir94e" and, pre-fix, technically "1°-adjacent"). Believed resolved as a side effect of the `all_hop1_interneurons` fix, but **not yet independently reconfirmed by rerunning the full `classify_group_members` sweep after all fixes landed** — flagged in Open Items rather than marked resolved, per this doc's own rule about not calling something fixed without rerun confirmation.

**Sankey layout — manual node positioning implemented.** Plotly's automatic Sankey layout couldn't infer the intended tiered structure once the graph grew past the original ~9-node version (see previous session's open item). Fixed via `arrangement='snap'` plus an explicit per-node `x` coordinate assigned by role (`Ir94e` → 0, hop-1/named/promoted nodes → 0.25, bridge/unknown nodes → 0.5, hop-2 nodes → 0.75, `OviDN` → 1), with header annotations (`"1° interneuron"`, `"Bridge..."`, `"2° interneuron"`) added above the corresponding columns for readability. Same-`pre_group`/`post_group` edges (i.e., any self-loop, including the real Ir94e→Ir94e one) are now explicitly filtered out of the rendered Sankey (`if row['pre_group'] == row['post_group']: continue`) while remaining correctly represented in the underlying `grouped_edge_list.csv` — matches the standing recommendation to keep reporting the self-loop's value separately from the diagram itself.

---

## Open / Next Steps

1. **Resolve the two-parallel-pipeline situation in `new.ipynb`.** The notebook currently contains both `## Highlighting important cell types` (the refined bucketing described above: `CB0159`/`VP5+Z_adPN` named, hop-split `Unknown`) and a later `## By NT type only` section (an earlier, simpler version: flat `Unknown`, no named exceptions). Both write to the same `grouped_edge_list.csv` filename — if run top-to-bottom, the later (simpler) section silently overwrites the former's output. Needs a decision: delete/archive the superseded section, or rename outputs so both can coexist intentionally.
2. **Rerun the full `classify_group_members` sweep after all current fixes** (self-loop exclusion, `VP5+Z_adPN`/`CB0159` carve-out, `Unknown` hop-split) and confirm every group now shows exactly one role, including `Ir94e` specifically (believed but not yet reconfirmed — see Current Status).
3. Run the same weight-based / role-based unknown-neuron characterization on **v630's** unknown neurons (still outstanding from before this session).
4. Quantify the v630→v783 growth deltas for the 15 named edges as a citable "what's genuinely new" finding (numbers already sit in the validation table in the Changelog).
5. Revisit the original paper's methods section for path-weighting details (weighted vs. unweighted shortest paths) — low priority.
6. Still open: whether to commit this handoff doc into the repo so it syncs automatically, instead of needing manual re-upload each time.
7. Prepare the external progress update (in progress, being handled independently outside of Claude).

---

## Changelog

### Bucketing scheme reworked; two structurally-distinct "bridge-like" bugs found and fixed; Sankey layout fixed via manual node positioning (this session)

- **Built `classify_group_members`:** a diagnostic that, for any group label, checks each underlying neuron's incoming/outgoing group memberships and classifies it as playing a "1° role," a "2°/final-hop role," or a "TRUE BRIDGE" role (both). Swept across every group in the circuit.
- **Two distinct root causes found under the same visual symptom** (a Sankey node that can't be placed at a single tier):
  - `VP5+Z_adPN`: a genuine single-neuron bridge (confirmed via direct edge trace: receives from `Ir94e` and `CB0437`; sends to `OviDN` and `Stanley Glu interneuron`). Fix: carve out as its own named singleton node, not poolable by NT.
  - `Unknown` (the 5 NT-unresolved neurons): not a single-neuron bridge at all — a heterogeneous *population*, where 2 of 5 neurons are purely hop-1 and 3 of 5 are purely hop-2/final-hop, incorrectly sharing one flat label. Fix: split into `1° Unknown` / `2° Unknown` using existing hop-membership sets. This also brings the scheme back in line with a plan from two sessions ago (give the low-confidence neurons a hop-aware bucket) that had been dropped somewhere along the way.
  - `Earmuff` was also flagged `TRUE BRIDGE` by the same tool — expected and correct, since this is the paper's own known direct-to-OviDN bypass; no fix needed, just confirms the classifier works.
  - `Ir94e` was also flagged multi-role, attributable to the self-loop bug below; believed resolved as a side effect but not yet independently reconfirmed post-fix.
- **Root-caused and fixed a real (if previously low-impact) bug:** `all_hop1_interneurons` didn't exclude `IR94E` from the set of "hop-1 targets," so the 4 Ir94e neurons that are themselves targets of the Ir94e→Ir94e self-loop were leaking their own ordinary hop-1 edges into the hop-2 edge query, double-counting them under a different label. Quantified: 21/90 hop-2 rows (526/1,884 synapses) were this kind of leak, enough on its own to spuriously qualify `CB0159` for `hop2_named` promotion (with literally zero genuine hop-2 signal for that type). Fix: subtract `IR94E` from `all_hop1_interneurons`. Confirmed via rerun that `hop2_named` no longer includes `CB0159`.
- **Bucketing scheme simplified/narrowed:** earlier plan (weight-promote a handful of hop-1 cell types via a `≥100`-synapse threshold, pure-NT-pool the final hop only, mirroring the paper's own hop-1-named/hop-2-pooled asymmetry) has been replaced with: pool everything by NT type at both hops, with exactly two named exceptions (`CB0159` for weight/prominence, `VP5+Z_adPN` for genuine bridge structure). The threshold-based `hop1_named`/`hop2_named` machinery is still present in the notebook but no longer consulted by `bucket_unknown` — left in place but effectively dead code for now.
- **Sankey rendering fixed:** manual `x` node-coordinate assignment (by role: Ir94e / 1° / bridge-or-unknown / 2° / OviDN) plus `arrangement='snap'`, replacing Plotly's automatic layout, which could not find a clean tiered arrangement once the diagram grew past ~9 nodes. Header annotations added above each tier. Same-group (self-loop) edges — including the real, biologically-confirmed `Ir94e→Ir94e` edge — are now explicitly excluded from the rendered links while remaining intact in the underlying grouped data, per the standing recommendation to report that value separately rather than render it.
- **New utility outputs added:** `neuron_group_edge_list.csv` (neuron-level edges with group columns attached, used as the direct input to `classify_group_members`), `id_to_group.csv` / `group_to_id.csv` (flat lookup and its reverse, for spot-checking bucket membership).

### NT confidence investigation for "Other" neurons — resolved, cell-type/hop-depth characterization complete
Full investigation prompted by noticing `AN_GNG_PRW_3` (a 2-member cell type) showed both ACH and GABA nt_type across its members in `filtered_edge_list.csv`-derived data, contradicting the otherwise-universal pattern that cell type predicts NT.

- **Root cause confirmed:** downloaded FlyWire's dedicated per-neuron NT prediction table (`neurons.csv`, columns `nt_type`, `nt_type_score`, and per-class `*_avg` mean-softmax scores). Both `AN_GNG_PRW_3` neurons show near-tied top-2 scores (margins 0.08 and 0.00) and blank `nt_type`/`nt_type_score=0.0` — i.e., FlyWire's own pipeline already flags these as unreliable; the ACH/GABA split we saw was never a real biological mix, it was two weak, near-tied guesses.
- **Generalized the check to all 67 unknown neurons**, independently two ways (margin-based threshold, and the `nt_type`-is-NaN flag) — both land on the identical set of 5 low-confidence neurons:
  - `720575940604891360` (`AN_GNG_PRW_3`) — GABA (0.45) / ACH (0.37), margin 0.08
  - `720575940623207885` (`AN_GNG_PRW_3`) — GABA (0.39) / ACH (0.39), margin 0.00
  - `720575940608471900` (`CB0627`) — GABA (0.38) / GLUT (0.34), margin 0.04
  - `720575940622319715` (`SMP286`) — GLUT (0.46) / GABA (0.43), margin 0.03
  - `720575940636990064` (`SLP212c`) — DA (0.32) / SER (0.30) / ACH (0.20), margin 0.02
  - Mechanism: `neurons.csv`'s `*_avg` columns are a mean of per-synapse softmax scores, not a calibrated whole-neuron probability — a small top1/top2 margin means individual synapses disagree with each other about transmitter identity.
  - **Decision: keep all 5 in the dataset** (they're only ambiguous on NT *sign*, not on whether the connectivity is real). 4 of the 5 are the sole representative of their cell type in the circuit; only `CB0627` has a confident same-cell-type neighbor (`720575940625005239`).
- **Cell type confirmed as a clean grouping axis for the 62 confident neurons.** 45 distinct `primary_type` values (32 singletons, 13 multi-member). All 13 multi-member cell types are NT-homogeneous once the 5 low-confidence neurons are excluded.
- **Weight concentration confirmed.** Top 10 of 67 neurons account for 60.8% of total Other-involved connectivity weight; top 10 of 45 confident cell types account for 74.0%. Two `CB0159` neurons alone absorb 75.2% of the entire Ir94e→Other flow (1,813 of 2,411 synapses).
- **Hop-depth structure confirmed clean.** 29 clean hop-1 (receive from Ir94e only), 37 clean final-hop (send to OviDN only), exactly 1 true single-hop bridge (`VP5+Z_adPN`), zero ambiguous mid-chain neurons.
- **Grouping strategy from this investigation (superseded — see this session's entry above):** originally planned to weight-promote hop-1 cell types and pure-NT-pool the final hop, mirroring the paper's own asymmetry. Replaced this session with a simpler NT-pool-everywhere-plus-two-named-exceptions scheme.

### v630 pipeline validated against published ground truth
All 15 named edges in `630_grouped_edge_list.csv` now match the paper exactly:

| Edge                              | Paper (target) | v630 (validated) | v783 (current) |
| --------------------------------- | -------------- | ---------------- | -------------- |
| Ir94e → GNG.SLP.T1 (L)            | 173            | 173              | 251            |
| Ir94e → GNG.SLP.T1 (R)            | 178            | 178              | 287            |
| Ir94e → GNG.SLP.T2 (L)            | 17             | 17               | 19             |
| Ir94e → GNG.SLP.T2 (R)            | 22             | 22               | 36             |
| Ir94e → Earmuff                   | 20             | 20               | 21             |
| GNG.SLP.T1 (L) → ACh interneurons | 78             | 78               | 84             |
| GNG.SLP.T1 (L) → Glu interneurons | 13             | 13               | 19             |
| GNG.SLP.T1 (R) → ACh interneurons | 33             | 33               | 43             |
| GNG.SLP.T1 (R) → Glu interneurons | 8              | 8                | 8              |
| GNG.SLP.T2 (L) → Glu interneurons | 37             | 37               | 34             |
| GNG.SLP.T2 (R) → Glu interneurons | 25             | 25               | 34             |
| Earmuff → ACh interneurons        | 7              | 7                | 10             |
| Earmuff → OviDNs (direct)         | 83             | 83               | 102            |
| ACh interneurons → OviDNs         | 110            | 110              | 142            |
| Glu interneurons → OviDNs         | 31             | 31               | 34             |

All but one named edge are equal-or-larger in v783 than v630 — consistent with continued proofreading adding synapses to already-real connections, not spurious new circuitry. The one exception: **GNG.SLP.T2 (L) → Glu interneurons drops slightly, 37→34**, not yet investigated.

Two real bugs were behind the previously-bad v630 numbers:
1. **Shortest-path filter computed but never applied to the final output** — fixed by merging `path_edges_df` against the raw edge list to produce `630_filtered_edge_list.csv`.
2. **Earmuff's v630 root ID had been copied from the v783 entry** instead of a distinct, correct v630-era ID. Self-caught and fixed.

**Resolved — Ir94e→Ir94e self-loop:** the self-loop (93 synapses in v630, 326 in v783) survives the identical ≤3-hop shortest-path filter under the same materialization the paper itself used. Most likely explanation: the original authors deliberately excluded it from the Sankey since self-loops aren't representable as flow. The v783 recreation now follows the same convention explicitly in code (see this session's Sankey-rendering entry above).

**Resolved — Earmuff routing:** confirmed matching the paper exactly — Earmuff → Stanley ACh interneuron (7) *and* Earmuff → OviDN direct (83). (Note: `VP5+Z_adPN` was later found doing the same direct-bypass thing — see above.)

**Confirmed — "Other" dominance:** real at both snapshots, not a pipeline artifact. `Ir94e → Other` is 1,544 in the validated v630 circuit vs. 2,411 in v783.

**Direction-flag design choice confirmed sound:** all three v630 hop-fetches deliberately request both `upstream` and `downstream` connectivity — confirmed this doesn't compromise correctness since `G` is a true `DiGraph`.

### v630 pipeline debugging (leading up to validation)
- Bidirectional direction flags across all three hops: intentional experiment, not a bug.
- `groups.json["630"]`'s OviDN entry count was a real, earlier-caught issue (four entries → five)
- The actual bug behind the inflated "Other" numbers was the shortest-path filter being disconnected from the final grouped output (see validated entry above).

### v783 pipeline established from an earlier thread
- Fixed: `nx.from_pandas_edgelist` defaulting to undirected `Graph` instead of `DiGraph`, which let `all_shortest_paths` traverse backwards and inflated "Other" ~46% (Ir94e→Other: 4,439 undirected → 2,411 directed).
- Fixed: neuropil-split rows for the same `(pre_root_id, post_root_id)` pair need `groupby(...).sum()`, not naive `drop_duplicates()`.
- Added the ≤3-hop (`len(path) <= 4` nodes) cap matching the paper's own methodology; reduced discovered interneurons 119→84, path edges 466→302.