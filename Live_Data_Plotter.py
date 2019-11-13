from PyQt5.QtWidgets import QFrame, QVBoxLayout
from PyQt5.QtCore import QObject, QSize
from copy import copy
import numpy as np
from matplotlib.figure import Figure
from matplotlib.pyplot import cm as colormap
from matplotlib.animation import TimedAnimation
from matplotlib.lines import Line2D
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavToolBar


class LivePlotWidget(QFrame):
    def __init__(self, axes_labels: list, lead=True, lead_length=3, head=True, line_color='blue', head_color='red', draw_interval=200):
        super().__init__()

        # Create child widgets
        self.live_plot = LivePlotCanvas(axes_labels, lead, lead_length, head, line_color, head_color, draw_interval)
        self.toolbar = NavToolBar(self.live_plot, self, coordinates=True)

        self.init_connections()
        self.init_control_setup()
        self.init_layout()

    def init_connections(self):
        pass

    def init_control_setup(self):
        pass

    def init_layout(self):
        # Create a layout to hold the plot and toolbar
        vbox = QVBoxLayout()
        vbox.addWidget(self.toolbar)
        vbox.addWidget(self.live_plot)

        # Set layout to be the vbox
        self.setLayout(vbox)

    def update_plot_labels(self, axes_labels: list):
        self.live_plot.change_axes_labels(axes_labels)

    def add_data(self, point: list):
        self.live_plot.add_data(point)

    def clear_data(self):
        self.live_plot.clear_data()


class LivePlotCanvas(FigCanvas, TimedAnimation):
    def __init__(self, axes_labels: list, lead: bool, lead_length: int, head: bool, line_color: str,
                 head_color: str, draw_interval: str):

        self.lead_length = int(lead_length)

        # Plot Data
        self.x = [0]
        self.y = [0]

        # Plot figure
        self.figure = Figure(figsize=(5, 5))
        self.axes = self.figure.add_subplot(111)

        # Create the line dictionary
        self.lines = {'line': Line2D([], [], color=line_color)}
        if lead:
            self.lines['lead'] = Line2D([], [], color=head_color, linewidth=2)
        if head:
            self.lines['head'] = Line2D([], [], color=head_color, marker='o', markeredgecolor=head_color)

        # Create a list to hold old lines (used to store data when we want a color change
        self.old_lines = []

        # Add the lines to the graph
        for key, line in self.lines.items():
            self.axes.add_line(line)

        # Add titles
        self.axes_labels = axes_labels
        self.change_axes_labels(axes_labels)

        FigCanvas.__init__(self, self.figure)
        TimedAnimation.__init__(self, self.figure, interval=draw_interval)

    def add_data(self, point: list):
        self.x.append(point[0])
        self.y.append(point[1])

    def change_line_color(self, line: str, color: str):
        self.lines[line].set_color(color)

    def start_new_line(self):
        self.old_lines.append(copy(self.lines['line']))
        self.old_lines[-1].set_linestyle(':')
        # FIXME: Need to get dynamic colors, for now its just winter to match defaults
        colors = colormap.winter(np.linspace(0, 1, len(self.old_lines)))
        for (i, line) in enumerate(reversed(self.old_lines)):
            line.set_color(colors[i])

        self.axes.add_line(self.old_lines[-1])
        self.x.clear()
        self.y.clear()

    def clear_data(self):
        self.old_lines.clear()
        self.x.clear()
        self.y.clear()
        self.axes.clear()

        # Re-add the lines to the graph so that the main line can be plotted again.
        for key, line in self.lines.items():
            self.axes.add_line(line)
        # Re initialize the axes labels
        self.change_axes_labels(self.axes_labels)

    def change_axes_labels(self, axes_labels: list):
        self.axes_labels = axes_labels
        self.axes.set_xlabel(axes_labels[0], fontsize=14, weight='bold')
        self.axes.set_ylabel(axes_labels[1], fontsize=14, weight='bold')

    def new_frame_seq(self):
        return iter(range(200))

    def _init_draw(self):
        for key, line in self.lines.items():
            line.set_data([], [])

    def _draw_frame(self, framedata):
        self.lines['line'].set_data(self.x, self.y)

        try:
            # If there is a lead line, plot lead_length of the data as red
            self.lines['lead'].set_data(self.x[-self.lead_length:],
                                        self.y[-self.lead_length:])
        except KeyError:
            pass
        except IndexError:
            pass

        try:
            # If there is a head, plot the last data point as a red dot
            self.lines['head'].set_data(self.x[-1], self.y[-1])
        except KeyError:
            pass
        except IndexError:
            pass

        # Relimit the plot to keep data in view
        self.axes.relim()
        self.axes.autoscale_view()

        # Add each relevant line to the drawn artists
        self._drawn_artists = [line for key, line in self.lines.items()]
        for line in self.old_lines:
            self._drawn_artists.append(line)
