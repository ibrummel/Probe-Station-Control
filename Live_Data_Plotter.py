from PyQt5.QtWidgets import QFrame, QVBoxLayout
from PyQt5.QtCore import QObject, QSize
from copy import copy
import numpy as np
from matplotlib import colors
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavToolBar


class LivePlotWidget(QFrame):
    def __init__(self, parent=None, dual_y=True, axes_labels=['x', 'y', 'y2'],
                 lead=[True, True], lead_length=[3, 3],
                 head=[True, True], line_color=['#0173b2', '#e74c3c'],
                 head_color=['#1f78b4', '#ad1f1f'], draw_interval=200):
        super().__init__(parent)

        # Create child widgets
        self.canvas = LivePlotCanvas(dual_y, axes_labels, lead, lead_length,
                                     head, line_color, head_color, draw_interval)
        self.toolbar = NavToolBar(self.canvas, self, coordinates=True)

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
        vbox.addWidget(self.canvas)

        # Set layout to be the vbox
        self.setLayout(vbox)

    def update_plot_labels(self, axes_labels: list):
        self.canvas.change_axes_labels(axes_labels)

    def add_data(self, point: list):
        self.canvas.add_data(point)

    def clear_data(self):
        self.canvas.clear_data()


class LivePlotCanvas(FigCanvas):
    def __init__(self, dual_y: bool, axes_labels: list, lead: list,
                 lead_length: list, head: list, line_color: list,
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
        self.axes2 = self.axes.twinx()
        if not dual_y:
            self.axes2.set_visible(False)
            self.axes2.set_frame_on(False)

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
        self.old_line_alphas = []

        self.init_axes()
        FigCanvas.__init__(self, self.figure)
        self.draw()

    def init_axes(self):
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

        self._draw_frame()

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
            self.axes2.set_frame_on(False)
            self.axes2.set_visible(False)
            self.lines2.clear()
            self.old_lines2.clear()
            self.init_axes()

    def set_head(self, head: list, head_color: list):
        self.head = head
        self.head_color = head_color

    def set_lead(self, lead: list):
        self.lead = lead

    def change_line_color(self, line_color: list, head_color: list):
        self.line_color = line_color

    def start_new_line(self):
        self.old_lines.append({'x': copy(self.x), 'y': copy(self.y1)})

        self.old_line_alphas = list(np.linspace(30, 100, len(self.old_lines), False))
        for idx, value in enumerate(self.old_line_alphas):
            self.old_line_alphas[idx] = hex(int(256 * (value / 100)))[-2:]

        if self.dual_y:
            self.old_lines2.append({'x': copy(self.x), 'y': copy(self.y2)})

        self.x.clear()
        self.y1.clear()
        self.y2.clear()

    def clear_data(self):
        self.old_lines.clear()
        self.x.clear()
        self.y1.clear()
        self.y2.clear()
        self.axes.clear()
        self.old_lines2.clear()
        self.axes2.clear()
        
        # Re initialize the axes labels
        self.change_axes_labels(self.axes_labels)

    def change_axes_labels(self, axes_labels: list):
        self.axes_labels = axes_labels
        self.axes.set_xlabel(axes_labels[0], fontsize=14, weight='bold')
        self.axes.set_ylabel(axes_labels[1], fontsize=14, weight='bold')
        if self.dual_y:
            self.axes2.set_ylabel(axes_labels[2], fontsize=14, weight='bold')

    def _draw_frame(self):
        # Clear both sets of axes
        self.axes.clear()
        self.axes2.clear()
        
        try:
            # Add the current primary axis data to the plot
            self.axes.plot(self.x, self.y1, color=self.line_color[0])
            if self.lead[0]:
                self.axes.plot(self.x[-self.lead_length[0]:],
                               self.y1[-self.lead_length[0]:],
                               color=self.head_color[0])
            if self.head[0]:
                self.axes.plot(self.x[-1], self.y1[-1],
                               color=self.head_color[0])
            # Plot the old lines for the primary axis
            prim_color = colors.to_hex(self.line_color[0])
            for idx, line_data in enumerate(self.old_lines):
                self.axes.plot(line_data['x'], line_data['y'],
                               linestyle=':',
                               color=prim_color+self.old_line_alphas[idx])
            # Add current secondary axis data to the plot, if necessary
            if self.dual_y:
                self.axes2.plot(self.x, self.y2, color=self.line_color[1])
                if self.lead[1]:
                    self.axes2.plot(self.x[-self.lead_length[1]:],
                                    self.y2[-self.lead_length[1]:],
                                    color=self.head_color[1])
                if self.head[1]:
                    self.axes2.plot(self.x[-1], self.y2[-1],
                                    color=self.head_color[1])
                    # Plot the old lines for the secondary axis
                    sec_color = colors.to_hex(self.line_color[1])
                    for idx, line_data in enumerate(self.old_lines2):
                        self.axes.plot(line_data['x'], line_data['y'],
                                       linestyle=':',
                                       color=sec_color + self.old_line_alphas[idx])
        except IndexError as err:
            print(err, 'Likely a result of attempting to replot too quickly after clearing the old data')
        # Relimit the plot to keep data in view
        self.axes.relim()
        self.axes.autoscale_view(True, True, True)
        # Relimit the plot to keep data in view for secondary y
        self.axes2.relim()
        self.axes2.autoscale_view(True, True, True)

        self.change_axes_labels(self.axes_labels)
        # Draw the plot with new stuff
        self.draw()
