from PyQt5.QtWidgets import QFrame, QVBoxLayout
from PyQt5.QtCore import QObject, QSize
from copy import copy
import numpy as np
from matplotlib import colors
from matplotlib.figure import Figure
from matplotlib.pyplot import cm as colormap
from matplotlib.animation import TimedAnimation
from matplotlib.lines import Line2D
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavToolBar


class LivePlotWidget(QFrame):
    def __init__(self, parent=None, dual_y=True, axes_labels=['x', 'y', 'y2'], lead=[True, True], lead_length=[3, 3],
                 head=[True, True], line_color=['#0173b2', '#e74c3c'],
                 head_color=['#1f78b4', '#ad1f1f'], draw_interval=200):
        super().__init__(parent)

        # Create child widgets
        self.live_plot = LivePlotCanvas(dual_y, axes_labels, lead, lead_length, head, line_color, head_color, draw_interval)
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
    def __init__(self, dual_y: bool, axes_labels: list, lead: list, lead_length: list, head: list, line_color: list,
                 head_color: list, draw_interval: list):

        # Save init values to class variables
        self.dual_y = dual_y
        self.axes_labels = axes_labels
        self.lead = lead
        self.lead_length = lead_length
        for idx, value in enumerate(lead_length):
            self.lead_length[idx] = int(value)
        self.head = head
        self.line_color = line_color
        self.head_color = head_color
        self.line_width = 2

        # Create figure and first set of axes
        self.figure = Figure(figsize=(5, 5))
        self.axes = self.figure.add_subplot(111)
        if dual_y:
            self.axes2 = self.axes.twinx()

        # Plot Data
        self.x = [0]
        self.y1 = [0]
        self.y2 = [0]

        # Create empty dictionaries of main line parts, filled in init_axes
        self.lines = {}
        self.lines2 = {}
        # Create a list to hold old lines (used to store data when we want a color change
        self.old_lines = []
        self.old_lines2 = []

        self.init_axes()

        FigCanvas.__init__(self, self.figure)
        TimedAnimation.__init__(self, self.figure, interval=draw_interval)

    def init_axes(self):
        # Create the line dictionary for the primary axes
        self.lines = {'line': Line2D([], [], color=self.line_color[0])}
        if self.lead[0]:
            self.lines['lead'] = Line2D([], [], color=self.head_color[0], linewidth=self.line_width)
        if self.head[0]:
            self.lines['head'] = Line2D([], [], color=self.head_color[0], marker='*', markeredgecolor=self.head_color[0])

        # Add the lines to the graph
        for key, line in self.lines.items():
            self.axes.add_line(line)

        # If a dual y is called for, setup another spot for data and the second axes
        if self.dual_y:
            if not self.axes2:
                self.axes2 = self.axes.twinx()

            # Create the line dictionary for the secondary axes
            self.lines2 = {'line': Line2D([], [], color=self.line_color[1])}
            if self.lead[1]:
                self.lines2['lead'] = Line2D([], [], color=self.head_color[1], linewidth=self.line_width)
            if self.head[1]:
                self.lines2['head'] = Line2D([], [], color=self.head_color[1], marker='*', markeredgecolor=self.head_color[1])

            # Add the lines for the second set of axes to the plot
            for key, line in self.lines2.items():
                self.axes2.add_line(line)

            # Set axes to match the colors of their main lines if we have dual y otherwise primary will stay black
            self.axes.tick_params(axis='y', labelcolor=self.line_color[0])
            self.axes2.tick_params(axis='y', labelcolor=self.line_color[1])

        # Add labels
        self.change_axes_labels(self.axes_labels)

    def add_data(self, point: list):
        self.x.append(point[0])
        self.y1.append(point[1])
        if self.dual_y:
            self.y2.append(point[2])

    def set_dual_y(self, enable: bool, axes_labels: list):
        self.dual_y = enable
        self.axes_labels = axes_labels
        self.clear_data()
        if enable:
            self.axes2.set_frame_on(True)
            self.axes2.set_visible(True)
            self.init_axes()
        elif not enable:
            # Delete the stuff from the second y axis
            self.axes2.clear()
            self.axes2.set_frame_on(False)
            self.axes2.set_visible(False)
            self.lines2.clear()
            self.old_lines2.clear()
            self.init_axes()

    def set_draw_interval(self, draw_interval: int):
        TimedAnimation._interval = draw_interval

    def set_head(self, head: list, head_color: list):
        if head[0]:
            self.lines['head'] = Line2D([], [], color=head_color[0], marker='*', markeredgecolor=head_color[0])
        elif not head[0]:
            try:
                self.lines.pop('head')
            except KeyError:
                print('Primary axis head was already disabled')

        if self.dual_y:
            if head[1]:
                self.lines['head'] = Line2D([], [], color=head_color[1], marker='*', markeredgecolor=head_color[1])
            elif not head[1]:
                try:
                    self.lines.pop('head')
                except KeyError:
                    print('Secondary axis head was already disabled')

    def set_lead(self, lead: list, lead_color: list):
        if lead[0]:
            self.lines['lead'] = Line2D([], [], color=lead_color[0], linewidth=self.line_width)
        elif not lead[0]:
            try:
                self.lines.pop('lead')
            except KeyError:
                print('Primary axis lead was already disabled.')

        if self.dual_y:
            if lead[1]:
                self.lines['lead'] = Line2D([], [], color=lead_color[1], linewidth=self.line_width)
            elif not lead[1]:
                try:
                    self.lines.pop('lead')
                except KeyError:
                    print('Secondary axis lead was already disabled.')

    def change_line_color(self, line: str, color: list):
        self.lines[line].set_color(color[0])

        if self.dual_y:
            self.lines2[line].set_color(color[1])
            if line == 'line':
                self.axes.tick_params(axis='y', labelcolor=color[0])
                self.axes2.tick_params(axis='y', labelcolor=color[1])


    def start_new_line(self):
        curr_color = colors.to_hex(self.lines['line'].get_color())

        self.old_lines.append(copy(self.lines['line']))
        self.old_lines[-1].set_linestyle(':')

        # FIXME: Verify that new dynamic coloring is working takes color value then adds transparency to previous lines
        old_line_alphas = list(np.linspace(30, 100, len(self.old_lines), False))
        for idx, value in enumerate(old_line_alphas):
            old_line_alphas[idx] = hex(int(256 * (value / 100)))[-2:]

        for idx, line in enumerate(self.old_lines):
            line.set_color(curr_color + old_line_alphas[idx])

        self.axes.add_line(self.old_lines[-1])
        self.x.clear()
        self.y1.clear()

        if self.dual_y:
            curr_color2 = colors.to_hex(self.lines2['line'].get_color())

            self.old_lines2.append(copy(self.lines2['line']))
            self.old_lines2[-1].set_linestyle(':')

            old_line_alphas2 = list(np.linspace(30, 100, len(self.old_lines2), False))
            for idx, value in enumerate(old_line_alphas2):
                old_line_alphas2[idx] = hex(int(256 * (value / 100)))[-2:]

            for idx, line in enumerate(self.old_lines2):
                line.set_color(curr_color2 + old_line_alphas2[idx])

            self.axes2.add_line(self.old_lines2[-1])
            self.y2.clear()

    def clear_data(self):
        self.old_lines.clear()
        self.x.clear()
        self.y1.clear()
        self.axes.clear()

        # Re-add the lines to the graph so that the main line can be plotted again.
        for key, line in self.lines.items():
            self.axes.add_line(line)

        if self.dual_y:
            self.old_lines2.clear()
            self.y2.clear()
            self.axes2.clear()

            for key, line in self.lines2.items():
                self.axes2.add_line(line)

        # Re initialize the axes labels
        self.change_axes_labels(self.axes_labels)

    def change_axes_labels(self, axes_labels: list):
        self.axes_labels = axes_labels
        self.axes.set_xlabel(axes_labels[0], fontsize=14, weight='bold')
        self.axes.set_ylabel(axes_labels[1], fontsize=14, weight='bold')
        if self.dual_y:
            self.axes2.set_ylabel(axes_labels[2], fontsize=14, weight='bold')

    def new_frame_seq(self):
        return iter(range(200))

    def _init_draw(self):
        for key, line in self.lines.items():
            line.set_data([], [])

        if self.dual_y:
            for key, line in self.lines2.items():
                line.set_data([], [])

    def _draw_frame(self, framedata):
        self.lines['line'].set_data(self.x, self.y1)

        try:
            # If there is a lead line, plot lead_length of the data as red
            self.lines['lead'].set_data(self.x[-self.lead_length[0]:],
                                        self.y1[-self.lead_length[0]:])
        except KeyError:
            pass
        except IndexError:
            pass

        try:
            # If there is a head, plot the last data point as a red dot
            self.lines['head'].set_data(self.x[-1], self.y1[-1])
        except KeyError:
            pass
        except IndexError:
            pass

        # Relimit the plot to keep data in view
        self.axes.relim()
        self.axes.autoscale_view()

        # Handle the secondary axis
        if self.dual_y:
            self.lines2['line'].set_data(self.x, self.y2)

            try:
                # If there is a lead line, plot lead_length of the data as red
                self.lines2['lead'].set_data(self.x[-self.lead_length[1]:],
                                            self.y2[-self.lead_length[1]:])
            except KeyError:
                pass
            except IndexError:
                pass

            try:
                # If there is a head, plot the last data point as a red dot
                self.lines2['head'].set_data(self.x[-1], self.y2[-1])
            except KeyError:
                pass
            except IndexError:
                pass

            # Relimit the plot to keep data in view
            self.axes2.relim()
            self.axes2.autoscale_view()

        # Add each relevant line to the drawn artists
        self._drawn_artists = [line for key, line in self.lines.items()]
        for line in self.old_lines:
            self._drawn_artists.append(line)
        # Add the secondary axis lines if relevant
        if self.dual_y:
            for line in self.lines2:
                self._drawn_artists.append(line)

            for line in self.old_lines2:
                self._drawn_artists.append(line)
