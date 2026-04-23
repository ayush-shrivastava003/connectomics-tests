import plotly.graph_objects as go
import os
import pandas as pd

files = os.listdir('out')
info = {}
name_to_idx = {}
labels = []

for file in files:
    df = pd.read_csv(f'out/{file}')
    outgoing = df[df['Incoming'] == 0]['Group']
    incoming = df[df['Incoming'] != 0]

    if outgoing.shape[0] == 0 or incoming.shape[0] == 0: continue
    if info.get(outgoing.iloc[0]) == None: info[outgoing.iloc[0]] = {}
    if name_to_idx.get(outgoing.iloc[0]) == None:
        name_to_idx[outgoing.iloc[0]] = len(labels)
        labels.append(outgoing.iloc[0])
    if name_to_idx.get(incoming['Group'].iloc[0]) == None:
        name_to_idx[incoming['Group'].iloc[0]] = len(labels)
        labels.append(incoming['Group'].iloc[0])

    info[outgoing.iloc[0]][incoming['Group'].iloc[0]] = incoming['Incoming'].iloc[0]

print(info)
print(name_to_idx)
print(labels)

source = []
target = []
value = []
color = []

for outgoing, connections in info.items():
    for incoming, val in connections.items():
        source.append(name_to_idx[outgoing])
        target.append(name_to_idx[incoming])
        value.append(val)

print(source)
print(target)
print(value)

fig = go.Figure(data=[go.Sankey(
    node = dict(
      pad = 15,
      thickness = 10,
      line = dict(color = "green", width = 0.5),
      label = labels,
      color = ["purple", "yellow", "yellow", "yellow", "blue", "yellow"],
    ),
    link = dict(
        arrowlen = 30,
        source = source,
        target = target,
        value = value,
        color = ["rgba(0, 255, 0, 0.5)", "rgba(0, 255, 0, 0.5)", "rgba(0, 255, 0, 0.5)", "rgba(0, 255, 0, 0.5)", "rgba(255, 0, 0, 0.5)"]
    ))])

fig.update_layout(title_text="Sankey Test", font_size=10)
fig.show()