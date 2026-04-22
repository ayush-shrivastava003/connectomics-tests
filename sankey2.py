import plotly.graph_objects as go
# TOKEN = open("token.txt", "r").read().strip()

# flywire.set_chunkedgraph_secret(TOKEN)


fig = go.Figure(data=[go.Sankey(
    node = dict(
      pad = 15,
      thickness = 10,
      line = dict(color = "green", width = 0.5),
      label = ["Ir94e\nAch", "Earmuff\nGABA", "OviDNs\nACh"],
      color = ["purple", "yellow", "blue"],
    ),
    link = dict(
        arrowlen = 30,
        source = [0, 1],
        target = [1, 2],
        value = [21, 102], # hard-coded values (which are correct). will update to read from csv
        color = ["rgba(0, 255, 0, 0.5)", "rgba(255, 0, 0, 0.5)"]
    ))])

fig.update_layout(title_text="Sankey Test", font_size=10)
fig.show()