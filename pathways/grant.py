# Modified flywire-test.py for Sugar GRN -> IPC.
# This version splits shortest-path GRN -> IPC pairs into 3-hop and 4-hop batches using merged.csv.

from json import dump, load
import pandas as pd

# Path definitions
GROUPS_JSON_PATH = 'data/groups.json'
HOP_MATRIX_PATH = 'data/merged.csv'
THREE_PATHS_PATH = 'data/three.csv'
FOUR_PATHS_PATH = 'data/four.csv'
THREE_PAIR_PATH = 'data/three_pairs.csv'
FOUR_PAIR_PATH = 'data/four_pairs.csv'

with open(GROUPS_JSON_PATH, 'r') as f:
    groups = load(f)

neuron_to_group = {}
for group_name, neuron_ids in groups.items():
    for neuron_id in neuron_ids:
        neuron_to_group[neuron_id] = group_name


def load_hop_matrix():
    merged = pd.read_csv(HOP_MATRIX_PATH)
    merged = merged.rename(columns={merged.columns[0]: 'Sugar GRN'})
    melted = merged.melt(id_vars=['Sugar GRN'], var_name='IPC', value_name='hops')
    melted['Sugar GRN'] = melted['Sugar GRN'].astype(int)
    melted['IPC'] = melted['IPC'].astype(int)
    melted = melted[melted['hops'].isin([3, 4])]
    return melted


def get_shortest_path_pairs():
    distances = load_hop_matrix()
    three = distances[distances['hops'] == 3].copy()
    four = distances[distances['hops'] == 4].copy()
    three.to_csv(THREE_PAIR_PATH, index=False)
    four.to_csv(FOUR_PAIR_PATH, index=False)
    return three, four


def get_pathways():
    from fafbseg import flywire

    distances = load_hop_matrix()
    grn_ids = distances['Sugar GRN'].unique().tolist()
    ipc_ids = distances['IPC'].unique().tolist()

    print('Getting GRN -> I1')
    grn_i1 = flywire.synapses.get_connectivity(
        grn_ids,
        upstream=False,
        filtered=False,
        materialization=783,
    )

    grn_i1['pre_group'] = grn_i1['pre'].map(neuron_to_group)
    grn_i1['post_group'] = grn_i1['post'].map(neuron_to_group)
    grn_i1 = grn_i1[(grn_i1['weight'] >= 5) & (grn_i1['pre_group'] != grn_i1['post_group'])]
    print('Done GRN -> I1')

    print('Getting I1 -> I2')
    i1_i2 = flywire.synapses.get_connectivity(
        grn_i1['post'].tolist(),
        upstream=False,
        filtered=False,
        materialization=783,
    ).query('weight >= 5')
    print('Done I1 -> I2')

    print('Getting IPC upstream partners')
    ipc_up = flywire.synapses.get_connectivity(
        ipc_ids,
        downstream=False,
        filtered=True,
        materialization=783,
    ).query('weight >= 5')
    print('Done IPC upstream partners')

    print('Getting second upstream hop for IPC partners')
    i2_i3 = flywire.synapses.get_connectivity(
        ipc_up['pre'].tolist(),
        downstream=False,
        filtered=True,
        materialization=783,
    ).query('weight >= 5')
    print('Done second upstream hop')

    grn_i2 = grn_i1.merge(i1_i2, left_on='post', right_on='pre', how='inner').rename(columns={
        'pre_x': 'Sugar GRN',
        'pre_y': 'I1',
        'post_y': 'I2',
        'weight_y': 'weight_i1_i2',
        'weight_x': 'weight_grn_i1',
    }).drop(columns=['post_x'])

    three_pairs, four_pairs = get_shortest_path_pairs()

    print('Building 3-hop paths')
    three = grn_i2.merge(ipc_up, left_on='I2', right_on='pre', how='inner')
    three = three.rename(columns={
        'post': 'IPC',
        'weight': 'weight_i2_ipc',
    })
    three = three[['Sugar GRN', 'weight_grn_i1', 'pre_group', 'post_group', 'I1', 'I2', 'weight_i1_i2', 'weight_i2_ipc', 'IPC']]
    three = three.merge(three_pairs[['Sugar GRN', 'IPC']], on=['Sugar GRN', 'IPC'], how='inner').drop_duplicates()
    three['path_length'] = 3
    three.to_csv(THREE_PATHS_PATH, index=False)

    print('Building 4-hop paths')
    i2_ipc = i2_i3.merge(ipc_up, left_on='post', right_on='pre', how='inner').rename(columns={
        'pre_x': 'I2',
        'pre_y': 'I3',
        'post_y': 'IPC',
        'weight_y': 'weight_i3_ipc',
        'weight_x': 'weight_i2_i3',
    }).drop(columns=['post_x'])

    four = grn_i2.merge(i2_ipc, left_on='I2', right_on='I2', how='inner').drop_duplicates()
    four = four.merge(four_pairs[['Sugar GRN', 'IPC']], on=['Sugar GRN', 'IPC'], how='inner')
    four['path_length'] = 4
    four.to_csv(FOUR_PATHS_PATH, index=False)

    print(f'Saved {len(three)} three-hop paths to {THREE_PATHS_PATH}')
    print(f'Saved {len(four)} four-hop paths to {FOUR_PATHS_PATH}')


def organize_hops():
    four = pd.read_csv(FOUR_PATHS_PATH)
    three = pd.read_csv(THREE_PATHS_PATH)

    first_hop = pd.concat([
        four[['Sugar GRN', 'I1', 'weight_grn_i1', 'pre_group', 'post_group']],
        three[['Sugar GRN', 'I1', 'weight_grn_i1', 'pre_group', 'post_group']]
        ]).drop_duplicates()
    first_hop = first_hop.rename(columns={
        'Sugar GRN': 'from',
        'I1': 'to',
        'weight_grn_i1': 'weight',
        'pre_group': 'from_group',
        'post_group': 'to_group',
    })
    first_hop.to_csv('out/hop_1.csv', index=False)

    second_hop = pd.concat([
        four[['I1', 'I2', 'weight_i1_i2']],
        three[['I1', 'I2', 'weight_i1_i2']]
    ]).drop_duplicates()
    second_hop['from_group'] = second_hop['I1'].map(neuron_to_group)
    second_hop['to_group'] = second_hop['I2'].map(neuron_to_group)
    second_hop = second_hop.rename(columns={
        'I1': 'from',
        'I2': 'to',
        'weight_i1_i2': 'weight',
        'from_group': 'from_group',
        'to_group': 'to_group',
    })
    second_hop.to_csv('out/hop_2.csv', index=False)

    third_hop_4 = four[['I2', 'I3', 'weight_i2_i3']].rename(columns={
        'I2': 'from',
        'I3': 'to',
        'weight_i2_i3': 'weight',
    })

    third_hop_3 = three[['I2', 'IPC', 'weight_i2_ipc']].rename(columns={
        'I2': 'from',
        'IPC': 'to',
        'weight_i2_ipc': 'weight',
    })

    third_hop = pd.concat([third_hop_4, third_hop_3], ignore_index=True).drop_duplicates()
    third_hop['from_group'] = third_hop['from'].map(neuron_to_group)
    third_hop['to_group'] = third_hop['to'].map(neuron_to_group)
    third_hop.to_csv('out/hop_3.csv', index=False)

    fourth_hop = four[['I3', 'IPC', 'weight_i3_ipc']].drop_duplicates()
    fourth_hop['from_group'] = fourth_hop['I3'].map(neuron_to_group)
    fourth_hop['to_group'] = fourth_hop['IPC'].map(neuron_to_group)
    fourth_hop = fourth_hop.rename(columns={
        'I3': 'from',
        'IPC': 'to',
        'weight_i3_ipc': 'weight',
        'from_group': 'from_group',
        'to_group': 'to_group',
    })
    fourth_hop.to_csv('out/hop_4.csv', index=False)


def find_unknown_neurons():
    from fafbseg import flywire
    with open(GROUPS_JSON_PATH, 'r') as f:
        groups = load(f)
        neuron_to_group = {}

        for group_name, neuron_ids in groups.items():
            for neuron_id in neuron_ids:
                neuron_to_group[neuron_id] = group_name

    for i in range(1, 5):
        file = f'out/hop_{i}.csv'
        print(f'Analyzing {file}')
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
            single_pred=True,
        )

        for n in neurons:
            if n in neuron_to_group:
                print('in ntg')
                continue

            nt_type = nts[n][0] if isinstance(nts[n], (list, tuple)) else nts[n]
            category = f'hop {i} {nt_type} interneuron'

            if category not in groups:
                print(f'Neuron {n} is uncategorized, putting in category {category}')
                groups[category] = []
            groups[category].append(n)
            neuron_to_group[n] = category

        with open(GROUPS_JSON_PATH, 'w') as f:
            dump(groups, f)

        df['to_group'] = df['to'].map(neuron_to_group).fillna(df['to_group'])
        df['from_group'] = df['from'].map(neuron_to_group).fillna(df['from_group'])
        df.to_csv(file, index=False)


# get_pathways()
organize_hops()
find_unknown_neurons()