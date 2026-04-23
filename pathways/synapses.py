# Vibe-coded network graoh of Ir94e and GNG.SLP neuron connections
# I filtered it to only show inter-group synapsing as that was what I cared about.
# Since Flywire Codex has the most updated connectome, I manually downloaded the 
# connections data form there.

import pandas as pd
import json

# Load the data
filename = input("Filename: ")
if not filename.endswith('.csv'): filename += '.csv'

df = pd.read_csv(f'data/{filename}')

# Load groups to categorize neurons
with open('data/groups.json', 'r') as f:
    groups = json.load(f)

# Create a mapping of neuron ID to group name
neuron_to_group = {}
for group_name, neuron_ids in groups.items():
    for neuron_id in neuron_ids:
        neuron_to_group[neuron_id] = group_name

# More efficient approach: Pre-filter inter-group connections
df['From_Group'] = df['From'].map(neuron_to_group)
df['To_Group'] = df['To'].map(neuron_to_group)

# Filter to only inter-group connections
inter_group_df = df[df['From_Group'] != df['To_Group']].copy()

# Get all unique neurons
all_neurons = set(list(df['From'].unique()) + list(df['To'].unique()))

# Calculate incoming synapses per neuron (from other groups)
incoming_synapses = inter_group_df.groupby('To')['Synapses'].sum().reset_index()
incoming_synapses.columns = ['Neuron', 'Incoming']

# Calculate outgoing synapses per neuron (to other groups)
outgoing_synapses = inter_group_df.groupby('From')['Synapses'].sum().reset_index()
outgoing_synapses.columns = ['Neuron', 'Outgoing']

# Get all unique neurons and their groups
all_neurons_df = pd.DataFrame({
    'Neuron': list(all_neurons),
    'Group': [neuron_to_group.get(n, 'Unknown') for n in all_neurons]
})

# Merge all data efficiently
df_clean = all_neurons_df.merge(incoming_synapses, on='Neuron', how='left') \
                        .merge(outgoing_synapses, on='Neuron', how='left') \
                        .fillna(0)

# Remove neurons with no inter-group connections
df_clean = df_clean[(df_clean['Incoming'] > 0) | (df_clean['Outgoing'] > 0)]
df_clean['Incoming'] = df_clean['Incoming'].astype(int)
df_clean['Outgoing'] = df_clean['Outgoing'].astype(int)

df_clean.groupby('Group').sum()[['Incoming', 'Outgoing']].to_csv(f'out/grouped_{filename}', index=True)
# df_clean.to_csv(f'out/clean_{filename}', index=False)
print(f"Synapse data saved to 'out/grouped_{filename}'")