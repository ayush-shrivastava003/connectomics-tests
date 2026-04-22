from fafbseg import flywire
from json import load

# TOKEN = open("token.txt", "r").read().strip()
# flywire.set_chunkedgraph_secret(TOKEN)

neurons = load(open('groups.json', 'r'))
edges = flywire.get_adjacency(
    sources=neurons["IR94e"],
    targets=neurons["GNG.SLP.T1 (L)"],
)
edges.to_csv('test.csv')
print(edges.head())