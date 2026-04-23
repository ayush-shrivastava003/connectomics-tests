# from fafbseg import flywire
from json import load
from pathlib import Path
import pandas as pd
import plotly.express as px

# neurons = pd.read_csv('data/sugar_GRNs_new.csv')['root_id'].tolist()
# nts = flywire.get_transmitter_predictions(neurons, materialization=783)
# nts.to_csv('out/sugar_GRNs_nt_predictions.csv')
# print(nts.head())
# serotonin_confidence = nts.loc['serotonin']
predictions = pd.read_csv('out/ir94e_nt_predictions.csv', index_col=0)
serotonin_confidence = predictions.loc['serotonin']
print(serotonin_confidence)

px.histogram(
    serotonin_confidence,
    x=serotonin_confidence.values,
    title='Confidence level distributions for serotonin as primary neurotransmitter',
    labels={'x': 'Confidence level', 'y': 'Number of neurons'},
).write_image('out/Ir94e.png')