from json import dump, load
import pandas as pd

def pathways(three_hops = False):
    from fafbseg import flywire
    neurons = load(open('data/groups.json', 'r'))

    start = flywire.synapses.get_connectivity(
        neurons['Ir94e'],
        downstream=True,
        filtered=True,
        materialization=783
    )

    start = start[start['weight'] >= 5]

    # SUPER TIME INTENSIVE STEP!!
    if three_hops:    
        middle = flywire.synapses.get_connectivity(
            start['post'].tolist(),
            downstream=True,
            filtered=True,
            materialization=783
    )

    end = flywire.synapses.get_connectivity(
        neurons["OviDN"],
        upstream=True,
        filtered=True,
        materialization=783
    )


    two = start.merge(end, left_on='post', right_on='pre', how='inner')
    two = two[(two['weight_x'] >= 5) & (two['weight_y'] >= 5)]
    two = two.rename(columns={'pre_x': 'start', 'post_x': 'middle', 'post_y': 'end'})
    two.to_csv('data/two.csv', index=False)

    if three_hops:
        two_to_three = middle.merge(end, left_on='post', right_on='pre', how='inner')
        two_to_three = two_to_three[(two_to_three['weight_x'] >= 5)]
        three = start.merge(two_to_three, left_on='post', right_on='pre_x', how='inner')
        three = three[(three['weight'] >= 5) & (three['weight_x'] >= 5) & (three['weight_y'] >= 5)]
        three.to_csv('data/three.csv', index=False)

def organize_hops():
    three = pd.read_csv('data/three.csv')

    with open('data/groups.json', 'r') as f:
        groups = load(f)

    neuron_to_group = {}
    for group_name, neuron_ids in groups.items():
        for neuron_id in neuron_ids:
            neuron_to_group[neuron_id] = group_name

    three['pre_start_group'] = three['pre'].map(neuron_to_group) # Ir94e
    three['post_start_group'] = three['post'].map(neuron_to_group) # GNG.SLP, Earmuff
    three['post_middle_group'] = three['post_x'].map(neuron_to_group) # interneuron
    three['post_end_group'] = three['post_y'].map(neuron_to_group) # OviDN
    three = three[(three['pre_start_group'] != three['post_start_group']) & (three['post_end_group'] == 'OviDN')]
    three.dropna(subset='pre_start_group', inplace=True)

    first_hop = three[['pre', 'post', 'weight', 'pre_start_group', 'post_start_group']].drop_duplicates()
    first_hop = first_hop.rename(columns={
        'pre': 'from',
        'post': 'to',
        'weight': 'weight',
        'pre_start_group': 'from_group',
        'post_start_group': 'to_group'
    })
    first_hop.to_csv('out/hop_1.csv', index=False)

    second_hop = three[['post', 'post_x', 'weight_x', 'post_start_group', 'post_middle_group']].drop_duplicates()
    second_hop = second_hop.rename(columns={
        'post': 'from',
        'post_x': 'to',
        'weight_x': 'weight',
        'post_start_group': 'from_group',
        'post_middle_group': 'to_group'
    })
    second_hop.to_csv('out/hop_2.csv', index=False)

    third_hop = three[['post_x', 'post_y', 'weight_y', 'post_middle_group', 'post_end_group']].drop_duplicates()
    third_hop = third_hop.rename(columns={
        'post_x': 'from',
        'post_y': 'to',
        'weight_y': 'weight',
        'post_middle_group': 'from_group',
        'post_end_group': 'to_group'
    })
    third_hop.to_csv('out/hop_3.csv', index=False)

def find_unknown_neurons():
    from fafbseg import flywire
    with open('../pathways/data/groups.json', 'r') as f:
        groups = load(f)
        neuron_to_group = {}

        for group_name, neuron_ids in groups.items():
            for neuron_id in neuron_ids:
                neuron_to_group[neuron_id] = group_name

    for i in range(1, 4): # repeat twice - once for hop 1 and once for hop 2, since hop 3 is only OviDNs
        file = f'out/hop_{i}.csv'
        print(f"Analyzing {file}")
        df = pd.read_csv(file)
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
            category = f"hop {i} {nts[n][0]} interneuron"
            if groups.get(category, None) is None:
                print(f"Neuron {n} is uncategorized, putting in category {category}")
                groups[category] = [n]
                neuron_to_group[n] = category
            else:
                groups[category].append(n)
                neuron_to_group[n] = category

        with open('../pathways/data/groups.json', 'w') as f:
            dump(groups, f)
        
        # Update the dataframe with the assigned groups
        df['to_group'] = df['to'].map(neuron_to_group).fillna(df['to_group'])
        df['from_group'] = df['from'].map(neuron_to_group).fillna(df['from_group'])
        
        # Save the updated dataframe back to the original CSV file
        df.to_csv(file, index=False)

    

pathways(three_hops=True)
organize_hops()
find_unknown_neurons()