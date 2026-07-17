
# Imports
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QObject
from PyQt6.QtGui import  QIcon
import PyQt6.QtWidgets as PQT 
import vlc
import os


class MainWindow(PQT.QMainWindow):
    def moveEvent(self, event):
        super().moveEvent(event)

        # Close any dock widgets when moving window
        for dock in self.findChildren(PQT.QDockWidget):
            dock.close()

class VLCEventBridge(QObject):
    """
    Class to allow main gui to interact with VLC
    """
    time_changed = pyqtSignal(int)

class Video_Player(PQT.QFrame):

    """
    Class capable of watching movies with expected operations
    """

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
        self.pop_up_bar = PQT.QDockWidget(self)

        # Make it have white background
        self.pop_up_bar.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 150);
                border-radius: 10px;
            }
        """)

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
        pause_button.setIcon(QIcon("icons/pause_unpause.png"))
        # Pause/resume movie
        def pause_movie():
            self.player.pause()

            # Make sure popup stays up
            self.position_popup()

        pause_button.clicked.connect(pause_movie)

        # Add fullscreen button
        full_screen = PQT.QPushButton()
        full_screen.setIcon(QIcon("icons/full_screen.jpg"))

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

            self.position_popup()

        # Add fullscreen to button
        full_screen.clicked.connect(fullscreen_movie)

        # Create container for volume bar and icon
        volume_container = PQT.QWidget()
        volume_layout = PQT.QHBoxLayout()

        # Make volume bar
        self.volume_bar = PQT.QSlider(Qt.Orientation.Horizontal)

        # Change volume bar to be small
        self.volume_bar.setMaximumWidth(int(self.width()/2))

        # Start at 100% volume
        self.volume_bar.setValue(100)

        # Make bar 0-100
        self.volume_bar.setMaximum(100)
        self.volume_bar.setMinimum(0)

        # Add mute/unmute button
        self.sound_button = PQT.QPushButton()
        self.sound_button.setIcon(QIcon("icons/unmute.png"))
        self.unmuted = True

        def change_sound():
            
            # Change icon and volume based on mute or unmute
            if self.unmuted:
                self.sound_button.setIcon(QIcon("icons/mute.png"))
                self.volume_bar.setValue(0)
                self.player.audio_set_volume(0)
            else:
                self.sound_button.setIcon(QIcon("icons/unmute.png"))
                self.volume_bar.setValue(100)
                self.player.audio_set_volume(100)

            # Toggle mute
            self.unmuted = not self.unmuted

            # Make sure popup stays open
            self.position_popup()

        # Make button alter sound
        self.sound_button.clicked.connect(change_sound)

        # Add mute/unmute
        volume_layout.addWidget(self.sound_button)

        # Add volume bar
        volume_layout.addWidget(self.volume_bar)

        # Add layout to container
        volume_container.setLayout(volume_layout)

        def change_volume():

            # Get volume
            volume = self.volume_bar.value()

            # Set volume to selected
            self.player.audio_set_volume(volume)

            # Make sure icon matches volume level
            if volume > 0:
                
                self.sound_button.setIcon(QIcon("icons/unmute.png"))
                self.unmuted = True
            else:
                self.sound_button.setIcon(QIcon("icons/mute.png"))
                self.unmuted = False

            # Change muted and unmuted
            self.unmuted = not self.unmuted

            # Make sure popup stays up
            self.position_popup()


        # Make volume change will press or move
        self.volume_bar.sliderMoved.connect(change_volume)
        self.volume_bar.sliderPressed.connect(change_volume)

        # Create fast forward button
        fast_forward = PQT.QPushButton()
        fast_forward.setIcon(QIcon("icons/fast_forward.png"))
        def skip_forward():

            try:
                # Skip forward 10 seconds
                self.player.set_time(self.player.get_time()+10000)
            except:
                pass
            # Make sure popup stays up
            self.position_popup()

        fast_forward.clicked.connect(skip_forward)

        # Create rewind button
        rewind = PQT.QPushButton()
        rewind.setIcon(QIcon("icons/rewind.png"))
        def skip_back():
            
            try:
                # Skip back 10 seconds
                self.player.set_time(self.player.get_time()-10000)
            except:
                pass
            
            # Make sure popup stays up
            self.position_popup()

        rewind.clicked.connect(skip_back)

        # Add all buttons to bar
        tools.addWidget(rewind)
        tools.addWidget(pause_button)
        tools.addWidget(fast_forward)
        tools.addWidget(volume_container)
        tools.addWidget(full_screen)

        # Add layout of buttons to tool widget
        tool_widget.setLayout(tools)

        # Create a widget to store progress bar and tools
        pop_up = PQT.QWidget()

        # Make it stack tools than progress bar
        pop_up_layout = PQT.QVBoxLayout()
        pop_up_layout.addWidget(progress_widget)
        pop_up_layout.addWidget(tool_widget)

        # Give pop-up white background
        pop_up.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 150);
                border-radius: 10px;

            }
        """)

        # Add layout to widget
        pop_up.setLayout(pop_up_layout)

        # Add tool widget and make sure bar cant move
        self.pop_up_bar.setWidget(pop_up)
        self.pop_up_bar.setFeatures(PQT.QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)

    def position_popup(self):
        """
        Function will create the popup with tools and progress bar
        """

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
        self.pop_up_bar.show()
        

    def resizeEvent(self, a0):
        """ 
        Handle resizing
        """
        super().resizeEvent(a0)

        # Make pop-up fit screen
        self.position_popup()

    def mousePressEvent(self, a0):

        """
        Handle pop-up on click
        """

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

    def mouseMoveEvent(self, a0):
        """
        Show pop-up whenever moving over screen
        """

        # Show on move
        self.position_popup()
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
        self.pop_up_bar.close()

        # Continue to close normally
        event.accept()

    def play_video(self):

        """
        Given a video, play it with full functionallity
        """

        # Check if file exists
        if os.path.exists(self.__video_path):

            # Add video to player
            self.player.set_mrl(self.__video_path)

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
            print(self.__video_path)
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

        """
        Given a time, move to that time in the video.
        
        """

        # Change time and make sure popup stays open a bit more
        self.position_popup()
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

    #window.play_video("Obsession.2025.1080p.Bluray.10Bit.AAC7.1.x265-NeoNoir.mkv")


    app.exec()

if __name__ == "__main__": 
    main()