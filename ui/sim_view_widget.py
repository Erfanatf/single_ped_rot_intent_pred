import pyqtgraph as pg
import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtCore import QTimer, Qt


class SimViewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # Status label
        self.status_label = QLabel("Waiting for simulator data...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #ffaa00; font-size: 12px;")
        layout.addWidget(self.status_label)

        # Plot
        self.plot = pg.PlotWidget()
        self.plot.setAspectLocked(True)
        self.plot.showGrid(True, True, alpha=0.3)
        self.plot.setBackground("#1e1e2f")
        self.plot.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.plot)

        # ---- Static plot items (with names for legend) ----
        self.user_scatter = pg.ScatterPlotItem(size=10, pen="w", brush="g", name="User")
        self.user_arrow = pg.ArrowItem(
            angle=0,
            tipAngle=30,
            baseAngle=20,
            headLen=15,
            tailLen=10,
            pen="w",
            brush="g",
        )

        self.robot_scatter = pg.ScatterPlotItem(
            size=12, pen="w", brush="c", name="Robot"
        )
        self.robot_arrow = pg.ArrowItem(
            angle=0,
            tipAngle=30,
            baseAngle=20,
            headLen=15,
            tailLen=10,
            pen="w",
            brush="c",
        )

        self.goal_scatter = pg.ScatterPlotItem(size=8, pen="y", brush="y", name="Goal")

        self.arc_curve = pg.PlotCurveItem(
            pen=pg.mkPen("c", width=2, style=Qt.DashLine), name="Robot Predicted Arc"
        )
        self.user_arc_curve = pg.PlotCurveItem(
            pen=pg.mkPen("g", width=2, style=Qt.DotLine), name="User Predicted Arc"
        )
        self.user_traj_curve = pg.PlotCurveItem(
            pen=pg.mkPen("g", width=1, style=Qt.DashLine), name="User Path"
        )

        self.ped_scatter = pg.ScatterPlotItem(
            size=8, pen="w", brush="r", name="Pedestrians"
        )

        # Add all items to plot
        self.plot.addItem(self.user_scatter)
        self.plot.addItem(self.user_arrow)
        self.plot.addItem(self.robot_scatter)
        self.plot.addItem(self.robot_arrow)
        self.plot.addItem(self.goal_scatter)
        self.plot.addItem(self.arc_curve)
        self.plot.addItem(self.user_arc_curve)
        self.plot.addItem(self.user_traj_curve)
        self.plot.addItem(self.ped_scatter)

        # ---- Legend (auto‑populated from named items) ----
        self.legend = self.plot.addLegend(offset=(10, 10))
        self.legend.setBrush(pg.mkBrush("#1e1e2fee"))
        self.legend.setPen(pg.mkPen("#ffffff"))
        self.legend.setLabelTextColor("#ffffff")

        # ---- Speed readouts ----
        speed_layout = QHBoxLayout()
        self.user_speed_label = QLabel("User speed: -- m/s")
        self.user_speed_label.setStyleSheet("color: #00ff88; font-size: 12px;")
        self.robot_speed_label = QLabel("Robot speed: -- m/s")
        self.robot_speed_label.setStyleSheet("color: #00ffff; font-size: 12px;")
        speed_layout.addWidget(self.user_speed_label)
        speed_layout.addWidget(self.robot_speed_label)
        speed_layout.addStretch()
        layout.addLayout(speed_layout)

        # --- Simulation performance readouts ----
        self.sim_rt_label = QLabel("Sim RT: --")
        self.sim_rt_label.setStyleSheet("color: #ffaa00; font-size: 12px;")
        self.loop_time_label = QLabel("Loop: --ms")
        self.loop_time_label.setStyleSheet("color: #ffaa00; font-size: 12px;")
        speed_layout.addWidget(self.sim_rt_label)
        speed_layout.addWidget(self.loop_time_label)
        self.pred_time_label = QLabel("Pred: --ms")
        self.pred_time_label.setStyleSheet("color: #ffaa00; font-size: 12px;")
        speed_layout.addWidget(self.pred_time_label)
        self.ctrl_time_label = QLabel("Ctrl: --ms")
        self.ctrl_time_label.setStyleSheet("color: #ffaa00; font-size: 12px;")
        speed_layout.addWidget(self.ctrl_time_label)

        # Centering
        self.follow_user = True
        self.view_radius = 10.0
        self.current_user_pos = None
        self.data_received = False

        self.timer = QTimer()
        self.timer.timeout.connect(self._update_view_range)

    def update_state(self, state):
        if not state:
            return

        if not self.data_received:
            self.data_received = True
            self.status_label.setText("Receiving simulation data")
            self.status_label.setStyleSheet("color: #00ff88; font-size: 12px;")
            self.timer.start(100)

        # User
        ux, uy, uf = state.get("user", (0, 0, 0))
        self.user_scatter.setData([ux], [uy])
        self.user_arrow.setPos(ux, uy)
        self.user_arrow.setRotation(np.rad2deg(uf))
        self.current_user_pos = (ux, uy)

        # Robot
        rx, ry, rt = state.get("robot", (0, 0, 0))
        self.robot_scatter.setData([rx], [ry])
        self.robot_arrow.setPos(rx, ry)
        self.robot_arrow.setRotation(np.rad2deg(rt))

        # Goal
        gx, gy = state.get("goal", (0, 0))
        self.goal_scatter.setData([gx], [gy])

        # Robot's predicted arc
        arc = state.get("arc", [])
        if arc:
            self.arc_curve.setData([p[0] for p in arc], [p[1] for p in arc])
        else:
            self.arc_curve.clear()

        # User's predicted arc
        user_arc = state.get("user_arc", [])
        if user_arc:
            self.user_arc_curve.setData(
                [p[0] for p in user_arc], [p[1] for p in user_arc]
            )
        else:
            self.user_arc_curve.clear()

        # Ground-truth trajectory
        traj = state.get("user_traj", [])
        if traj:
            self.user_traj_curve.setData([p[0] for p in traj], [p[1] for p in traj])

        # Pedestrians
        peds = state.get("pedestrians", [])
        if peds:
            spots = [{"pos": (p[0], p[1]), "size": p[2] * 20} for p in peds]
            self.ped_scatter.setData(spots=spots)
        else:
            self.ped_scatter.clear()

        # Speed readouts
        user_speed = state.get("user_speed", None)
        robot_speed = state.get("robot_speed", None)
        if user_speed is not None:
            self.user_speed_label.setText(f"User speed: {user_speed:.2f} m/s")
        if robot_speed is not None:
            self.robot_speed_label.setText(f"Robot speed: {robot_speed:.2f} m/s")

        # Performance readouts
        sim_rt = state.get("sim_rt_factor", None)
        pred_ms = state.get("pred_time_ms", None)
        ctrl_ms = state.get('ctrl_time_ms', None)

        if sim_rt is not None:
            self.sim_rt_label.setText(f"Sim RT: {sim_rt:.2f}")
        loop_ms = state.get("loop_time_ms", None)
        if loop_ms is not None:
            self.loop_time_label.setText(f"Loop: {loop_ms:.0f}ms")
        if pred_ms is not None:
            self.pred_time_label.setText(f"Pred: {pred_ms:.1f}ms")
        if ctrl_ms is not None:
            self.ctrl_time_label.setText(f"Ctrl: {ctrl_ms:.1f}ms")

    def _update_view_range(self):
        if self.follow_user and self.current_user_pos is not None:
            cx, cy = self.current_user_pos
            self.plot.setXRange(cx - self.view_radius, cx + self.view_radius, padding=0)
            self.plot.setYRange(cy - self.view_radius, cy + self.view_radius, padding=0)

    def set_follow_user(self, follow: bool):
        self.follow_user = follow
