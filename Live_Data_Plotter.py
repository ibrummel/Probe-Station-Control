from PyQt5.QtWidgets import QFrame, QVBoxLayout
from PyQt5.QtCore import QObject, QSize
from matplotlib.figure import Figure
from matplotlib.animation import TimedAnimation
from matplotlib.lines import Line2D
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavToolBar


class LivePlotWidget(QFrame):
    def __init__(self, axes_labels: list, lead=True, lead_length=0.1, head=True, line_color='blue', head_color='red', draw_interval=200):
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


class LivePlotCanvas(FigCanvas, TimedAnimation):
    def __init__(self, axes_labels: list, lead=True, lead_length=0.1, head=True, line_color='blue',
                 head_color='red', draw_interval=200):

        self.lead_length = lead_length

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

        # Add the lines to the graph
        for key, line in self.lines.items():
            self.axes.add_line(line)

        # Add titles
        self.change_axes_labels(axes_labels)

        FigCanvas.__init__(self, self.figure)
        TimedAnimation.__init__(self, self.figure, interval=draw_interval)

    def add_data(self, point: list):
        self.x.append(point[0])
        self.y.append(point[1])

    def change_axes_labels(self, axes_labels: list):
        self.axes.set_xlabel(axes_labels[0], fontsize=14, weight='bold')
        self.axes.set_ylabel(axes_labels[1], fontsize=14, weight='bold')

    def new_frame_seq(self):
        return iter(range(200))

    def _init_draw(self):
        for key, line in self.lines.items():
            line.set_data([], [])

    def _step(self, *args):
        # Extends the _step() method for the TimedAnimation class.
        try:
            TimedAnimation._step(self, *args)
        except Exception:
            print('Unable to draw next frame, stopping animation.')
            TimedAnimation._stop(self)
            pass

    def _draw_frame(self, framedata):
        self.lines['line'].set_data(self.x, self.y)

        try:
            # If there is a lead line, plot lead_length of the data as red
            self.lines['lead'].set_data(self.x[-int(self.axes.get_xlim()*self.lead_length):-1],
                                        self.y[-int(self.axes.get_xlim()*self.lead_length):-1])
        except KeyError:
            pass

        try:
            # If there is a head, plot the last data point as a red dot
            self.lines['head'].set_data(self.x[-1], self.y[-1])
        except KeyError:
            pass

        # Relimit the plot to keep data in view
        self.axes.relim()
        self.axes.autoscale_view()

        # Add each relevant line to the drawn artists
        self._drawn_artists = [line for key, line in self.lines.items()]
