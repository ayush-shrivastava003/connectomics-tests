from caveclient import CAVEclient
from cloudvolume import CloudVolume
import navis
import pandas as pd
import plotly.graph_objects as go
import pickle

yeast_orns = pd.read_csv('data/yeast_orns.csv')['root_id']
given_neurons = pd.read_csv('data/given_neurons.csv')
ovidns = given_neurons[given_neurons['group'] == "OviDN"]['root_id']
ca = given_neurons[given_neurons['group'] == "CA"]['root_id']
all_ids = set(pd.concat([yeast_orns, ovidns, ca]))

# These neurons are missing meshes in the connectome
MISSING_MESHES = {720575941431282680, 720575941436163360, 720575941440408287, 720575941442476495, 720575941461529043, 720575941478673514, 720575941482311619, 720575941502103947, 720575941504707010, 720575941513940812, 720575941514224195, 720575941516611321, 720575941528042265, 720575941535414762, 720575941535664922, 720575941537262785, 720575941546727868, 720575941569673210, 720575941570147316, 720575941576370102, 720575941578519897, 720575941585468638, 720575941585491678, 720575941592548236, 720575941595357654, 720575941595636101, 720575941645204856, 720575941669452465} 
all_ids = list(all_ids - MISSING_MESHES)

color_map = {}
for id in set(yeast_orns):
    color_map[str(id)] = (255, 0, 0)
for id in set(ovidns):
    color_map[str(id)] = (0, 255, 0)
for id in set(ca):
    color_map[str(id)] = (0, 0, 255)

def download_meshes():

    yeast_orns = pd.read_csv('data/yeast_orns.csv')['root_id']
    given_neurons = pd.read_csv('data/given_neurons.csv')
    ovidns = given_neurons[given_neurons['group'] == "OviDN"]['root_id']
    ca = given_neurons[given_neurons['group'] == "CA"]['root_id']
    all_ids = set(pd.concat([yeast_orns, ovidns, ca]))

    # These neurons are missing meshes in the connectome
    MISSING_MESHES = {720575941431282680, 720575941436163360, 720575941440408287, 720575941442476495, 720575941461529043, 720575941478673514, 720575941482311619, 720575941502103947, 720575941504707010, 720575941513940812, 720575941514224195, 720575941516611321, 720575941528042265, 720575941535414762, 720575941535664922, 720575941537262785, 720575941546727868, 720575941569673210, 720575941570147316, 720575941576370102, 720575941578519897, 720575941585468638, 720575941585491678, 720575941592548236, 720575941595357654, 720575941595636101, 720575941645204856, 720575941669452465} 
    all_ids = list(all_ids - MISSING_MESHES)

    # client = CAVEclient("brain_and_nerve_cord_public")
    # seg_source = client.info.segmentation_source()
    seg_source = "precomputed://gs://lee-lab_brain-and-nerve-cord-fly-connectome/neuron_meshes"
    print(seg_source)

    navis.patch_cloudvolume()
    cv = CloudVolume(seg_source, use_https=True, progress=False)
    print("Instantiated cloudvolume")

    # as_navis=True returns a navis.NeuronList directly -- skips the manual
    # dict -> list -> navis conversion, and gives you .plot3d-ready MeshNeurons for free
    meshes = cv.mesh.get(all_ids, as_navis=True)
    print(f"Downloaded {len(meshes)} meshes at")
    
    with open("mesh.pkl", "wb") as f:
        pickle.dump(meshes, f)
        print("Pickled")

def get_local_meshes():
    meshes = None
    with open("mesh.pkl", "rb") as f:
        print("Loading meshes...")
        meshes = pickle.load(f)

    # print("Simplifying meshes...")
    # simplified = navis.simplify_mesh(meshes, F=0.05, backend='pyfqmr')
    
    # orig_faces = sum(n.faces.shape[0] for n in meshes)
    # new_faces = sum(n.faces.shape[0] for n in simplified)
    # print(f"Faces: {orig_faces} -> {new_faces} ({new_faces/orig_faces:.1%})")
    OUTLINE_SOURCE = "precomputed://gs://lee-lab_brain-and-nerve-cord-fly-connectome/region_outlines"
    cv_outline = CloudVolume(OUTLINE_SOURCE, use_https=True, progress=False)
    outline_id = 1  # placeholder -- adjust based on the probe print above
    outline_mesh = cv_outline.mesh.get(outline_id)
    outline_vol = navis.Volume(
        [v / 1000 for v in outline_mesh.vertices],
        outline_mesh.faces,
        name="CNS outline",
        color=(0.7, 0.7, 0.7, 0.05),  # light, translucent grey background
    )

    g: go.Figure = navis.plot3d([meshes, outline_vol], backend='plotly')
    g.show()
    # print("Writing image...")
    g.write_html("mesh2.html", include_plotlyjs='cdn')
    # g.write_image('mesh.png')
    # print("Done!")
# download_meshes()
get_local_meshes()