# Connectomics Tests

Using [Flywire](https://flywire.ai) to learn about connectomics for future projects at the Lyu Lab.

**Current goal**: recreate the Sankey from Fig. 3A of [this paper](https://www.sciencedirect.com/science/article/pii/S2211124724009756?via%3Dihub#sec2) from Stanley et al., which shows how gustatory receptor neurons (GRNs) expressing Ir94e connect to oviposition descending neurons (OviDNs) through 1-2 layers of interneurons.

Ir94e GRNs were shown to activate strongly in response to amino acids, and in turn these GRNs were implicated in egg-laying behaviors. Replicating these results and identifying changes since the release of the latest FAFB dataset (v783) will greatly help in characterizing the relationship between sensory perception and reproductive ability.

## To replicate results

1. Downlaod the following datasets from [FlyWire v783](https://codex.flywire.ai/api/download).
   1. `connections_princeton.csv` - connectivity and synapse counts
   2. `neurons.csv` - neurotransmitter types and scores
   3. `consolidated_cell_types.csv` - cell types
2. Get an API token for `fafbseg` and install it. See directions [here](https://fafbseg-py.readthedocs.io/en/latest/source/tutorials/flywire_setup.html#flywire-setup).
3. Install dependencies:
   
    ```
    python3 -m pip install pandas networkx fafbseg plotly
    ```
4. Run all cells in [`new.ipynb`](https://github.com/ayush-shrivastava003/connectomics-tests/blob/main/pathways/new.ipynb). You'll also see a step-by-step breakdown of my approach in the notebook.

All relevant files are contained in the directory [`fafb/`](https://github.com/ayush-shrivastava003/connectomics-tests/tree/main/pathways). For this approach, the only relevant code is in `new.ipynb`.
