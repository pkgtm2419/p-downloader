"""
Scheduler and Queue Management Dialog (IDM Feature).
Supports timed queue starts, scheduled stops, simultaneous download limits, and shutdown actions.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QTimeEdit, QSpinBox, QGroupBox, QGridLayout, QPushButton,
    QComboBox, QRadioButton, QWidget
)
from PyQt6.QtCore import QTime
from core.db import DownloadDB

class SchedulerDialog(QDialog):
    def __init__(self, db: DownloadDB, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Scheduler & Queues")
        self.resize(540, 480)
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Queue Selection
        grp_queue = QGroupBox("Selected Queue")
        q_layout = QHBoxLayout(grp_queue)
        self.cmb_queue = QComboBox()
        self.cmb_queue.addItems(["Main Download Queue", "Synchronization Queue"])
        q_layout.addWidget(QLabel("Queue:"))
        q_layout.addWidget(self.cmb_queue)
        layout.addWidget(grp_queue)

        # Schedule Start
        grp_sched = QGroupBox("Timed Schedule")
        grid = QGridLayout(grp_sched)
        grid.setVerticalSpacing(8)

        self.chk_start_time = QCheckBox("Start download at:")
        self.time_start = QTimeEdit()
        self.time_start.setTime(QTime(2, 0, 0))
        grid.addWidget(self.chk_start_time, 0, 0)
        grid.addWidget(self.time_start, 0, 1)

        self.chk_stop_time = QCheckBox("Stop download at:")
        self.time_stop = QTimeEdit()
        self.time_stop.setTime(QTime(7, 0, 0))
        grid.addWidget(self.chk_stop_time, 1, 0)
        grid.addWidget(self.time_stop, 1, 1)

        # Days of week
        grid.addWidget(QLabel("Days of week:"), 2, 0)
        days_layout = QHBoxLayout()
        self.days_checks = []
        for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            chk = QCheckBox(day)
            chk.setChecked(True)
            self.days_checks.append(chk)
            days_layout.addWidget(chk)
        grid.addLayout(days_layout, 2, 1)

        layout.addWidget(grp_sched)

        # Queue Limits
        grp_limits = QGroupBox("Queue Limits")
        lim_layout = QGridLayout(grp_limits)
        lim_layout.addWidget(QLabel("Download files at the same time:"), 0, 0)
        self.spin_simultaneous = QSpinBox()
        self.spin_simultaneous.setRange(1, 10)
        self.spin_simultaneous.setValue(2)
        lim_layout.addWidget(self.spin_simultaneous, 0, 1)
        layout.addWidget(grp_limits)

        # Actions on Completion
        grp_action = QGroupBox("Actions on Queue Completion")
        act_layout = QVBoxLayout(grp_action)
        self.chk_hangup = QCheckBox("Disconnect internet connection")
        self.chk_exit = QCheckBox("Close P-Downloader when finished")
        self.chk_shutdown = QCheckBox("Turn off computer when finished")
        self.chk_sleep = QCheckBox("Put computer to sleep when finished")
        
        act_layout.addWidget(self.chk_hangup)
        act_layout.addWidget(self.chk_exit)
        act_layout.addWidget(self.chk_shutdown)
        act_layout.addWidget(self.chk_sleep)
        layout.addWidget(grp_action)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_apply = QPushButton("Apply Schedule")
        self.btn_apply.clicked.connect(self._save_settings)
        self.btn_close = QPushButton("Close")
        self.btn_close.setObjectName("secondaryBtn")
        self.btn_close.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)

    def _load_settings(self):
        self.chk_start_time.setChecked(self.db.get_setting("sched_start_enabled", "0") == "1")
        st = self.db.get_setting("sched_start_time", "02:00:00")
        self.time_start.setTime(QTime.fromString(st, "hh:mm:ss") if st else QTime(2, 0))

        self.chk_stop_time.setChecked(self.db.get_setting("sched_stop_enabled", "0") == "1")
        et = self.db.get_setting("sched_stop_time", "07:00:00")
        self.time_stop.setTime(QTime.fromString(et, "hh:mm:ss") if et else QTime(7, 0))

        self.spin_simultaneous.setValue(int(self.db.get_setting("simultaneous_downloads", "2")))
        self.chk_exit.setChecked(self.db.get_setting("sched_action_exit", "0") == "1")
        self.chk_shutdown.setChecked(self.db.get_setting("sched_action_shutdown", "0") == "1")
        self.chk_sleep.setChecked(self.db.get_setting("sched_action_sleep", "0") == "1")

    def _save_settings(self):
        self.db.set_setting("sched_start_enabled", "1" if self.chk_start_time.isChecked() else "0")
        self.db.set_setting("sched_start_time", self.time_start.time().toString("hh:mm:ss"))
        self.db.set_setting("sched_stop_enabled", "1" if self.chk_stop_time.isChecked() else "0")
        self.db.set_setting("sched_stop_time", self.time_stop.time().toString("hh:mm:ss"))
        self.db.set_setting("simultaneous_downloads", str(self.spin_simultaneous.value()))
        self.db.set_setting("sched_action_exit", "1" if self.chk_exit.isChecked() else "0")
        self.db.set_setting("sched_action_shutdown", "1" if self.chk_shutdown.isChecked() else "0")
        self.db.set_setting("sched_action_sleep", "1" if self.chk_sleep.isChecked() else "0")
        self.accept()
