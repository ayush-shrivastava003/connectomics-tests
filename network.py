# Vibe-coded network graoh of Ir94e and GNG.SLP neuron connections
# I filtered it to only show inter-group synapsing as that was what I cared about.
# Since Flywire Codex has the most updated connectome, I manually downloaded the 
# connections data form there.

import plotly.graph_objects as go
import pandas as pd
import networkx as nx
import json

# Load the data
df = pd.read_csv('data/ir94e-gng-slp-t1-R.csv')

# Load groups to categorize neurons
with open('groups.json', 'r') as f:
    groups = json.load(f)

# Create a mapping of neuron ID to group name
neuron_to_group = {}
for group_name, neuron_ids in groups.items():
    for neuron_id in neuron_ids:
        neuron_to_group[neuron_id] = group_name

# Define colors for each group
group_colors = {
    'IR94e': 'purple',
    'OviDNs': 'blue',
    'Earmuff': 'gold',
    'GNG.SLP.T1 (L)': 'green',
    'GNG.SLP.T1 (R)': 'cyan',
    'GNG.SLP.T2 (L)': 'orangered',
    'GNG.SLP.T2 (R)': 'pink'
}

# Create network graph from the CSV data
# Aggregate connections by neuron pair (sum synapses)
aggregated = df.groupby(['From', 'To'])['Synapses'].sum().reset_index()

# Filter to keep only inter-group connections (exclude internal connections)
# Remove edges where both neurons belong to the same group
aggregated = aggregated[
    aggregated.apply(
        lambda row: neuron_to_group.get(row['From']) != neuron_to_group.get(row['To']),
        axis=1
    )
]

# Create NetworkX directed graph
G = nx.DiGraph()

# Add nodes with attributes
all_neurons = set(list(df['From'].unique()) + list(df['To'].unique()))
for neuron_id in all_neurons:
    group = neuron_to_group.get(neuron_id, 'Unknown')
    G.add_node(neuron_id, group=group)

# Add edges with weights (synapses)
for _, row in aggregated.iterrows():
    G.add_edge(row['From'], row['To'], weight=row['Synapses'])

# Use spring layout for better visualization
pos = nx.spring_layout(G, k=0.5, iterations=50, seed=42)

# Extract edge information
edge_x = []
edge_y = []
edge_weights = []

for edge in G.edges(data=True):
    x0, y0 = pos[edge[0]]
    x1, y1 = pos[edge[1]]
    edge_x.append(x0)
    edge_x.append(x1)
    edge_x.append(None)
    edge_y.append(y0)
    edge_y.append(y1)
    edge_y.append(None)
    edge_weights.append(edge[2]['weight'])

# Create edge trace
edge_trace = go.Scatter(
    x=edge_x, y=edge_y,
    mode='lines',
    line=dict(width=0.5, color='#888'),
    hoverinfo='none',
    showlegend=False
)

# Extract node information
node_x = []
node_y = []
node_text = []
node_color = []
node_size = []
df2 = pd.DataFrame(columns=["Neuron", "Group", "Incoming", "Outgoing"])

for node in G.nodes():
    x, y = pos[node]
    node_x.append(x)
    node_y.append(y)
    
    group = neuron_to_group.get(node, 'Unknown')
    in_degree = G.in_degree(node)
    out_degree = G.out_degree(node)
    incoming = df[
        (df['To'] == node) &
        (df['From'].map(neuron_to_group) != group)
    ]['Synapses'].sum()
    outgoing = df[
        (df['From'] == node) &
        (df['To'].map(neuron_to_group) != group)
    ]['Synapses'].sum()

    df2.loc[len(df2)] = {"Neuron": node, "Group": group, "Incoming": incoming, "Outgoing": outgoing}

    node_text.append(f"ID: {node}<br>Group: {group}<br>Incoming inter-group synapses: {incoming}<br>Outgoing inter-group synapses: {outgoing}")
    node_color.append(group_colors.get(group, 'gray'))
    
    # Size based on total connections
    node_size.append(max(10, 15 + incoming))

# Create node trace
node_trace = go.Scatter(
    x=node_x, y=node_y,
    mode='markers',
    hoverinfo='text',
    text=node_text,
    showlegend=False,
    marker=dict(
        size=node_size,
        color=node_color,
        line=dict(width=2, color='white')
    )
)

# Create figure
fig = go.Figure(data=[edge_trace, node_trace],
    layout=go.Layout(
        title='Neuron Network Graph',
        title_font_size=16,
        showlegend=False,
        hovermode='closest',
        margin=dict(b=20, l=5, r=5, t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='white',
        height=800,
        width=1000
    )
)

# Add legend manually
for group_name, color in group_colors.items():
    fig.add_trace(go.Scatter(
        x=[None], y=[None],
        name=group_name,
        mode='markers',
        marker=dict(size=10, color=color),
        showlegend=True
    ))

# Save and show
fig.write_html('out/neuron_network.html')
print("Network graph saved to 'out/neuron_network.html'")
print(f"Total neurons: {len(G.nodes())}")
print(f"Total connections: {len(G.edges())}")
print("\nNeuron groups:")
for group_name, count in sorted([(g, len(n)) for g, n in groups.items()], key=lambda x: x[1], reverse=True):
    print(f"  {group_name}: {count} neurons")

df2.to_csv('out/clean.csv', index=False)