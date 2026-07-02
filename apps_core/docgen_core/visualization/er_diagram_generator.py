"""
ER Diagram Generator using NetworkX and Plotly
Generates interactive and static Entity-Relationship diagrams
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

from apps_core.docgen_core.core.models.data_model import DataModel, Table, TableType
from apps_core.docgen_core.core.models.relationship import Relationship, Cardinality


logger = logging.getLogger(__name__)


class ERDiagramGenerator:
    """Generates Entity-Relationship diagrams from Power BI data models"""

    # Color scheme for different table types
    COLORS = {
        'fact': '#1f77b4',      # Blue
        'dimension': '#2ca02c',  # Green
        'calculated': '#ff7f0e', # Orange
        'calendar': '#d62728',   # Red
        'other': '#9467bd'       # Purple
    }

    def __init__(self, data_model: DataModel):
        """
        Initialize ER diagram generator

        Args:
            data_model: DataModel to visualize

        Raises:
            ImportError: If required libraries are not available
        """
        if not NETWORKX_AVAILABLE:
            raise ImportError("NetworkX is required for ER diagram generation. Install with: pip install networkx")

        if not PLOTLY_AVAILABLE:
            logger.warning("Plotly not available. Only NetworkX graphs will be generated.")

        self.data_model = data_model
        self.graph = nx.DiGraph()
        self._build_graph()

    def _build_graph(self):
        """Build NetworkX graph from data model"""
        # Add nodes (tables)
        for table in self.data_model.tables:
            # Determine node color based on table type
            if table.is_fact_table:
                color = self.COLORS['fact']
                node_type = 'fact'
            elif table.table_type == TableType.CALENDAR:
                color = self.COLORS['calendar']
                node_type = 'calendar'
            elif table.table_type == TableType.CALCULATED:
                color = self.COLORS['calculated']
                node_type = 'calculated'
            elif table.is_dimension_table:
                color = self.COLORS['dimension']
                node_type = 'dimension'
            else:
                color = self.COLORS['other']
                node_type = 'other'

            self.graph.add_node(
                table.name,
                color=color,
                node_type=node_type,
                column_count=table.column_count,
                is_hidden=table.is_hidden,
                table_type=table.table_type.value
            )

        # Add edges (relationships)
        for rel in self.data_model.relationships:
            # Create edge label
            direction = "⟷" if rel.is_bidirectional else "→"
            label = f"{rel.cardinality.value} {direction}"

            # Edge color based on relationship type
            if rel.is_many_to_many:
                edge_color = '#d62728'  # Red for many-to-many
                edge_width = 3
            elif rel.is_bidirectional:
                edge_color = '#ff7f0e'  # Orange for bidirectional
                edge_width = 2.5
            elif not rel.is_active:
                edge_color = '#cccccc'  # Gray for inactive
                edge_width = 1
            else:
                edge_color = '#7f7f7f'  # Dark gray for normal
                edge_width = 2

            self.graph.add_edge(
                rel.from_table,
                rel.to_table,
                label=label,
                cardinality=rel.cardinality.value,
                is_bidirectional=rel.is_bidirectional,
                is_active=rel.is_active,
                color=edge_color,
                width=edge_width,
                from_column=rel.from_column,
                to_column=rel.to_column
            )

        logger.info(f"Built graph with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")

    def generate_plotly_figure(self,
                              layout_algorithm: str = 'spring',
                              width: int = 1200,
                              height: int = 800,
                              show_column_count: bool = True) -> Optional[go.Figure]:
        """
        Generate interactive Plotly figure

        Args:
            layout_algorithm: 'spring', 'circular', 'kamada_kawai', or 'shell'
            width: Figure width in pixels
            height: Figure height in pixels
            show_column_count: Show column count in node labels

        Returns:
            Plotly Figure object or None if Plotly not available
        """
        if not PLOTLY_AVAILABLE:
            logger.warning("Plotly not available, cannot generate figure")
            return None

        # Validate width and height (Plotly requires >= 10)
        width = max(10, width) if width else 1200
        height = max(10, height) if height else 800

        # Calculate layout positions
        if layout_algorithm == 'spring':
            pos = nx.spring_layout(self.graph, k=2, iterations=50, seed=42)
        elif layout_algorithm == 'circular':
            pos = nx.circular_layout(self.graph)
        elif layout_algorithm == 'kamada_kawai':
            pos = nx.kamada_kawai_layout(self.graph)
        elif layout_algorithm == 'shell':
            # Separate into shells: fact tables, dimension tables, others
            fact_tables = [n for n, d in self.graph.nodes(data=True) if d.get('node_type') == 'fact']
            dim_tables = [n for n, d in self.graph.nodes(data=True) if d.get('node_type') == 'dimension']
            other_tables = [n for n in self.graph.nodes() if n not in fact_tables and n not in dim_tables]
            shells = [fact_tables, dim_tables, other_tables]
            shells = [s for s in shells if s]  # Remove empty shells
            pos = nx.shell_layout(self.graph, nlist=shells)
        else:
            pos = nx.spring_layout(self.graph, seed=42)

        # Create edge traces
        edge_traces = []

        for edge in self.graph.edges(data=True):
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]

            edge_data = edge[2]
            color = edge_data.get('color', '#7f7f7f')
            width = edge_data.get('width', 2)

            # Create edge line
            edge_trace = go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                mode='lines',
                line=dict(width=width, color=color),
                hoverinfo='text',
                text=f"{edge[0]} → {edge[1]}<br>{edge_data.get('label', '')}",
                showlegend=False
            )
            edge_traces.append(edge_trace)

        # Create node trace
        node_x = []
        node_y = []
        node_colors = []
        node_text = []
        node_hover = []

        for node in self.graph.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)

            node_data = self.graph.nodes[node]
            node_colors.append(node_data.get('color', self.COLORS['other']))

            # Node label
            label = node
            if show_column_count:
                col_count = node_data.get('column_count', 0)
                label = f"{node}<br>({col_count} cols)"
            node_text.append(label)

            # Hover text
            hover = f"<b>{node}</b><br>"
            hover += f"Type: {node_data.get('node_type', 'unknown')}<br>"
            hover += f"Columns: {node_data.get('column_count', 0)}<br>"
            if node_data.get('is_hidden'):
                hover += "Hidden: Yes<br>"

            # Show relationships
            in_edges = list(self.graph.in_edges(node, data=True))
            out_edges = list(self.graph.out_edges(node, data=True))
            hover += f"<br>Relationships: {len(in_edges) + len(out_edges)}"

            node_hover.append(hover)

        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode='markers+text',
            marker=dict(
                size=20,
                color=node_colors,
                line=dict(width=2, color='white')
            ),
            text=node_text,
            textposition="top center",
            textfont=dict(size=10),
            hoverinfo='text',
            hovertext=node_hover,
            showlegend=False
        )

        # Create figure
        fig = go.Figure(
            data=[*edge_traces, node_trace],
            layout=go.Layout(
                title=dict(
                    text='Power BI Data Model - Entity Relationship Diagram',
                    font=dict(size=20)
                ),
                showlegend=False,
                hovermode='closest',
                margin=dict(b=20, l=5, r=5, t=40),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                width=width,
                height=height,
                plot_bgcolor='#1e1e1e',
                paper_bgcolor='#1e1e1e',
                font=dict(color='white')
            )
        )

        return fig

    def save_html(self, output_path: str, **kwargs):
        """
        Save interactive HTML diagram

        Args:
            output_path: Path to save HTML file
            **kwargs: Arguments passed to generate_plotly_figure
        """
        fig = self.generate_plotly_figure(**kwargs)

        if fig:
            fig.write_html(output_path)
            logger.info(f"Saved interactive diagram to {output_path}")
        else:
            logger.warning("Could not generate HTML diagram (Plotly not available)")

    def save_png(self, output_path: str, **kwargs):
        """
        Save static PNG diagram (requires kaleido)

        Args:
            output_path: Path to save PNG file
            **kwargs: Arguments passed to generate_plotly_figure
        """
        fig = self.generate_plotly_figure(**kwargs)

        if fig:
            try:
                fig.write_image(output_path)
                logger.info(f"Saved static diagram to {output_path}")
            except Exception as e:
                logger.error(f"Could not save PNG (kaleido may not be installed): {e}")
                logger.info("Install kaleido with: pip install kaleido")
        else:
            logger.warning("Could not generate PNG diagram (Plotly not available)")

    def get_graph_metrics(self) -> Dict:
        """
        Get metrics about the graph structure

        Returns:
            Dictionary with graph metrics
        """
        metrics = {
            'node_count': self.graph.number_of_nodes(),
            'edge_count': self.graph.number_of_edges(),
            'density': nx.density(self.graph),
            'is_connected': nx.is_weakly_connected(self.graph),
        }

        # Calculate average degree
        if self.graph.number_of_nodes() > 0:
            total_degree = sum(dict(self.graph.degree()).values())
            metrics['average_degree'] = total_degree / self.graph.number_of_nodes()
        else:
            metrics['average_degree'] = 0

        # Find isolated nodes (no relationships)
        metrics['isolated_nodes'] = list(nx.isolates(self.graph))

        # Central tables (highest degree)
        if self.graph.number_of_nodes() > 0:
            degree_dict = dict(self.graph.degree())
            sorted_nodes = sorted(degree_dict.items(), key=lambda x: x[1], reverse=True)
            metrics['most_connected_tables'] = sorted_nodes[:5]
        else:
            metrics['most_connected_tables'] = []

        return metrics

    def get_legend_info(self) -> List[Dict]:
        """
        Get legend information for diagram

        Returns:
            List of legend items
        """
        legend = [
            {'type': 'Fact Table', 'color': self.COLORS['fact'], 'description': 'Tables with primarily numeric columns'},
            {'type': 'Dimension Table', 'color': self.COLORS['dimension'], 'description': 'Descriptive attribute tables'},
            {'type': 'Calculated Table', 'color': self.COLORS['calculated'], 'description': 'Tables created with DAX'},
            {'type': 'Calendar Table', 'color': self.COLORS['calendar'], 'description': 'Date/time dimension'},
            {'type': 'Other', 'color': self.COLORS['other'], 'description': 'Other table types'},
        ]

        return legend
