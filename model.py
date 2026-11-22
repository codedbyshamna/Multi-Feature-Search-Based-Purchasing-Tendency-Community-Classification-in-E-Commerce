import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.preprocessing import LabelEncoder
from torch_geometric.data import Data
from torch_geometric.nn import GCNConv
from collections import defaultdict

# --------------------------------------
# Load Dataset
# --------------------------------------

data = pd.read_csv("static/data/ecommerce_dataset_fixed.csv")

# Encode categorical IDs
user_encoder = LabelEncoder()
product_encoder = LabelEncoder()
location_encoder = LabelEncoder()

data['user_idx'] = user_encoder.fit_transform(data['user_id'])
data['product_idx'] = product_encoder.fit_transform(data['product_id'])
data['location_idx'] = location_encoder.fit_transform(data['location'])

num_users = data['user_idx'].nunique()
num_products = data['product_idx'].nunique()
num_locations = data['location_idx'].nunique()

# --------------------------------------
# Build Graph for TendGraphNet
# --------------------------------------

edges = []

for _, row in data.iterrows():
    u = row['user_idx']
    p = row['product_idx'] + num_users
    edges.append([u, p])

edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()

num_nodes = num_users + num_products

x = torch.eye(num_nodes)

graph_data = Data(x=x, edge_index=edge_index)

# --------------------------------------
# TendGraphNet Model
# --------------------------------------

class TendGraphNet(nn.Module):

    def __init__(self, input_dim, hidden_dim, output_dim):
        super(TendGraphNet, self).__init__()

        self.conv1 = GCNConv(input_dim, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, output_dim)

    def forward(self, x, edge_index):

        x = self.conv1(x, edge_index)
        x = torch.relu(x)

        x = self.conv2(x, edge_index)

        return x

# --------------------------------------
# Train TendGraphNet
# --------------------------------------

gnn_model = TendGraphNet(num_nodes, 64, 32)

optimizer = optim.Adam(gnn_model.parameters(), lr=0.01)

for epoch in range(50):

    optimizer.zero_grad()

    embeddings = gnn_model(graph_data.x, graph_data.edge_index)

    loss = embeddings.norm()

    loss.backward()
    optimizer.step()

    print(f"GNN Epoch {epoch} Loss:", loss.item())

torch.save(gnn_model.state_dict(), "tendgraphnet.pth")

# --------------------------------------
# Prepare Sequential Data for SeqBehNet
# --------------------------------------

purchase_data = data[data['action'] == "purchase"]

purchase_data = purchase_data.sort_values("purchase_time")

user_sequences = defaultdict(list)

for _, row in purchase_data.iterrows():
    user_sequences[row['user_idx']].append(row['product_idx'])

sequences = list(user_sequences.values())

max_len = 10

X = []
Y = []

for seq in sequences:

    for i in range(1, len(seq)):

        start = max(0, i-max_len)

        X.append(seq[start:i])
        Y.append(seq[i])

# Padding
def pad(seq):
    return seq + [0]*(max_len-len(seq))

X = [pad(s) for s in X]

X = torch.tensor(X)
Y = torch.tensor(Y)

# --------------------------------------
# SeqBehNet (SASRec style)
# --------------------------------------

class SeqBehNet(nn.Module):

    def __init__(self, num_items):

        super(SeqBehNet, self).__init__()

        self.embedding = nn.Embedding(num_items, 64)

        self.transformer = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(d_model=64, nhead=4),
            num_layers=2
        )

        self.fc = nn.Linear(64, num_items)

    def forward(self, seq):

        x = self.embedding(seq)

        x = x.permute(1,0,2)

        x = self.transformer(x)

        x = x[-1]

        out = self.fc(x)

        return out

# --------------------------------------
# Train SeqBehNet
# --------------------------------------

seq_model = SeqBehNet(num_products)

optimizer = optim.Adam(seq_model.parameters(), lr=0.001)

criterion = nn.CrossEntropyLoss()

for epoch in range(20):

    optimizer.zero_grad()

    outputs = seq_model(X)

    loss = criterion(outputs, Y)

    loss.backward()

    optimizer.step()

    print(f"SASRec Epoch {epoch} Loss:", loss.item())

torch.save(seq_model.state_dict(), "seqbehnet.pth")

print("Training Completed")
