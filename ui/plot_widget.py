import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout
import time

class PlotWidget(QWidget):
    def __init__(self, parent=None, feature_names=None, buffer_duration=4.0):
        super().__init__(parent)
        self.feature_names = feature_names or []
        self.buffer_duration = buffer_duration

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Reset button
        btn_layout = QHBoxLayout()
        reset_btn = QPushButton("↺ Reset Views")
        reset_btn.setStyleSheet("background: #3a3a4c; color: white; padding: 4px;")
        reset_btn.clicked.connect(self.reset_views)
        btn_layout.addWidget(reset_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.win = pg.GraphicsLayoutWidget()
        self.win.setBackground('#1e1e2f')
        layout.addWidget(self.win)

        self.plots = []             # PlotItems
        self.curves_likelihood = [] # cyan curves (left axis)
        self.curves_value = []      # orange curves (right axis)
        self.vb2_list = []          # second ViewBox for raw values

        cols = 3
        for i, name in enumerate(self.feature_names):
            row = i // cols
            col = i % cols
            plot = self.win.addPlot(title=name.replace('_', ' ').title(), row=row, col=col)
            plot.showGrid(x=True, y=True, alpha=0.3)
            plot.setLabel('left', 'Likelihood', color='cyan')
            plot.setLabel('bottom', 'Time (s)', color='#c0c0c0')
            plot.setTitle(name.replace('_', ' ').title(), color='#ffffff', size='9pt')
            plot.getAxis('left').setPen('cyan')
            plot.getAxis('bottom').setPen('#888888')
            plot.setXRange(0, buffer_duration, padding=0)
            plot.setYRange(-0.1, 1.1)
            plot.setMouseEnabled(x=True, y=False)

            # Create a second ViewBox for the raw values
            vb2 = pg.ViewBox()
            plot.scene().addItem(vb2)
            vb2.setXLink(plot)

            # Connect right axis to the second ViewBox
            plot.showAxis('right')
            plot.getAxis('right').setLabel('Value', color='orange')
            plot.getAxis('right').setPen('orange')
            plot.getAxis('right').linkToView(vb2)

            # Ensure vb2 geometry matches the main plot's ViewBox
            def make_geometry_sync(plt, vbox):
                def sync():
                    vbox.setGeometry(plt.vb.sceneBoundingRect())
                return sync

            sync_func = make_geometry_sync(plot, vb2)
            plot.vb.sigResized.connect(sync_func)
            plot.vb.sigRangeChanged.connect(sync_func)   # also sync on pan/zoom
            sync_func()   # initial sync

            # Prevent vb2 from receiving mouse events (avoid panning conflicts)
            vb2.setMouseEnabled(x=False, y=False)

            # Likelihood curve (left axis)
            curve_l = plot.plot(pen=pg.mkPen('cyan', width=2))
            # Raw value curve (right axis)
            curve_v = pg.PlotCurveItem(pen=pg.mkPen('orange', width=1))
            vb2.addItem(curve_v)

            # Store references
            self.plots.append(plot)
            self.curves_likelihood.append(curve_l)
            self.curves_value.append(curve_v)
            self.vb2_list.append(vb2)

            # Default ranges for reset
            plot.default_range = {'x': (0, buffer_duration), 'y_left': (-0.1, 1.1), 'y_right': (-1, 1)}

    def update_plots(self, buffer_data, current_time=None):
        if not buffer_data:
            return
        if current_time is None:
            current_time = time.time()
        # Relative time: oldest buffer entry at x=0, newest at x=buffer_duration
        times = [current_time - d['timestamp'] for d in buffer_data]
        times = [self.buffer_duration - t for t in times]

        for i, name in enumerate(self.feature_names):
            lik = [d.get(name, {}).get('rotation_likelihood', 0.0) for d in buffer_data]
            val = [d.get(name, {}).get('value', 0.0) for d in buffer_data]
            self.curves_likelihood[i].setData(times, lik)
            self.curves_value[i].setData(times, val)

            # Auto-range the right axis based on current values
            if val:
                min_v, max_v = min(val), max(val)
                range_v = max_v - min_v
                if range_v == 0:
                    range_v = 1.0
                self.vb2_list[i].setYRange(min_v - 0.1 * range_v, max_v + 0.1 * range_v, padding=0)

    def reset_views(self):
        for plot, vb2 in zip(self.plots, self.vb2_list):
            dr = plot.default_range
            plot.setXRange(*dr['x'], padding=0)
            plot.setYRange(*dr['y_left'], padding=0)
            vb2.setYRange(*dr['y_right'], padding=0)