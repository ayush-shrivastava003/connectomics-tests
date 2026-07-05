# Ir94e → OviDN Sankey Recreation — Project Handoff

## How to use this doc
**Current Status** below is the fast-orientation section — read this first. **Changelog** is the history/reasoning trail, newest entry first — check it if something in Current Status needs justification, or if you're picking this project back up after a major commit. When adding a new changelog entry: only mark something "fixed"/"resolved" if it's been confirmed by actually rerunning and inspecting output, not just described as fixed in conversation — that distinction has caused real confusion in this project's history (see changelog). Don't rewrite past entries except to correct factual errors.

**Process note (how files move around this project):** the code/data live in the `ayush-shrivastava003/connectomics-tests` GitHub repo, connected to this Project. That sync only refreshes at the *start* of a new chat — it won't pick up mid-conversation commits. Workflow: between commits, new data file iterations get uploaded directly into the active chat (provisional, not yet committed); after a major commit, a new chat gets started (often to work a different angle of the project), which picks up the latest repo state fresh. This doc is currently a separate manual Project upload, not part of the repo, so it needs the same manual re-upload treatment as the CSVs whenever it's updated.

---

## Project overview

**Goal:** Recreate (programmatically, via FlyWire connectomics data) a published Sankey diagram showing how Ir94e neurons (~18 olfactory neurons) connect to OviDN neurons (~5 neurons) through intermediate interneurons in *Drosophila*. The original figure was built from FlyWire materialization **v630**; current work also uses the newer **v783**, which contains additional connectivity not reflected in the original paper. Secondary goal: characterize what's genuinely new in v783 vs. v630.

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

Color convention: ACh = excitatory (green); GABA and Glu = inhibitory (pink/red) — Glu is inhibitory here via GluCl receptors, not by neurotransmitter class. No Ir94e→Ir94e self-loop appears in the original figure (see Changelog — resolved).

**Data sources:**
- `connections_princeton.csv`: raw directed edge list, `[pre_root_id, post_root_id, neuropil, syn_count, nt_type]`, ~5.3M rows (v783).
- `groups.json`: neuron root ID → group label, keyed by materialization (`"783"` / `"630"`). Paper-derived ground truth for circuit membership. Groups: `Ir94e`, `GNG.SLP.T1 (L)`, `GNG.SLP.T1 (R)`, `GNG.SLP.T2 (L)`, `GNG.SLP.T2 (R)`, `Earmuff`, `Stanley ACh interneuron`, `Stanley Glu interneuron`, `OviDN`. Unmapped → `"Other"`. **Root IDs are not interchangeable across the `"783"`/`"630"` sections except by coincidence** — they churn on re-proofreading (see Mechanical Note).
- `new.ipynb`: pipeline notebook, both v783 and v630 branches.
- Outputs: `filtered_edge_list.csv` / `630_filtered_edge_list.csv` (shortest-path-filtered, per-neuron-pair), `grouped_edge_list.csv` / `630_grouped_edge_list.csv` (aggregated to group-pair level, feeds the Sankey).

**Mechanical note (still relevant):** FlyWire root IDs churn whenever a neuron is re-proofread/re-segmented, even if biologically the same neuron. A naive root-ID diff between v630 and v783 neuron sets will overcount "new" neurons. Matching across materializations properly likely requires supervoxel IDs or nucleus IDs via FlyWire's changelog/lineage API, not raw root-ID comparison.

---

## Current Status

**v783 pipeline:** stable, no open bugs. Shortest-path (≤3 hops) → filter → group, correctly using a `DiGraph`. Current output: `Ir94e,Ir94e,326` (self-loop), `Ir94e,Other,2411`.

**v630 pipeline:** now validated — **all 15 named-group edges match the published paper exactly** (see table in latest changelog entry). This also validates the ≤3-hop methodology and the group-ID mapping against real external ground truth, not just internal consistency.

**Resolved:** Ir94e self-loop question, Earmuff routing structure.
**Confirmed but not yet actioned:** "Other" group dominance is real at both snapshots, not a pipeline artifact (deprioritized — characterizing those neurons picked up later, by choice).

---

## Open / Next Steps

1. Characterize the Other/unknown neurons (deprioritized — pick up when ready). Start with ranking by summed weight in both materializations to see if the signal concentrates in a few high-weight relay candidates or spreads thin.
2. Quantify the v630→v783 growth deltas for the 15 named edges as a citable "what's genuinely new" finding — the numbers are already sitting in the validation table below.
3. Decide how (or whether) to annotate the Ir94e self-loop in any write-up or figure, given it's real but deliberately Sankey-incompatible.
4. Revisit the original paper's methods section for path-weighting details (weighted vs. unweighted shortest paths) — lower priority now that the self-loop question is resolved by other means.
5. Consider committing this handoff doc into the repo so it syncs automatically with the GitHub connection instead of needing manual re-upload.

---

## Changelog

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

**Resolved — Earmuff routing:** confirmed matching the paper exactly — Earmuff → Stanley ACh interneuron (7) *and* Earmuff → OviDN direct (83), the same dual pathway (feeds the interneuron layer *and* bypasses it) described in the paper. Not a structural mismatch.

**Confirmed, not fully resolved — "Other" dominance:** real at both snapshots, not a pipeline artifact. `Ir94e → Other` is 1,544 in the now-validated v630 circuit vs. 2,411 in v783 — both substantial relative to the ~410 reaching named groups. Characterizing which neurons these are is deferred by choice, not blocked.

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