"""Chart generation service using Matplotlib with vintage styling."""
import io
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import matplotlib
import matplotlib.figure
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import MaxNLocator

# Use Agg backend for non-interactive mode (headless servers)
matplotlib.use('Agg')

logger = logging.getLogger(__name__)

# Directory for storing generated charts
CHART_DIR = Path(os.environ.get("CHART_DIR", "data/visuals/charts"))


class ChartGenerator:
    """Generate vintage-styled charts for 1920s newspaper articles."""

    def __init__(self):
        """Initialize the chart generator."""
        # Create the chart directory if it doesn't exist
        os.makedirs(CHART_DIR, exist_ok=True)
        
        # Set up vintage color schemes
        self.vintage_colors = [
            "#2F343B",  # Dark slate
            "#77685D",  # Faded brown
            "#8E8268",  # Taupe
            "#A49966",  # Olive
            "#C4AA6B",  # Old gold
            "#D8C99B",  # Parchment
            "#E8E6D9",  # Ivory
        ]
        
        # Create vintage color maps
        self.vintage_cmap = LinearSegmentedColormap.from_list(
            "vintage", self.vintage_colors, N=100
        )
        
        # Define style parameters
        self.style_params = {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "DejaVu Serif", "Old Standard TT"],
            "axes.facecolor": "#F8F7F1",  # Aged paper
            "axes.edgecolor": "#2F343B",  # Dark slate
            "axes.labelcolor": "#2F343B",  # Dark slate
            "axes.grid": True,
            "axes.grid.which": "major",
            "axes.grid.axis": "y",
            "grid.color": "#D8D3C5",  # Light taupe
            "grid.linestyle": "--",
            "grid.linewidth": 0.6,
            "figure.facecolor": "#F8F7F1",  # Aged paper
            "text.color": "#2F343B",  # Dark slate
            "xtick.color": "#2F343B",  # Dark slate
            "ytick.color": "#2F343B",  # Dark slate
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
        }

    def create_chart(
        self,
        chart_type: str,
        data: Dict[str, Any],
        title: str,
        subtitle: Optional[str] = None,
        width: int = 8,
        height: int = 6,
        dpi: int = 100,
    ) -> Tuple[str, matplotlib.figure.Figure]:
        """Create a chart with the specified type and data.

        Args:
            chart_type (str): Type of chart (bar, line, pie, etc.)
            data (Dict[str, Any]): Data for the chart
            title (str): Chart title
            subtitle (Optional[str], optional): Chart subtitle. Defaults to None.
            width (int, optional): Chart width in inches. Defaults to 8.
            height (int, optional): Chart height in inches. Defaults to 6.
            dpi (int, optional): Chart DPI. Defaults to 100.

        Returns:
            Tuple[str, matplotlib.figure.Figure]: Path to saved chart image and the figure object

        Raises:
            ValueError: If chart type is not supported
        """
        chart_creators = {
            "bar": self._create_bar_chart,
            "horizontal_bar": self._create_horizontal_bar_chart,
            "line": self._create_line_chart,
            "pie": self._create_pie_chart,
            "scatter": self._create_scatter_chart,
            "stacked_bar": self._create_stacked_bar_chart,
            "grouped_bar": self._create_grouped_bar_chart,
            "area": self._create_area_chart,
        }

        creator = chart_creators.get(chart_type.lower())
        if not creator:
            raise ValueError(
                f"Unsupported chart type: {chart_type}. "
                f"Supported types: {', '.join(chart_creators.keys())}"
            )

        # Set style parameters for this figure
        with plt.style.context(self.style_params):
            # Create figure with proper dimensions
            fig, ax = plt.subplots(figsize=(width, height), dpi=dpi)
            
            # Create the chart
            creator(fig, ax, data)
            
            # Add title and subtitle
            ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
            if subtitle:
                ax.text(
                    0.5, 0.98, subtitle,
                    horizontalalignment="center",
                    verticalalignment="top",
                    transform=ax.transAxes,
                    fontsize=10,
                    fontstyle="italic",
                )
            
            # Add vintage styling
            self._apply_vintage_styling(fig, ax)
            
            # Add a footer with date
            current_date = datetime.now().strftime("%B %d, %Y")
            fig.text(
                0.99, 0.01, current_date,
                horizontalalignment="right",
                verticalalignment="bottom",
                fontsize=7,
                fontstyle="italic",
                color="#77685D",  # Faded brown
            )
            
            # Generate a unique filename and save the chart
            chart_id = str(uuid.uuid4())
            filename = f"{chart_id}.png"
            filepath = CHART_DIR / filename
            
            # Ensure the layout is tight and save the chart
            plt.tight_layout(pad=2.0)
            plt.savefig(filepath, bbox_inches="tight", facecolor=fig.get_facecolor())
            
            return str(filepath), fig

    def _create_bar_chart(
        self, fig: matplotlib.figure.Figure, ax: plt.Axes, data: Dict[str, Any]
    ) -> None:
        """Create a bar chart.

        Args:
            fig (matplotlib.figure.Figure): The figure object
            ax (plt.Axes): The axes to draw on
            data (Dict[str, Any]): Data for the chart
        """
        categories = data.get("categories", [])
        values = data.get("values", [])
        x_label = data.get("x_label", "")
        y_label = data.get("y_label", "")
        
        # Create the bar chart
        bars = ax.bar(
            categories,
            values,
            color=self.vintage_colors[:len(categories)],
            edgecolor="#2F343B",  # Dark slate
            linewidth=1,
            alpha=0.8,
        )
        
        # Add data labels on top of bars
        self._add_data_labels(ax, bars)
        
        # Set labels
        ax.set_xlabel(x_label, fontsize=10)
        ax.set_ylabel(y_label, fontsize=10)
        
        # Rotate x labels if there are many categories
        if len(categories) > 5:
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
            
        # Set y-axis to start at 0
        ax.set_ylim(bottom=0)
        
        # Use integer ticks on y-axis if values are integers
        if all(isinstance(v, int) for v in values):
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    def _create_horizontal_bar_chart(
        self, fig: matplotlib.figure.Figure, ax: plt.Axes, data: Dict[str, Any]
    ) -> None:
        """Create a horizontal bar chart.

        Args:
            fig (matplotlib.figure.Figure): The figure object
            ax (plt.Axes): The axes to draw on
            data (Dict[str, Any]): Data for the chart
        """
        categories = data.get("categories", [])
        values = data.get("values", [])
        x_label = data.get("x_label", "")
        y_label = data.get("y_label", "")
        
        # Create the horizontal bar chart
        bars = ax.barh(
            categories,
            values,
            color=self.vintage_colors[:len(categories)],
            edgecolor="#2F343B",  # Dark slate
            linewidth=1,
            alpha=0.8,
        )
        
        # Add data labels to the right of bars
        for bar in bars:
            width = bar.get_width()
            ax.text(
                width + (max(values) * 0.02),
                bar.get_y() + bar.get_height() / 2,
                f"{width:,.0f}",
                ha="left",
                va="center",
                fontsize=8,
            )
        
        # Set labels
        ax.set_xlabel(x_label, fontsize=10)
        ax.set_ylabel(y_label, fontsize=10)
            
        # Set x-axis to start at 0
        ax.set_xlim(left=0)
        
        # Use integer ticks on x-axis if values are integers
        if all(isinstance(v, int) for v in values):
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))

    def _create_line_chart(
        self, fig: matplotlib.figure.Figure, ax: plt.Axes, data: Dict[str, Any]
    ) -> None:
        """Create a line chart.

        Args:
            fig (matplotlib.figure.Figure): The figure object
            ax (plt.Axes): The axes to draw on
            data (Dict[str, Any]): Data for the chart
        """
        x_values = data.get("x_values", [])
        y_values = data.get("y_values", [])
        x_label = data.get("x_label", "")
        y_label = data.get("y_label", "")
        
        # Check for multiple line series
        if isinstance(y_values[0], list):
            # Multiple lines
            series_names = data.get("series_names", [f"Series {i+1}" for i in range(len(y_values))])
            
            for i, series in enumerate(y_values):
                color = self.vintage_colors[i % len(self.vintage_colors)]
                ax.plot(
                    x_values,
                    series,
                    marker="o",
                    markersize=5,
                    linewidth=2,
                    color=color,
                    label=series_names[i],
                )
            
            # Add legend
            ax.legend(frameon=True, facecolor="#F8F7F1", edgecolor="#2F343B")
        else:
            # Single line
            ax.plot(
                x_values,
                y_values,
                marker="o",
                markersize=5,
                linewidth=2,
                color=self.vintage_colors[0],
            )
        
        # Set labels
        ax.set_xlabel(x_label, fontsize=10)
        ax.set_ylabel(y_label, fontsize=10)
        
        # Rotate x labels if there are many points
        if len(x_values) > 5:
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    def _create_pie_chart(
        self, fig: matplotlib.figure.Figure, ax: plt.Axes, data: Dict[str, Any]
    ) -> None:
        """Create a pie chart.

        Args:
            fig (matplotlib.figure.Figure): The figure object
            ax (plt.Axes): The axes to draw on
            data (Dict[str, Any]): Data for the chart
        """
        categories = data.get("categories", [])
        values = data.get("values", [])
        
        # Create the pie chart
        wedges, texts, autotexts = ax.pie(
            values,
            labels=categories,
            autopct="%1.1f%%",
            startangle=90,
            colors=self.vintage_colors[:len(categories)],
            wedgeprops={"edgecolor": "#2F343B", "linewidth": 1, "alpha": 0.8},
            textprops={"fontsize": 9},
        )
        
        # Style the percentage text
        for autotext in autotexts:
            autotext.set_fontsize(8)
            autotext.set_weight("bold")
        
        # Equal aspect ratio ensures that pie is drawn as a circle
        ax.axis("equal")
        
        # Add a subtle outer circular border
        ax.set_frame_on(True)
        ax.patch.set_edgecolor("#2F343B")
        ax.patch.set_linewidth(0.5)

    def _create_scatter_chart(
        self, fig: matplotlib.figure.Figure, ax: plt.Axes, data: Dict[str, Any]
    ) -> None:
        """Create a scatter chart.

        Args:
            fig (matplotlib.figure.Figure): The figure object
            ax (plt.Axes): The axes to draw on
            data (Dict[str, Any]): Data for the chart
        """
        x_values = data.get("x_values", [])
        y_values = data.get("y_values", [])
        x_label = data.get("x_label", "")
        y_label = data.get("y_label", "")
        point_sizes = data.get("sizes", [50] * len(x_values))
        
        # Create the scatter plot
        scatter = ax.scatter(
            x_values,
            y_values,
            s=point_sizes,
            c=self.vintage_colors[0],
            edgecolor="#2F343B",
            linewidth=1,
            alpha=0.7,
        )
        
        # Set labels
        ax.set_xlabel(x_label, fontsize=10)
        ax.set_ylabel(y_label, fontsize=10)
        
        # Add trend line if requested
        if data.get("trend_line", False):
            # Calculate trend line
            z = np.polyfit(x_values, y_values, 1)
            p = np.poly1d(z)
            x_trend = np.linspace(min(x_values), max(x_values), 100)
            ax.plot(
                x_trend,
                p(x_trend),
                linestyle="--",
                color="#77685D",  # Faded brown
                linewidth=1.5,
            )

    def _create_stacked_bar_chart(
        self, fig: matplotlib.figure.Figure, ax: plt.Axes, data: Dict[str, Any]
    ) -> None:
        """Create a stacked bar chart.

        Args:
            fig (matplotlib.figure.Figure): The figure object
            ax (plt.Axes): The axes to draw on
            data (Dict[str, Any]): Data for the chart
        """
        categories = data.get("categories", [])
        series_names = data.get("series_names", [])
        series_values = data.get("series_values", [])
        x_label = data.get("x_label", "")
        y_label = data.get("y_label", "")
        
        bottom = np.zeros(len(categories))
        
        for i, values in enumerate(series_values):
            color = self.vintage_colors[i % len(self.vintage_colors)]
            bars = ax.bar(
                categories,
                values,
                bottom=bottom,
                label=series_names[i],
                color=color,
                edgecolor="#2F343B",
                linewidth=1,
                alpha=0.8,
            )
            bottom += values
        
        # Set labels
        ax.set_xlabel(x_label, fontsize=10)
        ax.set_ylabel(y_label, fontsize=10)
        
        # Add legend
        ax.legend(frameon=True, facecolor="#F8F7F1", edgecolor="#2F343B")
        
        # Rotate x labels if there are many categories
        if len(categories) > 5:
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    def _create_grouped_bar_chart(
        self, fig: matplotlib.figure.Figure, ax: plt.Axes, data: Dict[str, Any]
    ) -> None:
        """Create a grouped bar chart.

        Args:
            fig (matplotlib.figure.Figure): The figure object
            ax (plt.Axes): The axes to draw on
            data (Dict[str, Any]): Data for the chart
        """
        categories = data.get("categories", [])
        series_names = data.get("series_names", [])
        series_values = data.get("series_values", [])
        x_label = data.get("x_label", "")
        y_label = data.get("y_label", "")
        
        num_categories = len(categories)
        num_series = len(series_names)
        width = 0.8 / num_series
        
        x = np.arange(num_categories)
        
        for i, values in enumerate(series_values):
            offset = (i - (num_series - 1) / 2) * width
            color = self.vintage_colors[i % len(self.vintage_colors)]
            bars = ax.bar(
                x + offset,
                values,
                width,
                label=series_names[i],
                color=color,
                edgecolor="#2F343B",
                linewidth=1,
                alpha=0.8,
            )
        
        # Set labels
        ax.set_xlabel(x_label, fontsize=10)
        ax.set_ylabel(y_label, fontsize=10)
        
        # Set x-tick positions and labels
        ax.set_xticks(x)
        ax.set_xticklabels(categories)
        
        # Add legend
        ax.legend(frameon=True, facecolor="#F8F7F1", edgecolor="#2F343B")
        
        # Rotate x labels if there are many categories
        if len(categories) > 5:
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    def _create_area_chart(
        self, fig: matplotlib.figure.Figure, ax: plt.Axes, data: Dict[str, Any]
    ) -> None:
        """Create an area chart.

        Args:
            fig (matplotlib.figure.Figure): The figure object
            ax (plt.Axes): The axes to draw on
            data (Dict[str, Any]): Data for the chart
        """
        x_values = data.get("x_values", [])
        y_values = data.get("y_values", [])
        x_label = data.get("x_label", "")
        y_label = data.get("y_label", "")
        
        # Check for multiple area series (stacked)
        if isinstance(y_values[0], list):
            # Stacked area
            series_names = data.get("series_names", [f"Series {i+1}" for i in range(len(y_values))])
            ax.stackplot(
                x_values,
                y_values,
                labels=series_names,
                colors=self.vintage_colors[:len(y_values)],
                alpha=0.8,
                edgecolor="#2F343B",
                linewidth=0.5,
            )
            
            # Add legend
            ax.legend(frameon=True, facecolor="#F8F7F1", edgecolor="#2F343B")
        else:
            # Single area
            ax.fill_between(
                x_values,
                y_values,
                color=self.vintage_colors[0],
                alpha=0.8,
                edgecolor="#2F343B",
                linewidth=0.5,
            )
            
            # Add line on top of area
            ax.plot(
                x_values,
                y_values,
                color="#2F343B",
                linewidth=1.5,
                marker="o",
                markersize=4,
            )
        
        # Set labels
        ax.set_xlabel(x_label, fontsize=10)
        ax.set_ylabel(y_label, fontsize=10)
        
        # Rotate x labels if there are many points
        if len(x_values) > 5:
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    def _apply_vintage_styling(
        self, fig: matplotlib.figure.Figure, ax: plt.Axes
    ) -> None:
        """Apply vintage styling to the chart.

        Args:
            fig (matplotlib.figure.Figure): The figure object
            ax (plt.Axes): The axes to draw on
        """
        # Add a subtle background texture
        ax.patch.set_alpha(0.5)
        
        # Style the border
        for spine in ax.spines.values():
            spine.set_color("#2F343B")  # Dark slate
            spine.set_linewidth(1)
        
        # Style the ticks
        ax.tick_params(axis="both", which="both", direction="out", length=5, width=1, pad=5)
        
        # Add a subtle drop shadow to the figure
        fig.patch.set_alpha(0.8)
        
        # Add a border around the figure
        fig.patch.set_edgecolor("#2F343B")  # Dark slate
        fig.patch.set_linewidth(1)
        
        # Add a vintage watermark
        fig.text(
            0.5, 0.5, "FoglioAI",
            fontsize=40,
            color="#D8D3C5",  # Light taupe
            ha="center",
            va="center",
            alpha=0.1,
            rotation=45,
            transform=fig.transFigure,
        )

    def _add_data_labels(self, ax: plt.Axes, bars) -> None:
        """Add data labels to bar chart bars.

        Args:
            ax (plt.Axes): The axes to draw on
            bars: Bar containers from ax.bar()
        """
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                height + (ax.get_ylim()[1] * 0.01),
                f"{height:,.0f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    def save_to_bytes(self, fig: matplotlib.figure.Figure) -> bytes:
        """Save a figure to bytes buffer.

        Args:
            fig (matplotlib.figure.Figure): The figure to save

        Returns:
            bytes: The figure as PNG bytes
        """
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
        buf.seek(0)
        return buf.getvalue()

    def close_figure(self, fig: matplotlib.figure.Figure) -> None:
        """Close a matplotlib figure to free memory.

        Args:
            fig (matplotlib.figure.Figure): The figure to close
        """
        plt.close(fig) 