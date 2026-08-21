from caveclient import CAVEclient
from cloudvolume import CloudVolume
import pcg_skel
import navis
import pandas as pd
import plotly.graph_objects as go
import pickle

def main():
    yeast_orns = pd.read_csv('data/yeast_orns.csv')['root_id']
    given_neurons = pd.read_csv('data/given_neurons.csv')
    ovidns = given_neurons[given_neurons['group'] == "OviDN"]['root_id']
    ca = given_neurons[given_neurons['group'] == "CA"]['root_id']

    # --- Color map fix ---
    # navis.read_swc's default fmt='{name}.swc' extracts the id via regex,
    # which always returns a STRING (confirmed in navis/io/base.py's
    # parse_filename -- only converts to int if you write '{name:int}' in
    # fmt). Meanwhile these root_ids come from pandas as int64. A dict like
    # {720575941417243164: (255,0,0)} will never match neuron.id ==
    # "720575941417243164" even though they print identically -- that
    # silent type mismatch is why every neuron fell back to the default
    # orange. Fix: key the color_map with str(id) to match what read_swc
    # actually assigns.
    color_map = {}
    for id in set(yeast_orns):
        color_map[str(id)] = (255, 0, 0)
    for id in set(ovidns):
        color_map[str(id)] = (0, 255, 0)
    for id in set(ca):
        color_map[str(id)] = (0, 0, 255)

    # navis reads a directory of SWCs directly into a NeuronList
    neurons = navis.read_swc("skeletons_swc/", parallel=False)
    print(f"Loaded {len(neurons)} neurons into navis")

    # Sanity check: confirm color_map keys actually match neuron .id values
    # before plotting -- if this prints 0 matches, something about the SWC
    # filenames doesn't match the root_ids in your CSVs (e.g. stale/merged
    # IDs) and the color mismatch has a different cause than the string/int
    # issue above.
    neuron_ids = {n.id for n in neurons}
    matched = neuron_ids & set(color_map.keys())
    print(f"{len(matched)}/{len(neuron_ids)} neuron ids matched color_map")

    # --- CNS region-outlines mesh, as background context ---
    # Same static Lee lab precomputed:// bucket as the neuron mesh mirror
    # from earlier, just a different object (whole-CNS outline, not
    # per-neuron). This is a single small mesh, not 600+ neurons, so none
    # of the earlier graphene speed/RAM concerns apply -- plain CloudVolume
    # mesh.get() is fine here.
    OUTLINE_SOURCE = "precomputed://gs://lee-lab_brain-and-nerve-cord-fly-connectome/region_outlines"
    cv_outline = CloudVolume(OUTLINE_SOURCE, use_https=True, progress=False)

    # Probe: list available segment IDs in this volume before guessing one.
    # Region-outline volumes often use a small fixed set of IDs (e.g. 1 for
    # "whole CNS", or one per named region) rather than neuron root IDs --
    # check what's actually there rather than assume ID 1 works.
    print("Outline mesh info:", cv_outline.mesh.meta.info if hasattr(cv_outline.mesh, "meta") else "unavailable")

    outline_id = 1  # placeholder -- adjust based on the probe print above
    outline_mesh = cv_outline.mesh.get(outline_id)
    outline_vol = navis.Volume(
        [v / 1000 for v in outline_mesh.vertices],
        outline_mesh.faces,
        name="CNS outline",
        color=(0.7, 0.7, 0.7, 0.05),  # light, translucent grey background
    )

    print("Outline volume:")
    print(outline_vol.vertices.min(axis=0), outline_vol.vertices.max(axis=0))
    print("Sample node:")
    print(neurons[0].nodes[['x','y','z']].min(axis=0), neurons[0].nodes[['x','y','z']].max(axis=0))


    g: go.Figure = navis.plot3d([neurons, outline_vol], backend='plotly', color=color_map)
    print("Writing image...")
    g.write_html("mesh.html")
    g.write_image('mesh.png')
    print("Done!")

if __name__ == "__main__":
    main()