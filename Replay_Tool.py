"""
Nifty Replay Tool

Author: ANB HFund
X: https://x.com/AnbHfund
Created: 2026

Free & open-source for learning and research purposes.
"""


import sys
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QVBoxLayout, QPushButton, QWidget, QLabel, 
                            QSlider, QHBoxLayout, QDateEdit, QSpinBox, QCheckBox,
                            QComboBox, QGroupBox, QFormLayout, QDoubleSpinBox,
                            QFileDialog)
from PyQt5.QtCore import Qt, QTimer, QDate
import os
import pyqtgraph as pg
from pyqtgraph import DateAxisItem, InfiniteLine, GraphicsLayoutWidget
import numpy as np
from datetime import time
import pytz

class CandleReplay(QWidget):
    def __init__(self):
        super().__init__()
        
        # Set timezone for Indian market
        self.local_tz = pytz.timezone('Asia/Kolkata')
        self.utc_tz = pytz.utc

        self.setWindowTitle("Enhanced Candle Replay with Indicators")
        self.setGeometry(100, 100, 1600, 900)
        
        # Button states
        self.is_playing = False

        self.df = None
        self.current_idx = 0
        self.speed = 500  # milliseconds
        self.visible_candle_count = 100  # Default visible candles
        self.current_file_path = None  # Track loaded file
        
        # Indicator settings
        self.show_ema = True
        self.ema_period = 14
        self.show_sma = False
        self.sma_period = 20
        self.show_vwap = True
        self.show_bollinger = False
        self.bb_period = 20
        self.bb_std = 2.0
        
        # RSI and MACD settings
        self.show_rsi = False
        self.rsi_period = 14
        self.show_macd = False
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9

        # Main horizontal layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        self.setLayout(main_layout)

        # Left sidebar
        self.create_left_sidebar()
        main_layout.addWidget(self.sidebar, stretch=0)

        # Right side - Chart area
        self.create_chart_area()
        main_layout.addWidget(self.chart_widget, stretch=1)

        # Load initial data
        self.load_default_data()

        self.timer = QTimer()
        self.timer.timeout.connect(self.next_candle)

    def create_left_sidebar(self):
        """Create left sidebar with controls"""
        self.sidebar = QWidget()
        self.sidebar.setMaximumWidth(350)
        self.sidebar.setMinimumWidth(250)
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(5, 5, 5, 5)
        sidebar_layout.setSpacing(10)
        self.sidebar.setLayout(sidebar_layout)

        # Data Loading Section
        data_group = QGroupBox("📊 Data Settings")
        data_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        data_layout = QVBoxLayout()
        data_layout.setSpacing(5)
        
        # Manual file selection
        file_select_layout = QHBoxLayout()
        self.browse_button = QPushButton("📁 Browse File")
        self.browse_button.clicked.connect(self.browse_file)
        file_select_layout.addWidget(self.browse_button)
        data_layout.addLayout(file_select_layout)
        
        self.file_path_label = QLabel("No file selected")
        self.file_path_label.setWordWrap(True)
        self.file_path_label.setStyleSheet("color: gray; font-size: 9px; padding: 2px;")
        data_layout.addWidget(self.file_path_label)
        
        # Separator
        separator = QLabel("─" * 30)
        separator.setAlignment(Qt.AlignCenter)
        data_layout.addWidget(separator)
        
        # Default data loading
        default_layout = QFormLayout()
        default_layout.setSpacing(5)
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(["1min", "3min", "5min", "15min", "30min", "1hour"])
        self.timeframe_combo.setCurrentText("3min")
        default_layout.addRow("Timeframe:", self.timeframe_combo)
        
        self.reload_button = QPushButton("🔄 Load Default Data")
        self.reload_button.clicked.connect(self.load_default_data)
        default_layout.addRow(self.reload_button)
        
        data_layout.addLayout(default_layout)
        
        data_group.setLayout(data_layout)
        sidebar_layout.addWidget(data_group)

        # Indicators Section
        indicators_group = QGroupBox("📈 Indicators")
        indicators_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        indicators_layout = QVBoxLayout()
        indicators_layout.setSpacing(5)
        
        # EMA
        ema_layout = QHBoxLayout()
        self.ema_check = QCheckBox("EMA")
        self.ema_check.setChecked(True)
        self.ema_check.stateChanged.connect(self.on_indicator_changed)
        self.ema_spin = QSpinBox()
        self.ema_spin.setRange(5, 200)
        self.ema_spin.setValue(14)
        self.ema_spin.valueChanged.connect(self.on_indicator_changed)
        ema_layout.addWidget(self.ema_check, stretch=1)
        ema_layout.addWidget(self.ema_spin, stretch=1)
        indicators_layout.addLayout(ema_layout)
        
        # SMA
        sma_layout = QHBoxLayout()
        self.sma_check = QCheckBox("SMA")
        self.sma_check.setChecked(False)
        self.sma_check.stateChanged.connect(self.on_indicator_changed)
        self.sma_spin = QSpinBox()
        self.sma_spin.setRange(5, 200)
        self.sma_spin.setValue(20)
        self.sma_spin.valueChanged.connect(self.on_indicator_changed)
        sma_layout.addWidget(self.sma_check, stretch=1)
        sma_layout.addWidget(self.sma_spin, stretch=1)
        indicators_layout.addLayout(sma_layout)
        
        # VWAP
        self.vwap_check = QCheckBox("VWAP")
        self.vwap_check.setChecked(True)
        self.vwap_check.stateChanged.connect(self.on_indicator_changed)
        indicators_layout.addWidget(self.vwap_check)
        
        # Bollinger Bands
        bb_layout = QVBoxLayout()
        bb_header = QHBoxLayout()
        self.bb_check = QCheckBox("Bollinger Bands")
        self.bb_check.setChecked(False)
        self.bb_check.stateChanged.connect(self.on_indicator_changed)
        bb_header.addWidget(self.bb_check)
        bb_layout.addLayout(bb_header)
        
        bb_params = QFormLayout()
        bb_params.setSpacing(5)
        self.bb_period_spin = QSpinBox()
        self.bb_period_spin.setRange(5, 100)
        self.bb_period_spin.setValue(20)
        self.bb_period_spin.valueChanged.connect(self.on_indicator_changed)
        bb_params.addRow("Period:", self.bb_period_spin)
        
        self.bb_std_spin = QDoubleSpinBox()
        self.bb_std_spin.setRange(0.5, 5.0)
        self.bb_std_spin.setSingleStep(0.1)
        self.bb_std_spin.setValue(2.0)
        self.bb_std_spin.valueChanged.connect(self.on_indicator_changed)
        bb_params.addRow("Std Dev:", self.bb_std_spin)
        bb_layout.addLayout(bb_params)
        indicators_layout.addLayout(bb_layout)
        
        # RSI
        rsi_layout = QHBoxLayout()
        self.rsi_check = QCheckBox("RSI")
        self.rsi_check.setChecked(False)
        self.rsi_check.stateChanged.connect(self.on_indicator_changed)
        self.rsi_spin = QSpinBox()
        self.rsi_spin.setRange(5, 50)
        self.rsi_spin.setValue(14)
        self.rsi_spin.valueChanged.connect(self.on_indicator_changed)
        rsi_layout.addWidget(self.rsi_check, stretch=1)
        rsi_layout.addWidget(self.rsi_spin, stretch=1)
        indicators_layout.addLayout(rsi_layout)
        
        # MACD
        macd_layout = QVBoxLayout()
        macd_header = QHBoxLayout()
        self.macd_check = QCheckBox("MACD")
        self.macd_check.setChecked(False)
        self.macd_check.stateChanged.connect(self.on_indicator_changed)
        macd_header.addWidget(self.macd_check)
        macd_layout.addLayout(macd_header)
        
        macd_params = QFormLayout()
        macd_params.setSpacing(5)
        self.macd_fast_spin = QSpinBox()
        self.macd_fast_spin.setRange(5, 50)
        self.macd_fast_spin.setValue(12)
        self.macd_fast_spin.valueChanged.connect(self.on_indicator_changed)
        macd_params.addRow("Fast:", self.macd_fast_spin)
        
        self.macd_slow_spin = QSpinBox()
        self.macd_slow_spin.setRange(10, 100)
        self.macd_slow_spin.setValue(26)
        self.macd_slow_spin.valueChanged.connect(self.on_indicator_changed)
        macd_params.addRow("Slow:", self.macd_slow_spin)
        
        self.macd_signal_spin = QSpinBox()
        self.macd_signal_spin.setRange(5, 30)
        self.macd_signal_spin.setValue(9)
        self.macd_signal_spin.valueChanged.connect(self.on_indicator_changed)
        macd_params.addRow("Signal:", self.macd_signal_spin)
        macd_layout.addLayout(macd_params)
        indicators_layout.addLayout(macd_layout)
        
        indicators_group.setLayout(indicators_layout)
        sidebar_layout.addWidget(indicators_group)

        # Display Settings
        display_group = QGroupBox("⚙️ Display")
        display_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        display_layout = QFormLayout()
        display_layout.setSpacing(5)
        
        self.candle_count_spin = QSpinBox()
        self.candle_count_spin.setMinimum(20)
        self.candle_count_spin.setMaximum(1000)
        self.candle_count_spin.setValue(self.visible_candle_count)
        self.candle_count_spin.valueChanged.connect(self.update_candle_count)
        display_layout.addRow("Visible Candles:", self.candle_count_spin)
        
        self.optimize_check = QCheckBox("Optimize Performance")
        self.optimize_check.setChecked(True)
        display_layout.addRow(self.optimize_check)
        
        display_group.setLayout(display_layout)
        sidebar_layout.addWidget(display_group)

        # Statistics Section
        self.stats_group = QGroupBox("📊 Statistics")
        self.stats_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        self.stats_layout = QVBoxLayout()
        self.stats_layout.setSpacing(5)
        self.stats_label = QLabel("No data loaded")
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet("font-size: 10px; padding: 2px;")
        self.stats_layout.addWidget(self.stats_label)
        
        # Date range display
        self.date_range_label = QLabel("")
        self.date_range_label.setWordWrap(True)
        self.date_range_label.setStyleSheet("font-weight: bold; color: #2c3e50; padding: 5px; background-color: #ecf0f1; border-radius: 3px; font-size: 10px;")
        self.stats_layout.addWidget(self.date_range_label)
        
        self.stats_group.setLayout(self.stats_layout)
        sidebar_layout.addWidget(self.stats_group)

        sidebar_layout.addStretch()

    def create_chart_area(self):
        """Create chart area with price and volume panels"""
        self.chart_widget = QWidget()
        chart_layout = QVBoxLayout()
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.setSpacing(5)
        self.chart_widget.setLayout(chart_layout)

        # Graphics layout for stacked charts
        self.graphics_layout = GraphicsLayoutWidget()
        self.graphics_layout.setBackground('w')
        chart_layout.addWidget(self.graphics_layout, stretch=1)

        # Price chart (main) - row 0
        self.date_axis = DateAxisItem(orientation='bottom')
        self.price_plot = self.graphics_layout.addPlot(row=0, col=0, axisItems={'bottom': self.date_axis})
        self.price_plot.setMouseEnabled(x=True, y=True)
        self.price_plot.showGrid(x=True, y=True, alpha=0.3)
        self.price_plot.setLabel('left', 'Price')
        self.price_plot.setMinimumHeight(200)

        # Crosshair setup for price chart
        self.vline = InfiniteLine(angle=90, movable=False, pen=pg.mkPen('b', width=1))
        self.hline = InfiniteLine(angle=0, movable=False, pen=pg.mkPen('b', width=1))
        self.price_plot.addItem(self.vline, ignoreBounds=True)
        self.price_plot.addItem(self.hline, ignoreBounds=True)
        
        # Create hover info label on the chart
        self.hover_label = pg.TextItem(anchor=(0, 0), color='k', fill=(255, 255, 255, 200), border='k')
        self.hover_label.setZValue(1000)
        self.price_plot.addItem(self.hover_label)
        self.hover_label.setVisible(False)

        # Volume chart - row 1
        self.volume_plot = self.graphics_layout.addPlot(row=1, col=0)
        self.volume_plot.setMouseEnabled(x=True, y=True)
        self.volume_plot.showGrid(x=False, y=True, alpha=0.3)
        self.volume_plot.setLabel('left', 'Volume')
        self.volume_plot.setMinimumHeight(80)
        
        # RSI chart - row 2 (will be shown/hidden based on checkbox)
        self.rsi_plot = self.graphics_layout.addPlot(row=2, col=0)
        self.rsi_plot.setMouseEnabled(x=True, y=True)
        self.rsi_plot.showGrid(x=True, y=True, alpha=0.3)
        self.rsi_plot.setLabel('left', 'RSI')
        self.rsi_plot.setMinimumHeight(80)
        self.rsi_plot.hide()  # Initially hidden
        
        # MACD chart - row 3 (will be shown/hidden based on checkbox)
        self.macd_plot = self.graphics_layout.addPlot(row=3, col=0)
        self.macd_plot.setMouseEnabled(x=True, y=True)
        self.macd_plot.showGrid(x=True, y=True, alpha=0.3)
        self.macd_plot.setLabel('left', 'MACD')
        self.macd_plot.setMinimumHeight(80)
        self.macd_plot.hide()  # Initially hidden
        
        # Link X-axes
        self.volume_plot.setXLink(self.price_plot)
        self.rsi_plot.setXLink(self.price_plot)
        self.macd_plot.setXLink(self.price_plot)

        # Enable mouse interaction
        self.graphics_layout.scene().sigMouseMoved.connect(self.mouse_moved)
        self.graphics_layout.scene().sigMouseClicked.connect(self.mouse_clicked)

        # Control panel
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)

        # Playback controls
        self.play_button = QPushButton("▶️ Play")
        self.play_button.clicked.connect(self.play)
        self.play_button.setFixedWidth(80)
        controls_layout.addWidget(self.play_button)

        self.pause_button = QPushButton("⏸️ Pause")
        self.pause_button.clicked.connect(self.pause)
        self.pause_button.setFixedWidth(80)
        controls_layout.addWidget(self.pause_button)

        self.reset_button = QPushButton("🔄 Reset")
        self.reset_button.clicked.connect(self.reset)
        self.reset_button.setFixedWidth(80)
        controls_layout.addWidget(self.reset_button)

        self.zoom_fit_button = QPushButton("🔍 Zoom Fit")
        self.zoom_fit_button.clicked.connect(self.zoom_fit)
        self.zoom_fit_button.setFixedWidth(90)
        controls_layout.addWidget(self.zoom_fit_button)

        # Speed control
        controls_layout.addWidget(QLabel("Speed:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(100)
        self.speed_slider.setMaximum(2000)
        self.speed_slider.setValue(self.speed)
        self.speed_slider.setTickInterval(100)
        self.speed_slider.setFixedWidth(100)
        self.speed_slider.valueChanged.connect(self.update_speed)
        controls_layout.addWidget(self.speed_slider)
        
        speed_label = QLabel(f"{self.speed}ms")
        speed_label.setFixedWidth(50)
        self.speed_slider.valueChanged.connect(lambda v: speed_label.setText(f"{v}ms"))
        controls_layout.addWidget(speed_label)

        controls_layout.addStretch()

        # Navigation controls
        controls_layout.addWidget(QLabel("Date:"))
        self.date_picker = QDateEdit()
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setFixedWidth(120)
        self.date_picker.dateChanged.connect(self.jump_to_date)
        controls_layout.addWidget(self.date_picker)

        controls_layout.addWidget(QLabel("Candle:"))
        self.candle_slider = QSpinBox()
        self.candle_slider.setMinimum(1)
        self.candle_slider.setFixedWidth(80)
        self.candle_slider.valueChanged.connect(self.jump_to_candle)
        controls_layout.addWidget(self.candle_slider)

        chart_layout.addLayout(controls_layout)

        self.info_label = QLabel()
        self.info_label.setStyleSheet("padding: 5px; background-color: #f8f9fa; border: 1px solid #dee2e6;")
        chart_layout.addWidget(self.info_label)

    def resizeEvent(self, event):
        """Handle window resize event"""
        super().resizeEvent(event)
        # Force update of the chart layout
        self.update_chart_layout()

    def update_chart_layout(self):
        """Update the chart layout dynamically based on visible indicators"""
        if not hasattr(self, 'graphics_layout'):
            return
            
        # Reset all row stretches
        for i in range(4):
            self.graphics_layout.ci.layout.setRowStretchFactor(i, 0)
        
        # Price chart always gets the most space
        self.graphics_layout.ci.layout.setRowStretchFactor(0, 3)
        
        # Volume chart gets fixed space
        self.graphics_layout.ci.layout.setRowStretchFactor(1, 1)
        
        # RSI and MACD get space if visible
        row = 2
        if self.show_rsi:
            self.graphics_layout.ci.layout.setRowStretchFactor(row, 1)
            row += 1
        if self.show_macd:
            self.graphics_layout.ci.layout.setRowStretchFactor(row, 1)

    def browse_file(self):
        """Open file dialog to select CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSV Data File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            self.current_file_path = file_path
            self.load_data_from_file(file_path)

    def load_default_data(self):
        """Load default data file based on timeframe selection"""
        timeframe = self.timeframe_combo.currentText()
        default_file = f"Nifty_Fut_{timeframe}.csv"
        
        # Check multiple relative locations
        possible_paths = [
            # Option 1: In a 'data' folder next to the script
            os.path.join("data", default_file),
            # Option 2: In the same folder as the script
            default_file,
            # Option 3: In a 'Data' folder (capital D)
            os.path.join("Data", default_file),
            # Option 4: In 'data_files' folder
            os.path.join("data_files", default_file),
        ]
        
        for file_path in possible_paths:
            if os.path.exists(file_path):
                self.current_file_path = file_path
                self.load_data_from_file(file_path)
                self.file_path_label.setText(f"Loaded: {default_file}")
                return
        
        # If no file found, show helpful instructions
        error_msg = f"❌ Default file not found: Nifty_Fut_{timeframe}.csv<br>"
        error_msg += f"<br>Please place your data file in one of these locations:"
        for path in possible_paths:
            error_msg += f"<br>• {path}"
        
        error_msg += "<br><br>Or click 'Browse' to select a file manually."
        self.stats_label.setText(error_msg)
        self.file_path_label.setText(f"File missing: {default_file}")

    def load_data_from_file(self, file_path):
        """Load data from specified CSV file"""
        try:
            self.df = pd.read_csv(
                file_path,
                parse_dates=['datetime'],
                dayfirst=True
            )
            
            if not pd.api.types.is_datetime64_any_dtype(self.df['datetime']):
                self.df['datetime'] = pd.to_datetime(self.df['datetime'], dayfirst=True)
            
            self.df['datetime'] = self.df['datetime'].dt.tz_localize(self.local_tz)
            self.df = self.df.sort_values('datetime').reset_index(drop=True)
            self.df = self.df[self.df['datetime'].dt.tz_convert(self.local_tz).dt.time.between(time(9,15), time(15,30))]
            self.df = self.df.drop_duplicates('datetime')
            self.df['continuous_time'] = self.create_continuous_timeline(self.df['datetime'])
            
            if self.df.empty:
                raise ValueError("No data remaining after filtering trading hours")
            
            # Update UI elements
            self.date_picker.setDate(self.df.iloc[0]['datetime'].date())
            self.candle_slider.setMaximum(len(self.df))
            self.candle_slider.setValue(1)
            self.current_idx = 0
            
            # Update file path label
            file_name = os.path.basename(file_path)
            self.file_path_label.setText(f"✅ Loaded: {file_name}")
            self.file_path_label.setStyleSheet("color: green; font-size: 9px; padding: 2px;")
            
            self.update_statistics()
            self.update_chart()
            
        except FileNotFoundError:
            self.stats_label.setText(f"❌ Error: File not found<br>{file_path}")
            self.file_path_label.setText(f"❌ File not found")
            self.file_path_label.setStyleSheet("color: red; font-size: 9px; padding: 2px;")
        except Exception as e:
            self.stats_label.setText(f"❌ Error loading file:<br>{str(e)}")
            self.file_path_label.setText(f"❌ Error: {str(e)[:50]}")
            self.file_path_label.setStyleSheet("color: red; font-size: 9px; padding: 2px;")

    def update_button_states(self):
        """Update button appearance based on state"""
        if self.is_playing:
            self.play_button.setStyleSheet("""
                QPushButton {
                    background-color: #1e8449;
                    color: white;
                    font-weight: bold;
                    padding: 8px;
                    border-radius: 5px;
                    border: 3px solid #145a32;
                }
            """)
            self.pause_button.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    font-weight: bold;
                    padding: 8px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
        else:
            self.play_button.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    font-weight: bold;
                    padding: 8px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #229954;
                }
                QPushButton:pressed {
                    background-color: #1e8449;
                }
            """)
            self.pause_button.setStyleSheet("""
                QPushButton {
                    background-color: #95a5a6;
                    color: white;
                    font-weight: bold;
                    padding: 8px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #7f8c8d;
                }
            """)

    def on_indicator_changed(self):
        """Handle indicator setting changes"""
        self.show_ema = self.ema_check.isChecked()
        self.ema_period = self.ema_spin.value()
        self.show_sma = self.sma_check.isChecked()
        self.sma_period = self.sma_spin.value()
        self.show_vwap = self.vwap_check.isChecked()
        self.show_bollinger = self.bb_check.isChecked()
        self.bb_period = self.bb_period_spin.value()
        self.bb_std = self.bb_std_spin.value()
        
        # RSI and MACD settings
        self.show_rsi = self.rsi_check.isChecked()
        self.rsi_period = self.rsi_spin.value()
        self.show_macd = self.macd_check.isChecked()
        self.macd_fast = self.macd_fast_spin.value()
        self.macd_slow = self.macd_slow_spin.value()
        self.macd_signal = self.macd_signal_spin.value()
        
        if self.df is not None:
            self.update_chart()

    def update_statistics(self):
        """Update statistics display"""
        if self.df is None or len(self.df) == 0:
            return
            
        stats_text = f"<b>Data Summary:</b><br>"
        stats_text += f"Total Candles: {len(self.df)}<br>"
        stats_text += f"<br><b>Price Range:</b><br>"
        stats_text += f"High: {self.df['high'].max():.2f}<br>"
        stats_text += f"Low: {self.df['low'].min():.2f}<br>"
        
        if 'volume' in self.df.columns:
            stats_text += f"<br><b>Volume:</b><br>"
            stats_text += f"Total: {self.df['volume'].sum():,.0f}<br>"
            stats_text += f"Avg: {self.df['volume'].mean():,.0f}"
        
        self.stats_label.setText(stats_text)
        
        # Update date range display
        start_date = self.df.iloc[0]['datetime'].strftime('%d-%m-%Y')
        end_date = self.df.iloc[-1]['datetime'].strftime('%d-%m-%Y')
        date_range_text = f"📅 <b>Data Range:</b><br>{start_date}<br>to<br>{end_date}"
        self.date_range_label.setText(date_range_text)

    def create_continuous_timeline(self, datetimes):
        datetimes = datetimes.sort_values()
        continuous_time = []
        continuous_counter = 0
        
        for dt in datetimes:
            if len(continuous_time) == 0:
                continuous_time.append(0)
            else:
                continuous_time.append(continuous_counter)
            continuous_counter += 3  # 3 minutes per candle
        
        return continuous_time

    def update_chart(self):
        if self.df is None:
            return
            
        # Clear all plots
        self.price_plot.clear()
        self.volume_plot.clear()
        self.rsi_plot.clear()
        self.macd_plot.clear()
        
        # Always add crosshair items back after clearing
        self.price_plot.addItem(self.vline, ignoreBounds=True)
        self.price_plot.addItem(self.hline, ignoreBounds=True)
        self.price_plot.addItem(self.hover_label)
    
        start_idx = max(0, self.current_idx - self.visible_candle_count + 1)
        self.visible_df = self.df.iloc[start_idx:self.current_idx + 1].reset_index(drop=True)
    
        x_values = self.visible_df['continuous_time'].values
        
        # Show/hide RSI and MACD plots based on checkbox
        if self.show_rsi:
            self.rsi_plot.show()
            self.plot_rsi()
        else:
            self.rsi_plot.hide()
            
        if self.show_macd:
            self.macd_plot.show()
            self.plot_macd()
        else:
            self.macd_plot.hide()
        
        # Update the layout
        self.update_chart_layout()
        
        # Plot price indicators
        min_price = self.visible_df['low'].min()
        max_price = self.visible_df['high'].max()
        price_buffer = (max_price - min_price) * 0.05

        # Plot indicators on price chart
        if self.show_vwap and 'vwap' in self.visible_df.columns:
            vwap_line = pg.PlotCurveItem(
                x=x_values,
                y=self.visible_df['vwap'].values,
                pen=pg.mkPen('k', width=2, style=Qt.DotLine),
                symbol='o',
                symbolSize=4,
                symbolPen='k',
                symbolBrush='k',
                name="VWAP"
            )
            self.price_plot.addItem(vwap_line)
        
        if self.show_ema and len(self.visible_df) >= self.ema_period:
            ema = self.visible_df['close'].ewm(span=self.ema_period, adjust=False).mean().values
            ema_line = pg.PlotCurveItem(
                x=x_values,
                y=ema,
                pen=pg.mkPen('b', width=2),
                name=f"EMA {self.ema_period}"
            )
            self.price_plot.addItem(ema_line)
        
        if self.show_sma and len(self.visible_df) >= self.sma_period:
            sma = self.visible_df['close'].rolling(window=self.sma_period).mean().values
            sma_line = pg.PlotCurveItem(
                x=x_values,
                y=sma,
                pen=pg.mkPen('orange', width=2),
                name=f"SMA {self.sma_period}"
            )
            self.price_plot.addItem(sma_line)
        
        if self.show_bollinger and len(self.visible_df) >= self.bb_period:
            sma = self.visible_df['close'].rolling(window=self.bb_period).mean()
            std = self.visible_df['close'].rolling(window=self.bb_period).std()
            upper_band = sma + (std * self.bb_std)
            lower_band = sma - (std * self.bb_std)
            
            self.price_plot.plot(x_values, upper_band.values, pen=pg.mkPen('purple', width=1, style=Qt.DashLine))
            self.price_plot.plot(x_values, sma.values, pen=pg.mkPen('purple', width=1))
            self.price_plot.plot(x_values, lower_band.values, pen=pg.mkPen('purple', width=1, style=Qt.DashLine))
    
        # Plot candles
        if self.visible_candle_count > 300 and self.optimize_check.isChecked():
            self.plot_with_arrays(self.visible_df, x_values)
        else:
            self.plot_individual_candles(self.visible_df, x_values)
        
        # Plot volume - FIXED: Ensure volume always plots
        if 'volume' in self.visible_df.columns and len(self.visible_df['volume']) > 0:
            colors = ['g' if self.visible_df.iloc[i]['close'] >= self.visible_df.iloc[i]['open'] else 'r' 
                     for i in range(len(self.visible_df))]
            
            # Create volume bars
            volume_bars = pg.BarGraphItem(
                x=x_values,
                height=self.visible_df['volume'].values,
                width=2.5,
                brushes=colors,
                pens=colors
            )
            self.volume_plot.addItem(volume_bars)
            
            # Set volume Y-range
            if len(self.visible_df['volume']) > 0:
                max_vol = self.visible_df['volume'].max()
                if max_vol > 0:
                    self.volume_plot.setYRange(0, max_vol * 1.1, padding=0)
    
        # Auto-scale Y-axis with buffer
        self.price_plot.setYRange(min_price - price_buffer, max_price + price_buffer)
                
        # Set X-axis range
        if len(x_values) > 0:
            view_start = x_values[0] - 15
            view_end = x_values[-1] + 15
            self.price_plot.setXRange(view_start, view_end, padding=0)

        self.create_custom_ticks(self.visible_df)
        self.update_info_label(self.visible_df)
        
        # Force update of the layout
        self.graphics_layout.updateGeometry()

    def plot_rsi(self):
        """Plot RSI indicator"""
        if len(self.visible_df) < self.rsi_period + 1:
            return
            
        # Calculate RSI
        delta = self.visible_df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=self.rsi_period, min_periods=self.rsi_period).mean()
        avg_loss = loss.rolling(window=self.rsi_period, min_periods=self.rsi_period).mean()
        
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        
        x_values = self.visible_df['continuous_time'].values
        
        # Plot RSI line
        self.rsi_plot.plot(x_values, rsi.values, pen=pg.mkPen('purple', width=2), name=f'RSI({self.rsi_period})')
        
        # Add overbought/oversold lines
        overbought_line = pg.InfiniteLine(pos=70, angle=0, pen=pg.mkPen('r', width=1, style=Qt.DashLine))
        oversold_line = pg.InfiniteLine(pos=30, angle=0, pen=pg.mkPen('g', width=1, style=Qt.DashLine))
        self.rsi_plot.addItem(overbought_line)
        self.rsi_plot.addItem(oversold_line)
        
        # Set RSI Y-range
        self.rsi_plot.setYRange(0, 100, padding=0.1)

    def plot_macd(self):
        """Plot MACD indicator"""
        if len(self.visible_df) < max(self.macd_fast, self.macd_slow):
            return
            
        # Calculate MACD
        exp1 = self.visible_df['close'].ewm(span=self.macd_fast, adjust=False).mean()
        exp2 = self.visible_df['close'].ewm(span=self.macd_slow, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=self.macd_signal, adjust=False).mean()
        histogram = macd - signal
        
        x_values = self.visible_df['continuous_time'].values
        
        # Plot MACD line
        self.macd_plot.plot(x_values, macd.values, pen=pg.mkPen('b', width=2), name='MACD')
        
        # Plot Signal line
        self.macd_plot.plot(x_values, signal.values, pen=pg.mkPen('r', width=2), name='Signal')
        
        # Plot Histogram
        colors = ['g' if h >= 0 else 'r' for h in histogram]
        for i in range(len(x_values)):
            if i < len(histogram) and not np.isnan(histogram.iloc[i]):
                bar = pg.BarGraphItem(
                    x=[x_values[i]],
                    height=[histogram.iloc[i]],
                    width=2,
                    brush=colors[i],
                    pen=colors[i]
                )
                self.macd_plot.addItem(bar)
        
        # Add zero line
        zero_line = pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen('k', width=1))
        self.macd_plot.addItem(zero_line)
        
        # Auto-scale Y-axis for MACD
        if len(macd) > 0 and len(signal) > 0:
            combined = pd.concat([macd, signal, histogram])
            valid_vals = combined.dropna()
            if len(valid_vals) > 0:
                min_val = valid_vals.min()
                max_val = valid_vals.max()
                buffer = abs(max_val - min_val) * 0.1 if max_val != min_val else 0.1
                self.macd_plot.setYRange(min_val - buffer, max_val + buffer, padding=0)

    def plot_individual_candles(self, df, x_values):
        """Plot each candle individually"""
        for idx, row in df.iterrows():
            x = x_values[idx]
            color = 'g' if row['close'] >= row['open'] else 'r'
            pen = pg.mkPen(color, width=1)

            # Candle body
            rect_top = max(row['open'], row['close'])
            rect_bottom = min(row['open'], row['close'])
            
            if rect_top != rect_bottom:
                body = pg.BarGraphItem(
                    x=[x],
                    height=[rect_top - rect_bottom],
                    width=2.5,
                    y0=rect_bottom,
                    brush=color,
                    pen=pen
                )
                self.price_plot.addItem(body)

            # Wick
            wick_pen = pg.mkPen(color, width=1)
            self.price_plot.plot([x, x], [row['low'], row['high']], pen=wick_pen)

    def plot_with_arrays(self, df, x_values):
        """Plot using arrays for better performance"""
        opens = df['open'].values
        closes = df['close'].values
        lows = df['low'].values
        highs = df['high'].values
        
        colors = np.where(closes >= opens, 'g', 'r')
        
        for x, low, high, color in zip(x_values, lows, highs, colors):
            self.price_plot.plot([x, x], [low, high], pen=pg.mkPen(color, width=1))
        
        tops = np.maximum(opens, closes)
        bottoms = np.minimum(opens, closes)
        widths = np.full(len(x_values), 2.5)
        
        candles = pg.BarGraphItem(
            x=x_values,
            height=tops - bottoms,
            width=widths,
            y0=bottoms,
            brush=colors,
            pen=colors
        )
        self.price_plot.addItem(candles)

    def update_info_label(self, visible_df):
        current_candle = self.df.iloc[self.current_idx]
        local_time = current_candle['datetime'].astimezone(self.local_tz)
        info = f"<b>Candle {self.current_idx + 1}/{len(self.df)}:</b> Date: {local_time.strftime('%d-%m-%Y %H:%M:%S %Z')}<br>"
        info += f"O: {current_candle['open']:.2f}, H: {current_candle['high']:.2f}, "
        info += f"L: {current_candle['low']:.2f}, C: {current_candle['close']:.2f}"
        
        if 'volume' in current_candle and pd.notna(current_candle['volume']):
            info += f", Vol: {current_candle['volume']:,.0f}"
        
        self.info_label.setText(info)

        self.candle_slider.blockSignals(True)
        self.candle_slider.setValue(self.current_idx + 1)
        self.candle_slider.blockSignals(False)

    def create_custom_ticks(self, visible_df):
        """Create custom time axis labels"""
        unique_days = visible_df['datetime'].dt.date.unique()
        major_ticks = []
        major_labels = []
        minor_ticks = []
        minor_labels = []
        
        for day_idx, day in enumerate(unique_days):
            day_df = visible_df[visible_df['datetime'].dt.date == day]
            if len(day_df) == 0:
                continue
            
            # Major tick at start of day with date
            open_time = day_df.iloc[0]['continuous_time']
            major_ticks.append(open_time)
            major_labels.append(day.strftime('%d-%m-%Y'))
            
            # Minor ticks for each candle time
            for idx, row in day_df.iterrows():
                tick_pos = row['continuous_time']
                time_label = row['datetime'].strftime('%H:%M')
                minor_ticks.append(tick_pos)
                minor_labels.append(time_label)
        
        axis = self.price_plot.getAxis('bottom')
        axis.setTicks([
            [(pos, label) for pos, label in zip(major_ticks, major_labels)],
            [(pos, label) for pos, label in zip(minor_ticks, minor_labels)]
        ])

    def mouse_moved(self, pos):
        """Handle mouse movement over chart"""
        if self.df is None or not hasattr(self, 'visible_df'):
            return
            
        if self.price_plot.sceneBoundingRect().contains(pos):
            mouse_point = self.price_plot.vb.mapSceneToView(pos)
            x_val = mouse_point.x()
            y_val = mouse_point.y()
            
            self.vline.setValue(x_val)
            self.hline.setValue(y_val)
            
            # Find closest candle
            x_values = self.visible_df['continuous_time'].values
            if len(x_values) == 0:
                return
                
            # Find index of closest x value
            idx = np.searchsorted(x_values, x_val, side='left')
            idx = min(max(idx, 0), len(self.visible_df) - 1)
            
            # Check if mouse is close enough to a candle
            if idx < len(x_values) and abs(x_values[idx] - x_val) < 10:
                candle = self.visible_df.iloc[idx]
                
                # Format datetime
                dt = candle['datetime']
                date_str = dt.strftime('%d-%m-%Y')
                time_str = dt.strftime('%H:%M:%S')
                
                # Build hover text with all information
                hover_text = f"<b>Date:</b> {date_str}<br>"
                hover_text += f"<b>Time:</b> {time_str}<br>"
                hover_text += f"<b>Open:</b> {candle['open']:.2f}<br>"
                hover_text += f"<b>High:</b> {candle['high']:.2f}<br>"
                hover_text += f"<b>Low:</b> {candle['low']:.2f}<br>"
                hover_text += f"<b>Close:</b> {candle['close']:.2f}<br>"
                
                if 'volume' in candle and pd.notna(candle['volume']):
                    hover_text += f"<b>Volume:</b> {int(candle['volume']):,}<br>"
                
                # Add Day High/Low
                if 'day_high' in candle and 'day_low' in candle:
                    hover_text += f"<b>Day High:</b> {candle['day_high']:.2f}<br>"
                    hover_text += f"<b>Day Low:</b> {candle['day_low']:.2f}<br>"
                
                # Add VWAP if available
                if 'vwap' in candle and pd.notna(candle['vwap']):
                    hover_text += f"<b>VWAP:</b> {candle['vwap']:.2f}<br>"
                
                # Calculate and add indicators for this candle
                if self.show_ema and len(self.visible_df) >= self.ema_period:
                    ema = self.visible_df['close'].ewm(span=self.ema_period, adjust=False).mean()
                    if idx < len(ema) and pd.notna(ema.iloc[idx]):
                        hover_text += f"<b>EMA({self.ema_period}):</b> {ema.iloc[idx]:.2f}<br>"
                
                if self.show_sma and len(self.visible_df) >= self.sma_period:
                    sma = self.visible_df['close'].rolling(window=self.sma_period).mean()
                    if idx < len(sma) and pd.notna(sma.iloc[idx]):
                        hover_text += f"<b>SMA({self.sma_period}):</b> {sma.iloc[idx]:.2f}<br>"
                
                # Add RSI if enabled
                if self.show_rsi and len(self.visible_df) >= self.rsi_period + 1:
                    delta = self.visible_df['close'].diff()
                    gain = delta.where(delta > 0, 0)
                    loss = -delta.where(delta < 0, 0)
                    avg_gain = gain.rolling(window=self.rsi_period, min_periods=self.rsi_period).mean()
                    avg_loss = loss.rolling(window=self.rsi_period, min_periods=self.rsi_period).mean()
                    rs = avg_gain / avg_loss.replace(0, np.nan)
                    rsi = 100 - (100 / (1 + rs))
                    if idx < len(rsi) and pd.notna(rsi.iloc[idx]):
                        hover_text += f"<b>RSI({self.rsi_period}):</b> {rsi.iloc[idx]:.2f}<br>"
                
                # Add MACD if enabled
                if self.show_macd and len(self.visible_df) >= max(self.macd_fast, self.macd_slow):
                    exp1 = self.visible_df['close'].ewm(span=self.macd_fast, adjust=False).mean()
                    exp2 = self.visible_df['close'].ewm(span=self.macd_slow, adjust=False).mean()
                    macd = exp1 - exp2
                    signal = macd.ewm(span=self.macd_signal, adjust=False).mean()
                    if idx < len(macd) and pd.notna(macd.iloc[idx]):
                        hover_text += f"<b>MACD:</b> {macd.iloc[idx]:.2f}<br>"
                        if pd.notna(signal.iloc[idx]):
                            hover_text += f"<b>Signal:</b> {signal.iloc[idx]:.2f}<br>"
                
                # Show the hover label
                self.hover_label.setHtml(f'<div style="background-color: rgba(255, 255, 255, 220); padding: 8px; border: 1px solid black; border-radius: 3px;">{hover_text}</div>')
                self.hover_label.setPos(mouse_point.x(), mouse_point.y())
                self.hover_label.setVisible(True)
            else:
                self.hover_label.setVisible(False)
        else:
            self.hover_label.setVisible(False)

    def mouse_clicked(self, event):
        if event.button() == Qt.RightButton:
            self.zoom_fit()

    def next_candle(self):
        if self.current_idx < len(self.df) - 1:
            self.current_idx += 1
            self.update_chart()
        else:
            self.timer.stop()
            self.is_playing = False
            self.update_button_states()

    def play(self):
        self.is_playing = True
        self.update_button_states()
        self.timer.start(self.speed)

    def pause(self):
        self.is_playing = False
        self.update_button_states()
        self.timer.stop()

    def reset(self):
        self.timer.stop()
        self.is_playing = False
        self.update_button_states()
        self.current_idx = 0
        self.update_chart()

    def update_speed(self):
        self.speed = self.speed_slider.value()
        if self.timer.isActive():
            self.timer.start(self.speed)

    def jump_to_date(self):
        target_date = self.date_picker.date().toPyDate()
        for idx, row in self.df.iterrows():
            if row['datetime'].date() >= target_date:
                self.current_idx = idx
                self.update_chart()
                break

    def jump_to_candle(self):
        self.current_idx = self.candle_slider.value() - 1
        self.update_chart()

    def update_candle_count(self):
        self.visible_candle_count = self.candle_count_spin.value()
        self.update_chart()

    def zoom_fit(self):
        """Zoom to fit all visible candles"""
        start_idx = max(0, self.current_idx - self.visible_candle_count + 1)
        visible_df = self.df.iloc[start_idx:self.current_idx + 1]
        
        if len(visible_df) == 0:
            return
            
        x_min = visible_df['continuous_time'].iloc[0] - 15
        x_max = visible_df['continuous_time'].iloc[-1] + 15
        
        y_min = visible_df['low'].min()
        y_max = visible_df['high'].max()
        buffer = (y_max - y_min) * 0.05
        
        self.price_plot.setXRange(x_min, x_max, padding=0)
        self.price_plot.setYRange(y_min - buffer, y_max + buffer, padding=0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CandleReplay()
    window.show()
    sys.exit(app.exec_())