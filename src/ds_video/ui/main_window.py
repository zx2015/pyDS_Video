"""Main window: a directory tree of shared folders and a file list.

Per docs/requirements.md section 2: a simple tree navigation + file list,
no poster wall / metadata browsing. By default only the ``video``/``电影``
shared folder is relevant to this app, so the tree skips the full shared-
folder list and shows that folder's subdirectories directly as its roots;
navigation below that is by plain filesystem path.
"""

from __future__ import annotations

from contextlib import contextmanager

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStyle,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ds_video.api import ApiError, FileEntry, FileStationClient, SessionExpiredError
from ds_video.ui.sizing import apply_preferred_size

# Shared folder names treated as "the video library" — only these (and their
# subfolders) are shown by default; other shared folders (photo, docs, etc.)
# are not relevant to this app and are hidden to keep the tree focused.
_VIDEO_SHARE_NAMES = {"video", "电影"}

# Extensions treated as playable video files when listing a folder's
# contents; anything else (images, subtitles, docs, ...) is filtered out so
# the file list only ever shows what VLC can actually play.
_VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v",
    ".mpg", ".mpeg", ".ts", ".m2ts", ".3gp", ".rmvb", ".rm", ".vob",
}


def _is_video_file(name: str) -> bool:
    dot = name.rfind(".")
    return dot != -1 and name[dot:].lower() in _VIDEO_EXTENSIONS


class MainWindow(QMainWindow):
    """Browses shared folders/files and lets the user pick a video to play."""

    file_activated = pyqtSignal(str, str)  # (file_path, display_name)

    _PATH_ROLE = Qt.ItemDataRole.UserRole

    def __init__(self, client: FileStationClient) -> None:
        super().__init__()
        self.setWindowTitle("ds_video - File Station")
        self._client = client
        self._current_folder_path: str | None = None
        self._loading = False

        style = QApplication.instance().style() if QApplication.instance() else self.style()
        self._folder_icon = style.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        self._file_icon = style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay)

        self._build_toolbar(style)

        section_label = QLabel("视频目录")
        section_label.setProperty("variant", "section")

        self._share_fallback_hint = QLabel(
            "未找到名为 video/电影 的共享文件夹，已显示全部共享文件夹。"
        )
        self._share_fallback_hint.setProperty("variant", "hint")
        self._share_fallback_hint.setWordWrap(True)
        self._share_fallback_hint.hide()

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setIconSize(self._tree.iconSize())
        self._tree.itemExpanded.connect(self._on_tree_item_expanded)
        self._tree.itemClicked.connect(self._on_tree_item_clicked)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        left_layout.addWidget(section_label)
        left_layout.addWidget(self._share_fallback_hint)
        left_layout.addWidget(self._tree)

        self._file_section_label = QLabel("文件")
        self._file_section_label.setProperty("variant", "section")

        self._file_list = QListWidget()
        self._file_list.itemDoubleClicked.connect(self._on_file_double_clicked)

        self._empty_hint = QLabel("请选择左侧目录以查看视频文件，双击即可播放。")
        self._empty_hint.setProperty("variant", "hint")
        self._empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_hint.setWordWrap(True)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)
        right_layout.addWidget(self._file_section_label)
        right_layout.addWidget(self._file_list, 1)
        right_layout.addWidget(self._empty_hint)
        self._file_list.hide()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(splitter)
        self.setCentralWidget(central)

        self._status_hint = self.statusBar()
        self._status_hint.showMessage("已连接 DSM，正在加载视频目录…")

        apply_preferred_size(self, 1280, 800)

        self._load_shares()

    # -- chrome ------------------------------------------------------------

    def _build_toolbar(self, style) -> None:
        toolbar = QToolBar("主工具栏", self)
        toolbar.setMovable(False)
        toolbar.setIconSize(toolbar.iconSize())
        self.addToolBar(toolbar)

        refresh_button = QPushButton("刷新")
        refresh_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        refresh_button.clicked.connect(self._on_refresh_clicked)
        toolbar.addWidget(refresh_button)

    def _on_refresh_clicked(self) -> None:
        self._tree.clear()
        self._file_list.clear()
        self._file_list.hide()
        self._empty_hint.setText("请选择左侧目录以查看视频文件，双击即可播放。")
        self._empty_hint.show()
        self._share_fallback_hint.hide()
        self._current_folder_path = None
        self._status_hint.showMessage("正在刷新视频目录…")
        self._load_shares()

    # -- error handling ----------------------------------------------------

    def _handle_load_error(self, exc: Exception, message: str) -> None:
        """Show one dialog for both "API returned an error" and "the DSM
        session expired" cases, since the latter needs a clearer next step
        (re-login) rather than just "try again"."""
        if isinstance(exc, SessionExpiredError):
            QMessageBox.critical(
                self,
                "会话已过期",
                f"{message}：DSM 登录会话已过期或失效，请重新启动应用并登录。",
            )
        else:
            QMessageBox.critical(self, "加载失败", f"{message}：{exc}")

    def _make_tree_item(self, entry: FileEntry) -> QTreeWidgetItem:
        """Build a tree node for a folder entry (shared by the top-level
        share loader and the on-expand subfolder loader)."""
        item = QTreeWidgetItem([entry.name])
        item.setIcon(0, self._folder_icon)
        item.setData(0, self._PATH_ROLE, entry.path)
        item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
        return item

    @contextmanager
    def _busy(self):
        """Show a wait cursor for the duration of a blocking DSM call.

        Guarded by ``_loading`` so a re-entrant call (e.g. triggered from
        inside a Qt callback while another load is still on the stack)
        never pushes a second override cursor without a matching pop --
        ``QApplication.set/restoreOverrideCursor`` is stack-based, so
        mismatched calls would leave the wait cursor stuck.
        """
        if self._loading:
            yield
            return
        self._loading = True
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            yield
        finally:
            QApplication.restoreOverrideCursor()
            self._loading = False

    # -- population ------------------------------------------------------

    def _load_shares(self) -> None:
        self._status_hint.showMessage("正在加载视频目录…")
        with self._busy():
            try:
                shares = self._client.list_shares()
            except (ApiError, SessionExpiredError) as exc:
                self._handle_load_error(exc, "无法获取共享文件夹列表")
                self._status_hint.showMessage("加载视频目录失败", 5000)
                return

            video_shares = [share for share in shares if share.name.strip().lower() in _VIDEO_SHARE_NAMES]
            if not video_shares:
                self._share_fallback_hint.show()
                video_shares = shares
            else:
                self._share_fallback_hint.hide()

            loaded = 0
            failures: list[str] = []
            for share in video_shares:
                try:
                    entries = self._client.list_folder(share.path)
                except SessionExpiredError as exc:
                    # A session-expired error means every subsequent share
                    # load will fail identically -- report it immediately
                    # (with the clearer re-login message) instead of piling
                    # up one dialog per remaining share.
                    self._handle_load_error(exc, "无法获取目录内容")
                    return
                except ApiError as exc:
                    failures.append(f"{share.name}：{exc}")
                    continue
                for entry in entries:
                    if not entry.is_folder:
                        continue
                    self._tree.addTopLevelItem(self._make_tree_item(entry))
                    loaded += 1
            if failures:
                QMessageBox.critical(
                    self,
                    "加载失败",
                    "以下目录内容获取失败：\n" + "\n".join(failures),
                )
            if loaded:
                self._status_hint.showMessage(f"已加载 {loaded} 个目录", 4000)

    def _on_tree_item_expanded(self, item: QTreeWidgetItem) -> None:
        if item.childCount() > 0:
            return  # already populated
        path = item.data(0, self._PATH_ROLE)
        self._populate_subfolders(item, path)

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        path = item.data(0, self._PATH_ROLE)
        self._load_file_list(path)

    def _populate_subfolders(self, parent_item: QTreeWidgetItem, path: str) -> None:
        with self._busy():
            try:
                entries = self._client.list_folder(path)
            except (ApiError, SessionExpiredError) as exc:
                self._handle_load_error(exc, "无法获取目录内容")
                return
            for entry in entries:
                if not entry.is_folder:
                    continue
                parent_item.addChild(self._make_tree_item(entry))

    def _load_file_list(self, path: str) -> None:
        self._current_folder_path = path
        self._file_list.clear()
        self._status_hint.showMessage(f"正在加载 {path} …")
        with self._busy():
            try:
                entries = self._client.list_folder(path)
            except (ApiError, SessionExpiredError) as exc:
                self._handle_load_error(exc, "无法获取文件列表")
                self._status_hint.showMessage("加载文件列表失败", 5000)
                return

            video_count = 0
            for entry in entries:
                # Only list playable video files: folders are shown in the
                # tree, and non-video files (images, subtitles, docs, ...)
                # aren't something VlcLauncher can do anything useful with.
                if entry.is_folder or not _is_video_file(entry.name):
                    continue
                list_item = QListWidgetItem(entry.name)
                list_item.setIcon(self._file_icon)
                list_item.setData(Qt.ItemDataRole.UserRole, entry)
                self._file_list.addItem(list_item)
                video_count += 1

            self._file_section_label.setText(f"文件（{video_count}）")
            if video_count == 0:
                self._file_list.hide()
                self._empty_hint.setText("该目录下没有找到视频文件。")
                self._empty_hint.show()
            else:
                self._empty_hint.hide()
                self._file_list.show()
            self._status_hint.showMessage(f"{path}：共 {video_count} 个视频文件", 4000)

    def _on_file_double_clicked(self, item: QListWidgetItem) -> None:
        entry: FileEntry = item.data(Qt.ItemDataRole.UserRole)
        self.file_activated.emit(entry.path, entry.name)
