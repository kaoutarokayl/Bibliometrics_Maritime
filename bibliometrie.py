# -*- coding: utf-8 -*-
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
from wordcloud import WordCloud
import base64
from io import BytesIO
import networkx as nx
import dash
from dash import dcc, html
import plotly.express as px
import dash_cytoscape as cyto  # Pour réseau interactif

sns.set(style="whitegrid")

# ----------------------
# 1️⃣ Charger les données
# ----------------------
df = pd.read_csv("scopus.csv", encoding='utf-8')

# Colonnes utiles
cols_to_keep = ['Author full names','Title','Year','Affiliations','Author Keywords','Index Keywords','Document Type','Cited by']
df = df[cols_to_keep]

# Supprimer doublons et lignes vides
df.drop_duplicates(subset='Title', inplace=True)
df = df.dropna(subset=['Year', 'Author full names'])

# ----------------------
# 2️⃣ Préparer les statistiques
# ----------------------

# Publications par année
pub_per_year = df.groupby('Year')['Title'].count()

# Top auteurs
authors_list = [a.strip() for sublist in df['Author full names'].str.split(';') for a in sublist]
author_count = Counter(authors_list)
top_authors = author_count.most_common(10)

# Top pays
df['Country'] = df['Affiliations'].str.split(',').str[-1].str.strip()
country_count = df['Country'].value_counts()
top_countries = country_count.head(10)

# Top affiliations
top_affiliations = df['Affiliations'].value_counts().head(10)

# Mots-clés
df['Keywords'] = df['Author Keywords'].fillna('') + ';' + df['Index Keywords'].fillna('')
df['Keywords'] = df['Keywords'].str.split(';')
all_keywords = [k.strip() for sublist in df['Keywords'] for k in sublist if k]
keyword_count = Counter(all_keywords)
top_keywords = keyword_count.most_common(15)

# Type de document
doc_type_count = df['Document Type'].value_counts()

# Top articles les plus cités
top_cited = df.sort_values(by='Cited by', ascending=False).head(10)

# ----------------------
# 3️⃣ Nuage de mots-clés
# ----------------------
wc = WordCloud(width=800, height=400, background_color='white').generate_from_frequencies(keyword_count)
buf = BytesIO()
wc.to_image().save(buf, format="PNG")
img_b64 = base64.b64encode(buf.getvalue()).decode()

# ----------------------
# 4️⃣ Réseau de co-auteurs interactif avec Cytoscape
# ----------------------
# Limiter aux 30 auteurs les plus actifs
top_authors_names = [a[0] for a in author_count.most_common(30)]
G = nx.Graph()
for authors in df['Author full names'].dropna():
    auth_list = [a.strip() for a in authors.split(';') if a.strip() in top_authors_names]
    for i in range(len(auth_list)):
        for j in range(i+1, len(auth_list)):
            if G.has_edge(auth_list[i], auth_list[j]):
                G[auth_list[i]][auth_list[j]]['weight'] += 1
            else:
                G.add_edge(auth_list[i], auth_list[j], weight=1)

# Convertir en elements pour Dash Cytoscape
cy_elements = []
for node in G.nodes():
    cy_elements.append({'data': {'id': node, 'label': node}})
for edge in G.edges(data=True):
    cy_elements.append({'data': {'source': edge[0], 'target': edge[1], 'weight': edge[2]['weight']}})

# ----------------------
# 5️⃣ Tableau de bord Dash
# ----------------------
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Analyse Bibliométrique Maritime", style={'textAlign':'center'}),

    html.H2("Publications par année"),
    dcc.Graph(
        figure=px.bar(x=pub_per_year.index, y=pub_per_year.values,
                      labels={'x':'Année','y':'Nombre de publications'},
                      title="Publications par année")
    ),

    html.H2("Top 10 auteurs"),
    dcc.Graph(
        figure=px.bar(x=[a[0] for a in top_authors], y=[a[1] for a in top_authors],
                      labels={'x':'Auteur','y':'Nombre de publications'},
                      title="Top 10 auteurs")
    ),

    html.H2("Top 10 pays"),
    dcc.Graph(
        figure=px.bar(x=top_countries.index, y=top_countries.values,
                      labels={'x':'Pays','y':'Nombre de publications'},
                      title="Top 10 pays")
    ),

    html.H2("Top 10 affiliations"),
    dcc.Graph(
        figure=px.bar(x=top_affiliations.index, y=top_affiliations.values,
                      labels={'x':'Affiliation','y':'Nombre de publications'},
                      title="Top 10 affiliations")
    ),

    html.H2("Type de document"),
    dcc.Graph(
        figure=px.pie(values=doc_type_count.values, names=doc_type_count.index,
                      title="Répartition par type de document")
    ),

    html.H2("Top 10 articles les plus cités"),
    dcc.Graph(
        figure=px.bar(x=top_cited['Title'], y=top_cited['Cited by'],
                      labels={'x':'Article','y':'Nombre de citations'},
                      title="Top 10 articles les plus cités")
    ),

    html.H2("Top 15 mots-clés"),
    dcc.Graph(
        figure=px.bar(x=[k[0] for k in top_keywords], y=[k[1] for k in top_keywords],
                      labels={'x':'Mot-clé','y':'Fréquence'},
                      title="Top 15 mots-clés")
    ),

    html.H2("Nuage de mots-clés"),
    html.Img(src='data:image/png;base64,{}'.format(img_b64), style={'width':'80%'}),

    html.H2("Réseau de co-auteurs (Top 30)"),
    cyto.Cytoscape(
        elements=cy_elements,
        layout={'name': 'cose'},
        style={'width': '100%', 'height': '600px'},
        stylesheet=[
            {'selector': 'node', 'style': {'content': 'data(label)', 'font-size': '12px', 'background-color': '#1f77b4'}},
            {'selector': 'edge', 'style': {'line-color': 'gray', 'width': 'data(weight)'}}
        ]
    )
])

if __name__ == '__main__':
    app.run(debug=True)
