# Ir94e → OviDN Sankey Recreation — Project Handoff

## How to use this doc
**Current Status** below is the fast-orientation section — read this first. **Changelog** is the history/reasoning trail, newest entry first — check it if something in Current Status needs justification, or if you're picking this project back up after a major commit. When adding a new changelog entry: only mark something "fixed"/"resolved" if it's been confirmed by actually rerunning and inspecting output, not just described as fixed in conversation — that distinction has caused real confusion in this project's history (see changelog). Don't rewrite past entries except to correct factual errors.

**Process note (how files move around this project):** the code/data live in the `ayush-shrivastava003/connectomics-tests` GitHub repo, connected to this Project. That sync only refreshes at the *start* of a new chat — it won't pick up mid-conversation commits. Workflow: between commits, new data file iterations get uploaded directly into the active chat (provisional, not yet committed); after a major commit, a new chat gets started (often to work a different angle of the project), which picks up the latest repo state fresh. This doc is currently a separate manual Project upload, not part of the repo, so it needs the same manual re-upload treatment as the CSVs whenever it's updated.

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

Color convention: ACh = excitatory (green); GABA and Glu = inhibitory (pink/red) — Glu is inhibitory here via GluCl receptors, not by neurotransmitter class. No Ir94e→Ir94e self-loop appears in the original figure (resolved — see Changelog).

**Important structural note on the paper's own grouping convention (new, this session):** the paper is not internally consistent in how it pools neurons by depth. At hop-1 (immediately downstream of Ir94e), each interneuron/group keeps individual identity: `Earmuff`, `GNG.SLP.T1 (L)/(R)`, `GNG.SLP.T2 (L)/(R)` are all named individually, not simply pooled as "hop-1 ACh interneuron" / "hop-1 GABA interneuron." Only at hop-2 (immediately upstream of OviDN) does the paper collapse everything into bare NT-based pools: `Stanley ACh interneuron`, `Stanley Glu interneuron`, with no further distinction between the neurons inside each pool. This asymmetry matters for how the "Other" neurons should be grouped for the Sankey (see below).

**Data sources:**
- `connections_princeton.csv`: raw directed edge list, `[pre_root_id, post_root_id, neuropil, syn_count, nt_type]`, ~5.3M rows (v783).
- `groups.json`: neuron root ID → group label, keyed by materialization (`"783"` / `"630"`). Paper-derived ground truth for circuit membership. Groups: `Ir94e`, `GNG.SLP.T1 (L)`, `GNG.SLP.T1 (R)`, `GNG.SLP.T2 (L)`, `GNG.SLP.T2 (R)`, `Earmuff`, `Stanley ACh interneuron`, `Stanley Glu interneuron`, `OviDN`. Unmapped → `"Other"`. **Root IDs are not interchangeable across the `"783"`/`"630"` sections except by coincidence** — they churn on re-proofreading (see Mechanical Note).
- `new.ipynb`: pipeline notebook, both v783 and v630 branches.
- `filtered_cell_types.csv`: FlyWire Codex cell-type annotations (`root_id`, `primary_type`, `additional_type(s)`) for the 67 v783 "Other" neurons.
- **`neurons.csv` (new, this session):** whole-brain per-neuron table from FlyWire, including NT predictions. Columns: `root_id`, `group`, `nt_type`, `nt_type_score`, `da_avg`, `ser_avg`, `gaba_avg`, `glut_avg`, `ach_avg`, `oct_avg`. `nt_type`/`nt_type_score` are FlyWire's own committed per-neuron call (blank/`0.0` when the model doesn't clear FlyWire's internal confidence bar); the `*_avg` columns are the mean per-synapse softmax score for each transmitter class, averaged across that neuron's presynapses brain-wide (per Eckstein/Bates et al. 2024 methodology — see Changelog). **Important: this table's `nt_type` reflects the neuron's entire brain-wide synaptic output, not just its synapses within the filtered Ir94e→OviDN circuit** — this is a different (larger) evidence base than the implicit per-neuron NT you can derive from `filtered_edge_list.csv`.
- Outputs: `filtered_edge_list.csv` / `630_filtered_edge_list.csv` (shortest-path-filtered, per-neuron-pair), `grouped_edge_list.csv` / `630_grouped_edge_list.csv` (aggregated to group-pair level, feeds the Sankey).

**Mechanical note (still relevant):** FlyWire root IDs churn whenever a neuron is re-proofread/re-segmented, even if biologically the same neuron. A naive root-ID diff between v630 and v783 neuron sets will overcount "new" neurons. Matching across materializations properly likely requires supervoxel IDs or nucleus IDs via FlyWire's changelog/lineage API, not raw root-ID comparison.

---

## Current Status

**v783 named-group pipeline:** stable, no open bugs. Shortest-path (≤3 hops) → filter → group, correctly using a `DiGraph`. Current output: `Ir94e,Ir94e,326` (self-loop), `Ir94e,Other,2411`.

**v630 named-group pipeline:** validated — all 15 named-group edges match the published paper exactly (see earlier changelog entries). This also validates the ≤3-hop methodology and the group-ID mapping against real external ground truth, not just internal consistency.

**v783 "Other" neuron characterization (major progress this session):**
- **NT confidence fully investigated and resolved.** Of the 67 unknown neurons, 62 have a confident NT call in `neurons.csv` that **exactly agrees** with the implicit NT derivable from `filtered_edge_list.csv` (verified via a full merge/comparison across all 67 — zero disagreements outside the 5 flagged below). The remaining **5 are genuinely low-confidence**, confirmed two independent ways (top1/top2 margin ≤0.08 on the `*_avg` columns; and FlyWire's own `nt_type`/`nt_type_score` blank/`0.0` flag) — both checks land on the identical set:
  - `720575940604891360` (`AN_GNG_PRW_3`) — GABA (0.45) / ACH (0.37), margin 0.08
  - `720575940623207885` (`AN_GNG_PRW_3`) — GABA (0.39) / ACH (0.39), margin 0.00
  - `720575940608471900` (`CB0627`) — GABA (0.38) / GLUT (0.34), margin 0.04
  - `720575940622319715` (`SMP286`) — GLUT (0.46) / GABA (0.43), margin 0.03
  - `720575940636990064` (`SLP212c`) — DA (0.32) / SER (0.30) / ACH (0.20), margin 0.02 (only one that's a 3-way muddle, not a clean binary tie)
  - Mechanism: `neurons.csv`'s `*_avg` columns are a **mean of per-synapse softmax scores**, not a calibrated whole-neuron probability — a small top1/top2 margin means individual synapses disagree with each other about transmitter identity, which is why FlyWire itself declines to commit to a label for these 5 (blank `nt_type`) rather than reporting a weak guess.
  - **Decision: keep all 5 in the dataset** (they're only ambiguous on NT *sign*, not on whether the connectivity is real) but report them with full score distributions rather than a forced single label. Considered and rejected dropping them or omitting their cell type from analysis — 4 of the 5 are the *only* representative of their cell type in the circuit (`AN_GNG_PRW_3` ×2, `SMP286`, `SLP212c`), so dropping would delete confirmed connectivity to fix an NT-sign ambiguity, not a connectivity question. Only `CB0627` has a confident same-cell-type neighbor in the circuit (`720575940625005239`).
- **Cell type is now confirmed as a clean grouping axis for the 62 confident neurons.** 45 distinct `primary_type` values among the 62 (32 singletons, 13 multi-member). **All 13 multi-member cell types are now fully NT-homogeneous** once the 5 low-confidence neurons are excluded — the one earlier exception (`AN_GNG_PRW_3` showing both ACH and GABA) is fully explained by the low-confidence finding above, not a real biological mix.
- **Weight concentration confirmed at both the neuron and cell-type level.** Top 10 of 67 neurons account for 60.8% of total Other-involved connectivity weight. Aggregated to cell type, it's even more concentrated: top 10 of 45 confident cell types account for 74.0% of weight. Standout candidates: two `CB0159` neurons (GABAergic) absorb **75.2% of the entire Ir94e→Other flow** (1,813 of 2,411 synapses) and are contacted by nearly all 18 Ir94e neurons — functionally as prominent as any named group, just outside the paper's diagram. `SMP550` (720575940612490958, cholinergic) has balanced in/out weight and bridges directly to both Earmuff and OviDN.
- **Hop-depth structure confirmed clean (new, this session) — this resolves the Sankey-grouping question.** Classified all 67 unknown neurons by whether they receive directly from an Ir94e-group neuron and/or send directly to an OviDN-group neuron:
  - **29 are clean hop-1** (receive from Ir94e only) — structurally parallel to `Earmuff`/`GNG.SLP.T1/T2`.
  - **37 are clean final-hop** (send to OviDN only) — structurally parallel to `Stanley ACh/Glu interneuron`.
  - **Exactly 1 true bridge**: `720575940620445062` (`VP5+Z_adPN`) receives directly from Ir94e *and* sends directly to OviDN in a single hop — structurally identical to Earmuff's own direct-to-OviDN bypass. This is a second instance of that bypass pattern, previously thought to be unique to Earmuff.
  - **Zero neurons are ambiguous mid-chain** (i.e., none receive from one Other neuron and send to another) — hop depth is a safe, nearly single-valued attribute for this neuron set, contrary to an initial worry that a neuron's shortest-path hop position might vary across different Ir94e/OviDN endpoint pairs.
  - Hop×NT bucket sizes (confident neurons only): `hop1` → ACH=9, GABA=15, GLUT=2, SER=1 (4 buckets); `final_hop` → ACH=13, GABA=11, GLUT=10 (3 buckets). Pure hop+NT pooling gives full coverage of all 67 in ~8 nodes total (7 NT buckets + 1 bridge singleton), with no residual "Other" bucket needed — cleaner and more complete than any cell-type-based promotion scheme, which necessarily leaves a residual "Other" below whatever weight threshold is chosen.

**Grouping strategy decision for the Sankey (decided, not yet implemented):** given the paper's own hop-1-individual / hop-2-pooled asymmetry (see Project Overview), the plan is a **hybrid**, not a single uniform rule for all "Other" neurons:
  - **Hop-1 unknowns:** group by cell type (weight-promoted above some threshold, TBD — candidates discussed: ≥150 total synapses gives 10 promoted types covering 74% of weight; lower thresholds give more nodes/coverage), matching the paper's practice of keeping hop-1 individually identified.
  - **Final-hop unknowns:** pool purely by NT (ACH/GABA/GLUT), matching the paper's `Stanley ACh/Glu interneuron` precedent exactly.
  - **The bridge neuron** (`720575940620445062`) should likely stay its own singleton node given the Earmuff parallel, regardless of the above.
  - **The 5 low-confidence neurons:** give them an explicit `(NT unresolved)` bucket per hop rather than folding them into a generic "Other" or dropping them — this preserves their real connectivity while being honest that their transmitter sign isn't resolved.
  - **Not yet implemented in the notebook.** Next session should pick up here.

---

## Open / Next Steps

1. **Implement the hybrid grouping scheme above in `new.ipynb`** (modify the `id_to_grp` logic in step 1.4, extend `name_to_color` to be built dynamically for promoted cell-type nodes and NT-pool nodes, regenerate `grouped_edge_list.csv`, rebuild the Sankey). Code sketches for both halves (grouping function, dynamic color-dict construction) were drafted this session and should be adapted, not re-derived from scratch.
2. **Pick the final weight threshold for hop-1 cell-type promotion** (currently unresolved — options discussed range from ≥50 synapses/20 nodes/90% coverage down to ≥200/6 nodes/61% coverage; ≥150/10 nodes/74% was the working example but not committed).
3. Run the same weight-based unknown-neuron ranking analysis on **v630's** unknown neurons (still outstanding from before this session — offered, not yet done).
4. Quantify the v630→v783 growth deltas for the 15 named edges as a citable "what's genuinely new" finding — the numbers are already sitting in the validation table in the Changelog.
5. Decide how (or whether) to annotate the Ir94e self-loop in any write-up or figure, given it's real but deliberately Sankey-incompatible.
6. Revisit the original paper's methods section for path-weighting details (weighted vs. unweighted shortest paths) — lower priority now that the self-loop question is resolved by other means.
7. Consider committing this handoff doc into the repo so it syncs automatically with the GitHub connection instead of needing manual re-upload (still an open question, unresolved).

---

## Changelog

### NT confidence investigation for "Other" neurons — resolved, cell-type/hop-depth characterization complete (this session)

Full investigation prompted by noticing `AN_GNG_PRW_3` (a 2-member cell type) showed both ACH and GABA nt_type across its members in `filtered_edge_list.csv`-derived data, contradicting the otherwise-universal pattern that cell type predicts NT.

- **Root cause confirmed:** downloaded FlyWire's dedicated per-neuron NT prediction table (`neurons.csv`, columns `nt_type`, `nt_type_score`, and per-class `*_avg` mean-softmax scores). Both `AN_GNG_PRW_3` neurons show near-tied top-2 scores (margins 0.08 and 0.00) and blank `nt_type`/`nt_type_score=0.0` — i.e., FlyWire's own pipeline already flags these as unreliable; the ACH/GABA split we saw was never a real biological mix, it was two weak, near-tied guesses.
- **Generalized the check to all 67 unknown neurons**, independently two ways (margin-based threshold, and the `nt_type`-is-NaN flag) — both land on the identical set of 5 low-confidence neurons (see Current Status for the list). No other unknown neuron is affected.
- **Verified `filtered_edge_list.csv`'s implicit NT (derived from a neuron's outgoing edges within the filtered circuit) agrees with `neurons.csv`'s whole-brain NT call for all 62 confident neurons** — the two data sources are fully consistent everywhere except the 5 flagged neurons, where they diverge for a documented, understood reason (not a data quality problem). Practical implication: no need to prefer one NT source over the other wholesale; either is fine for the 62, and the dedicated dataset with full score distributions is authoritative for the 5.
- **Decision: keep all 5 low-confidence neurons in the dataset.** 4 of 5 are the sole representative of their cell type in the circuit, so excluding them would delete real, confirmed connectivity to resolve an NT-sign ambiguity, not a connectivity question. Report them with full score distributions instead of a forced single label.
- **Re-checked cell-type/NT homogeneity with the 5 excluded: fully clean.** All 13 multi-member cell types among the 62 confident neurons are now NT-homogeneous with no exceptions — confirms cell type is a safe basis for both grouping and NT-based coloring, as long as the 5 low-confidence neurons are excluded from that specific inference.
- **Weight-based ranking completed for v783** (this was open item #1 from before this session): confirms the "Other" signal concentrates rather than spreading thin. Top 10/67 neurons = 60.8% of weight; top 10/45 confident cell types = 74.0% of weight. Two `CB0159` neurons alone absorb 75.2% of all Ir94e→Other flow. `SMP550` flagged as a balanced-flow bridge candidate touching both Earmuff and OviDN.
- **Hop-depth structural analysis (new):** classified every unknown neuron by direct adjacency to Ir94e/OviDN. Result is clean and close to bimodal: 29 clean hop-1, 37 clean final-hop, exactly 1 true single-hop bridge (`720575940620445062`, `VP5+Z_adPN` — a second instance of the Earmuff-style direct-bypass pattern), zero ambiguous mid-chain neurons. This matters because it validates that "hop position" is safe to use as a grouping axis — there was a real concern going in that a neuron's shortest-path depth could vary across different specific Ir94e/OviDN endpoint pairs, since paths range from 2 to 4 nodes; empirically this isn't happening in this neuron set.
- **Grouping strategy decided:** noticed the paper itself is asymmetric — hop-1 groups are individually named (`Earmuff`, `GNG.SLP.T1/T2 (L)/(R)`), hop-2 groups are pure NT pools (`Stanley ACh/Glu interneuron`) with no further identity. Decided to mirror this rather than pick one scheme uniformly: hop-1 unknowns get weight-promoted cell-type grouping (preserves individual identity like the paper does at that layer), final-hop unknowns get pure NT pooling (matches the paper's own Stanley-layer precedent exactly). Not yet implemented — see Open/Next Steps.

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

All but one named edge are equal-or-larger in v783 than v630 — consistent with continued proofreading adding synapses to already-real connections, not spurious new circuitry. The one exception: **GNG.SLP.T2 (L) → Glu interneurons drops slightly, 37→34**, a small decrease rather than the usual growth. Not yet investigated — plausibly a re-proofreading correction (e.g. a split/merge reassigning a few synapses) rather than anything wrong with the pipeline, but worth a look if the "characterize what changed" pass ever covers named edges too, not just Other.

Two real bugs were behind the previously-bad v630 numbers:
1. **Shortest-path filter computed but never applied to the final output.** `path_edges_df` was correctly computed via `all_shortest_paths`, but the cell building `630_grouped_edge_list.csv` re-read the raw, unfiltered `630_edge_list.csv` directly instead of merging `path_edges_df` in first. This is why early v630 output showed enormous uncapped "Other" totals (e.g. `Other,Other,74943`) — that was the entire raw 3-hop neighborhood, not a shortest-path-restricted circuit. Fixed by merging `path_edges_df` (renamed to `pre`/`post`) against the raw edge list to produce `630_filtered_edge_list.csv`, and grouping that instead — mirrors the v783 pattern exactly.
2. **Earmuff's v630 root ID had been copied from the v783 entry** instead of a distinct, correct v630-era ID. Self-caught and fixed; confirmed by the exact 7/83 match above.

**Resolved — Ir94e→Ir94e self-loop:** the self-loop (93 synapses in v630, 326 in v783) survives the identical ≤3-hop shortest-path filter under the *same materialization the paper itself used*. This rules out "didn't exist in v630" and "genuinely new in v783." Most likely explanation: the original authors deliberately excluded it from the Sankey since self-loops aren't representable as flow — not that it was missed. Recommendation: keep excluding it from the Sankey, keep reporting the value separately.

**Resolved — Earmuff routing:** confirmed matching the paper exactly — Earmuff → Stanley ACh interneuron (7) *and* Earmuff → OviDN direct (83), the same dual pathway (feeds the interneuron layer *and* bypasses it) described in the paper. Not a structural mismatch. (Note: as of this session, a second, previously-unknown neuron — `VP5+Z_adPN`, `720575940620445062` — has been found doing the same direct-bypass thing; see above.)

**Confirmed, not fully resolved — "Other" dominance:** real at both snapshots, not a pipeline artifact. `Ir94e → Other` is 1,544 in the now-validated v630 circuit vs. 2,411 in v783 — both substantial relative to the ~410 reaching named groups. As of this session, this is no longer just "confirmed but deprioritized" — the characterization work above (NT, cell type, weight ranking, hop depth) is substantially complete for v783; only the v630-side equivalent analysis and the actual Sankey re-implementation remain.

**Direction-flag design choice confirmed sound:** all three v630 hop-fetches deliberately request both `upstream` and `downstream` connectivity (an experiment testing whether a wider candidate neighborhood improves the subgraph vs. forward-only fetching). Confirmed this doesn't compromise correctness — `G` is still a true `DiGraph` built from `(pre, post)` pairs that each carry the synapse's real direction, so `all_shortest_paths` only ever traverses forward regardless of how broadly edges were fetched. The exact ground-truth match above was achieved with this bidirectional fetch still in place, which is itself empirical confirmation.

### v630 pipeline debugging (leading up to validation)
- The bidirectional direction flags across all three hops were initially suspected as an unintentional bug — clarified as an intentional experiment, not a bug (see validated entry above for why it doesn't compromise correctness).
- `groups.json["630"]`'s OviDN entry count was a real issue earlier in the repo's history — four entries, later updated to five (confirmed via git history) — already fixed by the time this conversation's files were shared, which is why it looked like a non-issue on later inspection here. The `["630"]` vs `["783"]` key-usage concern likely followed the same pattern: a real, earlier-caught issue already resolved before this thread started, rather than a live bug or a Claude miscount.
- The actual bug behind the inflated "Other" numbers turned out to be neither of the above — it was the shortest-path filter being disconnected from the final grouped output (see validated entry above).

### v783 pipeline established (prior to this thread)
- Fixed: `nx.from_pandas_edgelist` defaulting to undirected `Graph` instead of `DiGraph`, which let `all_shortest_paths` traverse backwards and inflated "Other" ~46% (Ir94e→Other: 4,439 undirected → 2,411 directed).
- Fixed: neuropil-split rows for the same `(pre_root_id, post_root_id)` pair need `groupby(...).sum()`, not naive `drop_duplicates()` (which silently lost ~1.3% of total synapses). Confirmed this didn't change final grouped output (unweighted graph, final groupby re-sums regardless) but was still necessary for `filtered_edge_list.csv` correctness.
- Confirmed correct: `path_edges_df.drop_duplicates()` before merging — no weight column exists on that dataframe, so duplicates are pure re-discoveries across different Ir94e/OviDN seed pairs; deduping loses nothing.
- Added the ≤3-hop (`len(path) <= 4` nodes) cap matching the paper's own methodology; reduced discovered interneurons 119→84, path edges 466→302.
- Retracted: earlier suggestion that shortest-path search might be unnecessary overhead given `groups.json` already has curated membership — wrong, since the large "Other" signal would've been invisible under a naive group-only filter.