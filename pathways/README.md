# Connectomics Tests

Using [Flywire](https://flywire.ai) to learn about connectomics for future projects at the Lyu Lab.

**Current goal**: recreate the Sankey from Fig. 3A of [this paper](https://www.sciencedirect.com/science/article/pii/S2211124724009756?via%3Dihub#sec2) from Stanley et al., which shows how protein-detecting taste receptor neurons connect to oviposition descending neurons through 1-2 layers of interneurons.

To recreate the Sankey, I need to:

1. Identify the neurons used in the diagram.
2. Find the number of synapses between each group of neurons.
3. Build the actual Sankey.

<details>
<summary><strong>Click here to see my initial approach, which I am no longer following.</strong></summary>

## Approach 1 (abandoned)

My initial approach was to simply reverse engineer what Stanley et al. had done. I used Codex to query all the neurons used in the paper. I later found that this was **inaccurate** as I seemed to get fewer Ir94es, more projection neurons, and more OviDNs than what Stanley et al. reported in their paper. Nonetheless, I will leave my queries here for future reference:

* Ir94e - `label >> Ir94e`
* OviDN - `label >> OviDN`
* Earmuff - There should only be one result, but `label >> Earmuff` actually returns three. I don't remember how I narrowed it down to one, but the one I use in my anlyses is `720575940629861163`.
* GNG.SLP.T1 (L) - These are projection neurons on the left side that Stanley et al. identified as being involved in the pathway. They grouped these together for releasing Ach and being on the left side. I was able to identify them using `name >> GNG.SLP && side == left && nt_type == ACH`
* GNG.SLP.T1 (R) - Similar to the last one, but located on the right side. `name >> GNG.SLP && side == right && nt_type == ACH`
* GNG.SLP.T2 (L) - I only got one glutamatergic neuron using the criteria specified in the paper. `name >> GNG.SLP && side == left && nt_type == GLUT`
* GNG.SLP.T2 (R) - `name >> GNG.SLP && side == right && nt_type == GLUT`
* Ach interneurons - unidentified
* Glu interneurons - unidentified

I won't talk more about this method since it ended up being inefficient and inaccurate, but I will leave this documentation about two programs I wrote to find the number of synapses going between groups of neurons. **These files are no longer relevant.**

> Codex kind of sucks for grouping neurons together in the network view. I (inadvertently) vibe-coded a new network graph program to show only the synapses between neurons of different groups. I have now replaced this with `synapses.py` which outputs the same information without needing to view a graph. It also ignores any neurons that have no incoming or outcoming inter-group synapses. If you want to see the network view, go to an older commit and look for `network.py`.
> 
>  To use `synapses.py`, simply query Codex with the neurons you're looking for (e.g, Ir94e and Earmuff), download the connections (next to the "Copy IDs" button), and move the CSV to the `data/` folder. Then run `synapses.py` and put in the file name. The output will be in `out/grouped_filename.csv`.
</details>

## Usage

I used Python for this analysis. You will need to install a few libraries:

```
pip3 install fafbseg pandas plotly
```

I believe you will also need a token from FlyWire to use their data. See [here](https://fafbseg-py.readthedocs.io/en/latest/source/tutorials/flywire_setup.html) for more information.

The code should otherwise run fine on its own.

## Approach 2 (in progress)

I pivoted to using an almost entirely programmatic approach using the FlyWire analysis tool `fafbseg`. The main file of interest is `flywire-test.py`. Each method in this program roughly correlates with each step of this exercise.

### Getting the right neurons

I found the neurons Stanley et al. used in their paper by checking the supplemental information section. I compared these to the neurons I found from my initial approach and found there were drastic differences, so I opted to use their exact neurons for this analysis. All the root IDs can be found in `pathways/data/groups.json`. I updated some of the root IDs as the connectome has been updated since their paper was published.

### Finding pathways

We are looking for neurons that take a signal from Ir94e to OviDNs in three hops or less. In Codex, you could do this pretty easily with the Pathways tool, but unfortunately `fafbseg` doesn't have a function that does that automatically.

What it can do, however, is find all the neurons a given neuron synapses to and vice versa. If we chain this two to three times - finding the neurons directly downstream of Ir94e, then finding the neurons downstream of those, then again finding ones downstream of those - we can merge all that data with the list of neurons upstream of OviDNs and get nice, clean pathways.

You can see the results of this in two different places. For the list of complete, start-to-finish pathways, see `pathways/data/three.csv` and `two.csv`. I broke these pathways down into each hop and put them in `hop_1.csv`, `hop_2.csv`, and `hop_3.csv`, which may be easier to read as I labeled the neurons. Note that weight means the number of synapses (I excluded neurons that were connected by less than five synapses).

### Unknown neurons

Speaking of labeling neurons, there were many neurons in this pathway that didn't match up to anything Stanley et al. identified. They seem to make up a significant portion of the pathways. **This will require manual verification with Codex to see if there is something wrong with my pathway-making code.** For now, I will continue with the process and see how the final Sankey looks.

I have programmatically labeled these unknown neurons based on the hop at which they were found and the neurotransmitter they release. For example, if they are cholinergic and downstream of Ir94e, they are called hop 1 acetylcholine interneurons.