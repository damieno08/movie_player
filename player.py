
# Imports
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QObject
from PyQt6.QtGui import  QIcon
import PyQt6.QtWidgets as PQT 
import vlc
import os
        
class VLCEventBridge(QObject):
    time_changed = pyqtSignal(int)

class Video_Player(PQT.QFrame):

    def __init__(self, video_path, parent=None):

        # Call QWidget constructor
        super().__init__()

        # Make background black for video
        self.setStyleSheet("background-color: black")

        # Set up toolbar timer
        self.timer = QTimer()
        # Timer for toolbar to wait
        self.timer.setInterval(5000)

        # Set up vlc player
        self.player = vlc.MediaPlayer()
        self.player.set_hwnd(int(self.winId()))

        # Set up VLC to pyqt bridge
        self.bridge = VLCEventBridge()
        self.bridge.time_changed.connect(self.safe_update_slider)

        # Tell player to let Qt handle events
        self.player.video_set_key_input(False)
        self.player.video_set_key_input(False)

        # Make sure we can track mouse
        self.setMouseTracking(True)

        # Set up place to look for all videos
        self.__video_path = video_path

        # Set the parent if given
        if parent != None:
            self.setParent(parent)

        # set up the pop_up_bar
        self.pop_up_bar = PQT.QDockWidget()

        # Make transparent
        self.pop_up_bar.setWindowOpacity(0.5)

        # Set timer to remove pop-up
        self.timer.timeout.connect(self.pop_up_bar.close)

        # Create an empty widget and set it as the title bar
        empty_title_bar = PQT.QWidget()
        self.pop_up_bar.setTitleBarWidget(empty_title_bar)

        # make pop up as tool tip
        self.pop_up_bar.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)

        # Create progress bar and parent widget
        progress_widget = PQT.QWidget()
        progress_layout = PQT.QHBoxLayout()

        self.progress_bar = PQT.QSlider(Qt.Orientation.Horizontal)

        progress_layout.addWidget(self.progress_bar)
        progress_widget.setLayout(progress_layout)

        # Make a tool widget we can put into dock widget 
        tool_widget = PQT.QWidget()

        # Put all tools into layout
        tools = PQT.QHBoxLayout()
        
        # Add pause button
        pause_button = PQT.QPushButton()
        pause_button.setIcon(QIcon("pause_unpause.png"))
        # Pause/resume movie
        def pause_movie():
            self.player.pause()

            # Make sure pop-up stays open
        pause_button.clicked.connect(pause_movie)

        # Add fullscreen button
        full_screen = PQT.QPushButton()
        full_screen.setIcon(QIcon("full_screen.jpg"))

        # Make fullscreen seen everywhere
        global fullscreen_movie
        def fullscreen_movie():

            # Go fullscreen
            if not self.isFullScreen():

                # Store original place in window
                self.original_flags = self.windowFlags()

                # Make its own window
                self.setWindowFlags(Qt.WindowType.Window)
                self.showFullScreen()

            # Go back to normal
            else:
                self.setWindowFlags(self.original_flags)
                self.showNormal()

            # Find bottom left of the window
            global_bottom_left = self.mapToGlobal(self.rect().bottomLeft())
            
            # get bar height
            bar_height = int(self.height()*0.05)

            # Move into 
            self.pop_up_bar.setGeometry(
                global_bottom_left.x(), 
                global_bottom_left.y() - 100, 
                int(self.width()), 
                bar_height
            )

        # Add fullscreen to button
        full_screen.clicked.connect(fullscreen_movie)

        # Make volume bar
        volume_bar = PQT.QSlider(Qt.Orientation.Horizontal)

        # Make bar 0-100
        volume_bar.setMaximum(100)
        volume_bar.setMinimum(0)

        def change_volume():

            # Set volume to selected
            self.player.audio_set_volume(volume_bar.value())

        # Make volume change will press or move
        volume_bar.sliderMoved.connect(change_volume)
        volume_bar.sliderPressed.connect(change_volume)

        # Add all buttons to bar
        tools.addWidget(pause_button)
        tools.addWidget(full_screen)
        tools.addWidget(volume_bar)

        # Add layout of buttons to tool widget
        tool_widget.setLayout(tools)

        # Create a widget to store progress bar and tools
        pop_up = PQT.QWidget()

        # Make it stack tools than progress bar
        pop_up_layout = PQT.QVBoxLayout()
        pop_up_layout.addWidget(progress_widget)
        pop_up_layout.addWidget(tool_widget)


        # Add layout to widget
        pop_up.setLayout(pop_up_layout)

        # Add tool widget and make sure bar cant move
        self.pop_up_bar.setWidget(pop_up)
        self.pop_up_bar.setFeatures(PQT.QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)

    def mousePressEvent(self, a0):

        # Find bottom left of the window
        global_bottom_left = self.mapToGlobal(self.rect().bottomLeft())
        
        # get bar height
        bar_height = int(self.height()*0.05)

        # Move into 
        self.pop_up_bar.setGeometry(
            global_bottom_left.x(), 
            global_bottom_left.y() - 100, 
            int(self.width()), 
            bar_height
        )
        
        # Show and wait for closing
        self.pop_up_bar.show()
        self.timer.start()

    def mouseReleaseEvent(self, a0):
        # Pause the movie
        self.player.pause()

    def mouseDoubleClickEvent(self, a0):

        # Toggle fullscreen
        fullscreen_movie()

    def closeEvent(self, event):
        """ Runs automatically the exact moment the window is closed """
        # Kill VLC
        if hasattr(self, 'player') and self.player:
            self.player.stop()
            
            # Detach the event so it stops tracking
            try:
                self.player.event_manager().event_detach(vlc.EventType.MediaPlayerTimeChanged)
            except Exception:
                pass
                
            self.player.release()

        # Kill pop-up bar
        if hasattr(self, 'pop_up_bar') and self.pop_up_bar:
            self.pop_up_bar.close()

        # Continue to close normally
        event.accept()

    def play_video(self, video):

        # Create play path
        path = os.path.join(self.__video_path ,video)

        # Check if file exists
        if os.path.exists(path):

            # Add video to player
            self.player.set_mrl(path)

            # Start video
            self.player.play()
            self.player.video_set_key_input(False)
            self.player.video_set_mouse_input(False)
            
            # make progress bar update with movie
            self.progress_bar.setRange(0, self.player.get_length())
            event_manager = self.player.event_manager()
            event_manager.event_attach(
            vlc.EventType.MediaPlayerTimeChanged, 
            self.vlc_time_callback
        )
            # Connect movement to time
            self.progress_bar.sliderMoved.connect(self.seek_video)
            self.progress_bar.sliderPressed.connect(lambda: self.seek_video(self.progress_bar.value()))

        # What happens if no video
        else:

            # Say video can't be played
            PQT.QMessageBox.critical(None, "Failure", "Your video could not be found!")

    def vlc_time_callback(self, event):
        """ This runs on VLC's background thread. DO NOT touch the UI here. """
        current_time_ms = event.u.new_time
        
        # Safely forward the time data over to the PyQt Main Thread
        self.bridge.time_changed.emit(current_time_ms)

    def safe_update_slider(self, current_time_ms):
        """ This runs safely on the PyQt Main Thread. """
        # Dynamically keep updating the max duration in case it wasn't ready at launch
        video_length = self.player.get_length()
        if video_length > 0 and self.progress_bar.maximum() != video_length:
            self.progress_bar.setMaximum(video_length)

        # Block signals so updating the progress bar doesn't trick your app into thinking the user dragged it
        self.progress_bar.blockSignals(True)
        self.progress_bar.setValue(current_time_ms)
        self.progress_bar.blockSignals(False)

    def seek_video(self, position_ms):
        self.player.set_time(position_ms)

def main():
    app = PQT.QApplication([])

    main_window = PQT.QMainWindow()
    main_window.setWindowTitle("Main")
    main_window.resize(800, 600)

    container = PQT.QWidget()
    layout = PQT.QVBoxLayout()

    window = Video_Player("")

    label = PQT.QLabel()
    label.setText("Working")

    layout.addWidget(window)
    layout.addWidget(label)

    container.setLayout(layout)

    main_window.setCentralWidget(container)
    main_window.setMouseTracking(True)
    main_window.show()

    window.play_video("Obsession.2025.1080p.Bluray.10Bit.AAC7.1.x265-NeoNoir.mkv")


    app.exec()


main()