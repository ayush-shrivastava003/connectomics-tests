# Vibe coded Sankey generator for testing purposes. Trying to rule out any issues with the code in sankey.py
# by verifying that the expected values are accurately portrayed in the Sankey.

import pandas as pd
import plotly.graph_objects as go
import sys


def load_data(path="expected.csv"):
	df = pd.read_csv(path)
	# Try to detect columns
	col_names = {c.lower(): c for c in df.columns}
	# possible names
	pre = col_names.get("from_group")
	post = col_names.get("to_group")
	weight = col_names.get("weight")

	df = df[[pre, post, weight]].rename(columns={pre: "pre", post: "post", weight: "value"})
	# aggregate
	df = df.groupby(["pre", "post"], as_index=False)["value"].sum()
	return df


def build_sankey(df):
	labels = list(pd.unique(df["pre"].tolist() + df["post"].tolist()))
	label_to_idx = {l: i for i, l in enumerate(labels)}
	sources = df["pre"].map(label_to_idx)
	targets = df["post"].map(label_to_idx)
	values = df["value"]

	link = dict(source=sources, target=targets, value=values)
	node = dict(label=labels, pad=15, thickness=20)

	fig = go.Figure(go.Sankey(node=node, link=link))
	fig.update_layout(title_text="Synapses between neuron types", font_size=12)
	return fig


def main(path="expected.csv", out="sankey.html"):
	df = load_data(path)
	fig = build_sankey(df)
	fig.write_html(out)
	print(f"Wrote {out}")


if __name__ == "__main__":
	inp = sys.argv[1] if len(sys.argv) > 1 else "expected.csv"
	out = sys.argv[2] if len(sys.argv) > 2 else "sankey.html"
	main(inp, out)
