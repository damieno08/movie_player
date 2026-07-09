
# Imports
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor, QIcon
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QMainWindow, QVBoxLayout, QFrame, QMessageBox
import vlc
import time
import os

class Video_Player(QFrame):

    def __init__(self, video_path, parent=None):

        # Call QWidget constructor
        super().__init__(parent)
        # Set up vlc player
        self.player = vlc.MediaPlayer()
        self.player.set_hwnd(int(self.winId()))

        # Set up place to look for all videos
        self.__video_path = video_path

        # Set the parent if given
        if parent != None:
            self.setParent(parent)

    def play_video(self, video):

        # Create play path
        path = os.path.join(self.__video_path ,video)

        print(path)

        # Check if file exists
        if os.path.exists(path):

            # Add video to player
            self.player.set_mrl(path)

            # Start video
            self.player.play()

        # What happens if no video
        else:

            # Say video can't be played
            QMessageBox.critical(None, "Failure", "Your video could not be found!")

def main():
    app = QApplication([])

    main_window = QMainWindow()
    main_window.setWindowTitle("Main")
    main_window.resize(800, 600)

    window = Video_Player("")
    window.setMouseTracking(True)
    window.setStyleSheet("background-color: black")

    container = QWidget()
    layout = QVBoxLayout()

    button = QPushButton()
    button.setIcon(QIcon("pause_unpause.png"))
    def pause_movie():
        
        window.player.pause()

    button.clicked.connect(pause_movie)
    layout.addWidget(window)
    layout.addWidget(button)
    container.setLayout(layout)

    main_window.setCentralWidget(container)
    main_window.setMouseTracking(True)
    main_window.show()

    window.play_video("Obsession.2025.1080p.Bluray.10Bit.AAC7.1.x265-NeoNoir.mkv")


    app.exec()


main()