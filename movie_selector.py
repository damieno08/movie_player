import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import QTimer, Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap
import PyQt6.QtWidgets as PQT
from collections import defaultdict

from player import Video_Player, MainWindow
# Ensure player.py is in the same directory or comment this out if testing


@dataclass(eq=False)
class Movie:
    """Plain data object describing a single movie.

    Created exactly once per movie when the library is scanned. Every
    widget that needs to show this movie holds a reference to this same
    object instead of re-reading config.txt or re-decoding the cover art.
    (eq=False keeps identity-based equality/hashing, which is what we want
    since each Movie instance is unique -- this lets Movie be used as a
    dict key in movie_list's button caches.)
    """
    title: str
    cover: str
    runtime: int
    description: str
    genres: list
    cast: list
    path: str
    icon: Optional[QIcon] = field(default=None, repr=False)

    @property
    def title_lower(self):
        return self.title.lower()

    @classmethod
    def from_config(cls, data, movie_dir):
        movie = cls(
            title=data["title"],
            cover=os.path.join(movie_dir, data["cover"]),
            runtime=data["runtime"],
            description=data["description"],
            genres=data["genres"],
            cast=data["cast"],
            path=os.path.join(movie_dir, data["filename"]),
        )
        movie.load_icon()
        return movie

    def load_icon(self):
        """Decode + scale the cover art once and cache it on the Movie
        itself, so every button that shows this movie reuses the same
        QIcon instead of re-decoding the image from disk."""
        if os.path.exists(self.cover):
            pixmap = QPixmap(self.cover).scaled(
                150,
                220,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.icon = QIcon(pixmap)
        else:
            self.icon = None


class Movie_button(PQT.QPushButton):
    """Thin display widget wrapping a Movie.

    Holds no movie data of its own -- everything (including the icon)
    comes off the shared Movie object, so constructing one is cheap (no
    disk I/O, no image decoding/scaling).

    A movie that belongs to N genres needs N simultaneously-visible
    button instances (a QWidget can only have one parent at a time), plus
    one more for the search grid. movie_list caches and reuses all of
    these across rebuilds instead of recreating them -- the only thing
    that's ever duplicated is this lightweight widget, never the
    underlying movie data or the decoded cover art.
    """

    def __init__(self, movie: Movie):
        super().__init__()
        self.movie = movie

        self.setMinimumSize(120, 180)
        self.setSizePolicy(
            PQT.QSizePolicy.Policy.Expanding,
            PQT.QSizePolicy.Policy.Expanding,
        )

        if movie.icon is not None:
            self.setIcon(movie.icon)
            self.setIconSize(QSize(150, 220))
            self._update_icon_size()
        else:
            self.setText(movie.title)

        self.clicked.connect(self.open_player)

    def _update_icon_size(self):
        button_size = self.size()
        padding = 6
        icon_width = max(button_size.width() - padding, 1)
        icon_height = max(button_size.height() - padding, 1)
        self.setIconSize(QSize(icon_width, icon_height))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_icon_size()

    def open_player(self):
        player_screen = Play_Screen(self.movie)
        movie_list.main_screen.addWidget(player_screen)
        movie_list.main_screen.setCurrentWidget(player_screen)


class Search_Screen(PQT.QWidget):
    """Search UI. Does not own any movies or buttons -- it borrows both
    from the central movie_list (library) passed in."""

    def __init__(self, library: "movie_list"):
        super().__init__()
        self.library = library
        self.previous_text = ""
        self.previous_results: List[Movie] = []

        layout = PQT.QVBoxLayout(self)

        back = PQT.QPushButton("Back")
        back.clicked.connect(self.go_back)
        layout.addWidget(back)

        self.search = PQT.QLineEdit()
        self.search.setPlaceholderText("Search movies...")
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.search_movies)
        self.search.textChanged.connect(lambda: self.search_timer.start(300))

        layout.addWidget(self.search)

        self.results_widget = PQT.QWidget()
        self.results_layout = PQT.QGridLayout(self.results_widget)

        scroll = PQT.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.results_widget)
        layout.addWidget(scroll)

    def search_movies(self):
        text = self.search.text().strip().lower()
        movies = self.library.movies

        if not text:
            filtered = movies
        elif text.startswith(self.previous_text):
            filtered = [m for m in self.previous_results if text in m.title_lower]
        else:
            filtered = [m for m in movies if text in m.title_lower]

        self.previous_text = text
        self.previous_results = filtered

        # Hide + detach every button currently showing in this grid.
        # These buttons live only here (the search pool never overlaps
        # with the genre-row pool), so this is all the cleanup needed --
        # no cross-screen reparenting required.
        for button in self.library.search_buttons.values():
            button.hide()
            self.results_layout.removeWidget(button)

        columns = 5
        for i, movie in enumerate(filtered):
            button = self.library.get_search_button(movie)
            button.setFixedSize(150, 220)
            self.results_layout.addWidget(button, i // columns, i % columns)
            button.show()

    def go_back(self):
        # Just switch screens -- the main screen's genre-row buttons were
        # never touched, so there's nothing to rebuild.
        movie_list.main_screen.setCurrentIndex(0)


class Play_Screen(PQT.QWidget):
    def __init__(self, movie: Movie):
        super().__init__()
        self.movie = movie
        self.player = Video_Player(movie.path)
        self.descript = PQT.QWidget()

        layout = PQT.QVBoxLayout()
        layout.addWidget(self.player, stretch=6)
        layout.addWidget(self.descript, stretch=4)

        self.setLayout(layout)

        def center_label(text):
            label = PQT.QLabel(text)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return label

        descript_box = PQT.QVBoxLayout()
        descript_data = PQT.QHBoxLayout()

        movie_info_widget = PQT.QWidget()
        description = center_label(f"Description: {movie.description}")
        description.setWordWrap(True)
        genre_text = "Movie Genres: "
        for genre in movie.genres:
            genre_text += f"{genre} "
        genres = center_label(genre_text)
        genres.setWordWrap(True)

        descript_data.addWidget(center_label(f"Title: {movie.title}"), stretch=1)
        descript_data.addWidget(description, stretch=1)
        descript_data.addWidget(genres, stretch=1)

        cast_text = "Cast: "
        for cast in movie.cast:
            if cast_text == "Cast: ":
                cast_text += f"{cast} "
            else:
                cast_text += f",{cast} "
        Cast = center_label(cast_text)
        Cast.setWordWrap(True)
        descript_data.addWidget(Cast, stretch=1)
        descript_data.addWidget(center_label(f"{movie.runtime} minutes"), stretch=1)

        movie_info_widget.setLayout(descript_data)
        descript_box.addWidget(movie_info_widget)

        return_button = PQT.QPushButton()
        return_button.setText("Return to list")

        def return_to_list():
            self.player.player.stop()
            self.player.close()
            movie_list.main_screen.removeWidget(self)

        return_button.clicked.connect(return_to_list)
        descript_box.addWidget(return_button)
        self.descript.setLayout(descript_box)

        self.player.play_video()
        self.setFixedWidth(self.window().width())
        self.setMinimumHeight(self.window().height())

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        self.setFixedWidth(self.window().width())


class movie_list(PQT.QWidget):
    """Central library: owns the ONE authoritative list of movies, plus
    two lazily-populated button caches (per-genre-appearance and
    per-search-grid). Every screen reads from these instead of building
    its own copies of movie data or re-decoding cover art."""

    main_screen = None

    def __init__(self):
        super().__init__()
        self.movies: List[Movie] = []
        # One button per (movie, genre) appearance, so a movie can show up
        # in every genre row it belongs to at once.
        self.genre_buttons: Dict[Tuple[Movie, str], Movie_button] = {}
        # One button per movie, dedicated to the search grid.
        self.search_buttons: Dict[Movie, Movie_button] = {}
        self.search_screen: Optional[Search_Screen] = None

        movie_list.main_screen = PQT.QStackedWidget()
        movie_list.main_screen.addWidget(self)

        self.main_layout = PQT.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        search_button = PQT.QPushButton("Search")
        search_button.clicked.connect(self.open_search)

        filter_widget = PQT.QWidget()
        filter_layout = PQT.QHBoxLayout()
        filter_layout.addWidget(search_button, stretch=1)
        filter_widget.setLayout(filter_layout)

        self.main_layout.addWidget(filter_widget)

        self.scroll = PQT.QScrollArea()
        self.scroll.setMinimumHeight(self.window().height())
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll.setWidgetResizable(True)
        self.main_layout.addWidget(self.scroll, stretch=8)

        self.scroll_content = PQT.QWidget()
        self.scroll_layout = PQT.QVBoxLayout(self.scroll_content)
        self.scroll.setWidget(self.scroll_content)

    def open_search(self):
        if self.search_screen is None:
            self.search_screen = Search_Screen(self)
            movie_list.main_screen.addWidget(self.search_screen)
        self.search_screen.search_movies()
        movie_list.main_screen.setCurrentWidget(self.search_screen)

    def get_genre_button(self, movie: Movie, genre: str) -> Movie_button:
        """Return the (cached) button for this movie's appearance in this
        specific genre row, creating it the first time it's needed."""
        key = (movie, genre)
        button = self.genre_buttons.get(key)
        if button is None:
            button = Movie_button(movie)
            self.genre_buttons[key] = button
        return button

    def get_search_button(self, movie: Movie) -> Movie_button:
        """Return the (cached) button for this movie in the search grid,
        creating it the first time it's needed."""
        button = self.search_buttons.get(movie)
        if button is None:
            button = Movie_button(movie)
            self.search_buttons[movie] = button
        return button

    def get_movies(self):
        # Prevent crashes if E:\Movies doesn't exist on the testing machine
        movie_dir = r"E:\Movies"
        if not os.path.exists(movie_dir):
            print(f"Directory {movie_dir} not found.")
            return

        folders = [
            os.path.join(movie_dir, name) for name in os.listdir(movie_dir)
            if os.path.isdir(os.path.join(movie_dir, name))
        ]
        folders.sort()

        for movie_path in folders:
            config_path = os.path.join(movie_path, "config.txt")
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    movie = Movie.from_config(data, movie_path)
                    self.movies.append(movie)
                except Exception as e:
                    print(f"Error loading {config_path}: {e}")

        self.build_movie_sections()

    def group_by_genre(self, movies=None):
        movies = self.movies if movies is None else movies
        genres = defaultdict(list)
        for movie in movies:
            for genre in movie.genres:
                genres[genre].append(movie)
        return genres

    def build_movie_sections(self, movies=None):
        # The genre-row containers (labels, scroll areas) get deleted and
        # rebuilt below. Detach every cached genre button first so it
        # survives that teardown instead of being deleted along with its
        # old container.
        for button in self.genre_buttons.values():
            button.hide()
            button.setParent(None)

        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        movies = self.movies if movies is None else movies
        grouped = self.group_by_genre(movies)

        for genre, genre_movies in grouped.items():
            title = PQT.QLabel(genre)
            title.setStyleSheet("font-size: 20px; font-weight: bold;")
            self.scroll_layout.addWidget(title)

            genre_scroll = PQT.QScrollArea()
            genre_scroll.setMinimumHeight(int(self.window().height() / 2))
            genre_scroll.setWidgetResizable(True)
            genre_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            genre_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

            movie_container = PQT.QWidget()
            movie_layout = PQT.QHBoxLayout(movie_container)
            movie_layout.setContentsMargins(0, 0, 0, 0)

            for movie in genre_movies:
                button = self.get_genre_button(movie, genre)
                button.setFixedSize(150, 220)
                movie_layout.addWidget(button)
                button.show()

            genre_scroll.setWidget(movie_container)
            self.scroll_layout.addWidget(genre_scroll)


def main():
    app = PQT.QApplication([])

    lister = movie_list()
    lister.get_movies()

    window = MainWindow()
    window.setCentralWidget(movie_list.main_screen)
    window.setMouseTracking(True)
    window.resize(800, 300)
    window.show()

    app.exec()


if __name__ == "__main__":
    main()