import plotly.graph_objects as go
import pandas as pd

# Read and concatenate all hop files
dfs = []
for i in range(1, 4):
    df = pd.read_csv(f'out/hop_{i}.csv')
    dfs.append(df)

combined_df = pd.concat(dfs, ignore_index=True)

# Read and process two-hop data
# two_df = pd.read_csv('data/two.csv')
# two_connections = []
# for _, row in two_df.iterrows():
#     two_connections.append({
#         'from_group': row['pre_group'],
#         'to_group': row['post_group'],
#         'weight': row['weight_x']
#     })
#     two_connections.append({
#         'from_group': row['post_group'],
#         'to_group': 'OviDN',  # Assuming 'end' is OviDN
#         'weight': row['weight_y']
#     })

# two_df_processed = pd.DataFrame(two_connections)

# Concatenate with the three-hop data
# combined_df = pd.concat([combined_df, two_df_processed], ignore_index=True).drop_duplicates()

# Aggregate synapse counts across all data
aggregated = combined_df.groupby(['from_group', 'to_group'])['weight'].sum().reset_index()
# aggregated = aggregated[(aggregated['weight'] >= 40)]
# from_groups = set(aggregated['from_group'])
# to_groups = set(aggregated['to_group'])

# aggregated = aggregated[
#     ((aggregated['from_group'] == 'Sugar GRNs') | (aggregated['from_group'].isin(to_groups))) &
#     ((aggregated['to_group'] == 'IPCs') | (aggregated['to_group'].isin(from_groups)))
# ]

# aggregated = aggregated.sort_values(by='weight', ascending=False)
aggregated.to_csv('comb.csv', index=False)

# Build global labels
name_to_idx = {}
labels = []

for group in aggregated['from_group'].unique():
    if group not in name_to_idx:
        name_to_idx[group] = len(labels)
        labels.append(group)

for group in aggregated['to_group'].unique():
    if group not in name_to_idx:
        name_to_idx[group] = len(labels)
        labels.append(group)

# Build source, target, value
source = []
target = []
value = []

for _, row in aggregated.iterrows():
    source.append(name_to_idx[row['from_group']])
    target.append(name_to_idx[row['to_group']])
    value.append(row['weight'])

name_to_color = { # Key by group name for easier identification
    "Ir94e": {"line": "purple", "arrow": "rgba(0, 255, 0, 0.5)"},
    "GNG.SLP.T1 (L)": {"line": "yellow", "arrow": "rgba(0, 255, 0, 0.5)"},
    "GNG.SLP.T1 (R)": {"line": "yellow", "arrow": "rgba(0, 255, 0, 0.5)"},
    "GNG.SLP.T2 (L)": {"line": "yellow", "arrow": "rgba(255, 0, 0, 0.5)"},
    "GNG.SLP.T2 (R)": {"line": "yellow", "arrow": "rgba(255, 0, 0, 0.5)"},
    "Earmuff": {"line": "yellow", "arrow": "rgba(255, 0, 0, 0.5)"},
    "Stanley Glu interneuron": {"line": "red", "arrow": "rgba(255, 0, 0, 0.5)"},
    "Stanley ACh interneuron": {"line": "red", "arrow": "rgba(0, 255, 0, 0.5)"},
    "hop 1 gaba interneuron": {"line": "yellow", "arrow": "rgba(255, 0, 0, 0.5)"},
    "hop 2 gaba interneuron": {"line": "red", "arrow": "rgba(255, 0, 0, 0.5)"},
    "hop 3 gaba interneuron": {"line": "green", "arrow": "rgba(255, 0, 0, 0.5)"},
    "hop 1 acetylcholine interneuron": {"line": "yellow", "arrow": "rgba(0, 255, 0, 0.5)"},
    "hop 2 acetylcholine interneuron": {"line": "red", "arrow": "rgba(0, 255, 0, 0.5)"},
    "hop 3 acetylcholine interneuron": {"line": "green", "arrow": "rgba(0, 255, 0, 0.5)"},
    "hop 1 glutamate interneuron": {"line": "yellow", "arrow": "rgba(255, 0, 0, 0.5)"},
    "hop 2 glutamate interneuron": {"line": "red", "arrow": "rgba(255, 0, 0, 0.5)"},
    "hop 3 glutamate interneuron": {"line": "green", "arrow": "rgba(255, 0, 0, 0.5)"},
    "hop 1 dopamine interneuron": {"line": "yellow", "arrow": "rgba(255, 165, 0, 0.5)"},
    "hop 2 dopamine interneuron": {"line": "red", "arrow": "rgba(255, 165, 0, 0.5)"},
    "hop 3 dopamine interneuron": {"line": "green", "arrow": "rgba(255, 165, 0, 0.5)"},
    "hop 1 serotonin interneuron": {"line": "yellow", "arrow": "rgba(255, 192, 203, 0.5)"},
    "hop 2 serotonin interneuron": {"line": "red", "arrow": "rgba(255, 192, 203, 0.5)"},
    "hop 3 serotonin interneuron": {"line": "green", "arrow": "rgba(255, 192, 203, 0.5)"},
    "hop 1 octopamine interneuron": {"line": "yellow", "arrow": "rgba(173, 255, 47, 0.5)"},
    "OviDN": {"line": "blue", "arrow": "rgba(0, 255, 0, 0.5)"},
    "Sugar GRNs": {"line": "purple", "arrow": "rgba(0, 255, 0, 0.5)"}, # Note: 720575940623172843 is actually GLU, but all the rest are ACH
    "IPCs": {"line": "blue", "arrow": "rgba(0, 255, 255, 0.5)"}, # Unknown NT type,
    "Sugar-SELs": {"line": "purple", "arrow": "rgba(255, 192, 203, 0.5)"},
}

node_colors = [name_to_color.get(label, {"line": "grey"})['line'] for label in labels]
arrow_colors = [name_to_color.get(labels[src], {"arrow": "rgba(128, 128, 128, 0.5)"})['arrow'] for src in source]
print(name_to_idx, labels)

# Create and display the Sankey
fig = go.Figure(data=[go.Sankey(
    node=dict(
        pad=15,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=labels,
        color=node_colors
    ),
    link=dict(
        arrowlen=15,
        source=source,
        target=target,
        value=value,
        color=arrow_colors
    )
)])

fig.update_layout(title_text="Refined Neuron Pathway Sankey Diagram", font_size=10)
fig.write_html('out/sankey.html')
fig.show()
# print(value)