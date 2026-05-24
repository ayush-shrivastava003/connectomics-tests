# Modified flywire-test.py for Sugar GRN -> IPC.
# Codex shows it usually takes 4 hops to get to IPC, so we are doing one extra step.

from json import dump, load
import pandas as pd

# Path to the groups JSON file (shared across all functions)
GROUPS_JSON_PATH = 'data/groups.json'

with open(GROUPS_JSON_PATH, 'r') as f:
    groups = load(f)

neuron_to_group = {}
for group_name, neuron_ids in groups.items():
    for neuron_id in neuron_ids:
        neuron_to_group[neuron_id] = group_name

def get_pathways(three_hops = False):
    from fafbseg import flywire
    neurons = load(open(GROUPS_JSON_PATH, 'r'))

    print("Getting GRN -> I1")
    grn_i1 = flywire.synapses.get_connectivity(
        neurons['Sugar GRNs'],
        upstream=False,
        filtered=True,
        materialization=783,
    )

    grn_i1['pre_group'] = grn_i1['pre'].map(neuron_to_group)
    grn_i1['post_group'] = grn_i1['post'].map(neuron_to_group)

    # Only include neurons that are of different groups and connected by at least 5 synapses
    print("Done GRN -> I1")
    grn_i1 = grn_i1[(grn_i1['weight'] >= 5) & (grn_i1['pre_group'] != grn_i1['post_group'])]

    print("Getting I1 -> I2")
    i1_i2 = flywire.synapses.get_connectivity(
        grn_i1['post'].tolist(),
        upstream=False,
        filtered=True,
        materialization=783
    ).query('weight >= 5')
    # i1_i2['pre_group'] = i1_i2['pre'].map(neuron_to_group)
    # i1_i2['post_group'] = i1_i2['post'].map(neuron_to_group)
    # i1_i2 = i1_i2[(i1_i2['weight'] >= 5) & (i1_i2['pre_group'] != i1_i2['post_group'])]
    print("Done I1 -> I2")

    print("Getting IPC => I3")
    i3_ipc = flywire.synapses.get_connectivity( # UPSTREAM
        neurons["IPCs"],
        downstream=False,
        filtered=True,
        materialization=783
    ).query('weight >= 5')
    # i3_ipc['pre_group'] = i3_ipc['pre'].map(neuron_to_group)
    # i3_ipc['post_group'] = i3_ipc['post'].map(neuron_to_group)
    # i3_ipc = i3_ipc[(i3_ipc['weight'] >= 5) & (i3_ipc['pre_group'] != i3_ipc['post_group'])]
    print("Done IPC => I3")
    print(i3_ipc.head())

    print("Getting I3 => I2")
    i2_i3 = flywire.synapses.get_connectivity( # UPSTREAM
        i3_ipc['pre'].tolist(),
        downstream=False,
        filtered=True,
        materialization=783
    ).query('weight >= 5')
    # i2_i3['pre_group'] = i2_i3['pre'].map(neuron_to_group)
    # i2_i3['post_group'] = i2_i3['post'].map(neuron_to_group)
    # i2_i3 = i2_i3[(i2_i3['weight'] >= 5) & (i2_i3['pre_group'] != i2_i3['post_group'])]
    print("Done I3 => I2")

    # Merge to produce grn -> i1 -> i2
    grn_i2 = grn_i1.merge(i1_i2, left_on='post', right_on='pre', how='inner').rename(columns={
        'pre_x': 'Sugar GRN',
        'pre_y': 'I1',
        'post_y': 'I2',
        'weight_y': 'weight_i1_i2',
        'weight_x': 'weight_grn_i1'
    }).drop(columns=['post_x'])
    print(grn_i2.head())
    
    # Merge to produce i2 -> i3 -> ipc
    i2_ipc = i2_i3.merge(i3_ipc, left_on='post', right_on='pre', how='inner').rename(columns={
        'pre_x': 'I2',
        'pre_y': 'I3',
        'post_y': 'IPC',
        'weight_y': 'weight_i3_ipc',
        'weight_x': 'weight_i2_i3'
    }).drop(columns=['post_x'])

    # Big merge
    grn_ipc = grn_i2.merge(i2_ipc, left_on='I2', right_on='I2', how='inner').drop_duplicates()
    grn_ipc.to_csv('data/four.csv', index=False)

def organize_hops():
    four = pd.read_csv('data/four.csv')

    first_hop = four[['Sugar GRN', 'I1', 'weight_grn_i1', 'pre_group', 'post_group']].drop_duplicates()
    first_hop = first_hop.rename(columns={
        'Sugar GRN': 'from',
        'I1': 'to',
        'weight_grn_i1': 'weight',
        'pre_group': 'from_group',
        'post_group': 'to_group'
    })
    first_hop.to_csv('out/hop_1.csv', index=False)

    second_hop = four[['I1', 'I2', 'weight_i1_i2']].drop_duplicates()
    second_hop['from_group'] = second_hop['I1'].map(neuron_to_group)
    second_hop['to_group'] = second_hop['I2'].map(neuron_to_group)
    second_hop = second_hop.rename(columns={
        'I1': 'from',
        'I2': 'to',
        'weight_i1_i2': 'weight',
        'from_group': 'from_group',
        'to_group': 'to_group'
    })
    second_hop.to_csv('out/hop_2.csv', index=False)

    third_hop = four[['I2', 'I3', 'weight_i2_i3']].drop_duplicates()
    third_hop['from_group'] = third_hop['I2'].map(neuron_to_group)
    third_hop['to_group'] = third_hop['I3'].map(neuron_to_group)
    third_hop = third_hop.rename(columns={
        'I2': 'from',
        'I3': 'to',
        'weight_i2_i3': 'weight',
        'from_group': 'from_group',
        'to_group': 'to_group'
    })
    third_hop.to_csv('out/hop_3.csv', index=False)

    fourth_hop = four[['I3', 'IPC', 'weight_i3_ipc']].drop_duplicates()
    fourth_hop['from_group'] = fourth_hop['I3'].map(neuron_to_group)
    fourth_hop['to_group'] = fourth_hop['IPC'].map(neuron_to_group)
    fourth_hop = fourth_hop.rename(columns={
        'I3': 'from',
        'IPC': 'to',
        'weight_i3_ipc': 'weight',
        'from_group': 'from_group',
        'to_group': 'to_group'
    })
    fourth_hop.to_csv('out/hop_4.csv', index=False)

    # four[(four['Sugar GRN'] == 720575940639198653) & (four['IPC'] == 720575940612923390)].to_csv('/Users/ayushshrivastava/code/lab-analysis-test/connectomics-tests/pathways/onepath.csv')

def find_unknown_neurons():
    from fafbseg import flywire
    with open(GROUPS_JSON_PATH, 'r') as f:
        groups = load(f)
        neuron_to_group = {}

        for group_name, neuron_ids in groups.items():
            for neuron_id in neuron_ids:
                neuron_to_group[neuron_id] = group_name

    for i in range(1, 5): # repeat three times, since hop 4 is only IPCs
        file = f'out/hop_{i}.csv'
        print(f"Analyzing {file}")
        df = pd.read_csv(file)
        print(df.head())
        neurons = df[df['to_group'].isna()]['to'].unique().tolist()

        if len(neurons) == 0:
            df['from_group'] = df['from'].map(neuron_to_group).fillna(df['from_group'])
            df.to_csv(file, index=False)
            continue

        print('unique unknown neurons:', len(neurons))

        nts = flywire.get_transmitter_predictions(
            neurons,
            materialization=783,
            single_pred=True
        )

        for n in neurons:
            if n in neuron_to_group:
                print("in ntg")
                continue

            nt_type = nts[n][0] if isinstance(nts[n], (list, tuple)) else nts[n]
            category = f"hop {i} {nt_type} interneuron"
    
            if category not in groups:
                print(f"Neuron {n} is uncategorized, putting in category {category}")
                groups[category] = []
            groups[category].append(n)
            neuron_to_group[n] = category

        with open(GROUPS_JSON_PATH, 'w') as f:
            dump(groups, f)
        
        # Update the dataframe with the assigned groups
        df['to_group'] = df['to'].map(neuron_to_group).fillna(df['to_group'])
        df['from_group'] = df['from'].map(neuron_to_group).fillna(df['from_group'])
        
        # Save the updated dataframe back to the original CSV file
        df.to_csv(file, index=False)

# get_pathways()
organize_hops()
find_unknown_neurons()