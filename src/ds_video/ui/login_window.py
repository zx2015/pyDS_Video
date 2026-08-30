"""Login window: collects DSM connection info and performs login off the UI thread."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ds_video.api import AuthError, FileStationClient
from ds_video.config import DsmConnectionSettings, load_settings, save_settings
from ds_video.ui.theme import make_app_icon


class _LoginWorker(QThread):
    """Runs the (blocking) DSM login call off the Qt UI thread."""

    succeeded = pyqtSignal(object)  # FileStationClient
    failed = pyqtSignal(str)

    def __init__(self, settings: DsmConnectionSettings) -> None:
        super().__init__()
        self._settings = settings

    def run(self) -> None:
        try:
            client = FileStationClient(
                ip_address=self._settings.host,
                port=self._settings.port,
                username=self._settings.username,
                password=self._settings.password,
                secure=self._settings.secure,
            )
        except AuthError as exc:
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - last line of defense: an
            # exception escaping a QThread can abort the whole PyQt process
            # instead of just failing this login attempt, so nothing may
            # propagate out of run().
            self.failed.emit(f"未预期的错误：{exc}")
            return
        self.succeeded.emit(client)


class LoginWindow(QWidget):
    """Prompts for DSM host/credentials and emits ``login_succeeded`` once connected."""

    login_succeeded = pyqtSignal(object, object)  # (FileStationClient, DsmConnectionSettings)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ds_video - 登录 DSM")
        self._worker: _LoginWorker | None = None
        self._auto_connecting = False

        # -- header: logo mark + title/subtitle ---------------------------
        logo_label = QLabel()
        logo_label.setPixmap(make_app_icon(56).pixmap(56, 56))
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel("DS Video")
        title_label.setProperty("variant", "title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle_label = QLabel("登录群晖 DSM，浏览并播放 File Station 中的视频")
        subtitle_label.setProperty("variant", "subtitle")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setWordWrap(True)

        # -- card: connection form -----------------------------------------
        card = QFrame()
        card.setProperty("variant", "card")

        self._host_edit = QLineEdit()
        self._host_edit.setPlaceholderText("例如 192.168.1.10")
        self._port_edit = QLineEdit("5000")
        self._port_edit.setPlaceholderText("HTTP 默认 5000，HTTPS 默认 5001")
        self._username_edit = QLineEdit()
        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._secure_checkbox = QCheckBox("使用 HTTPS（端口通常为 5001，而非 5000）")
        self._save_checkbox = QCheckBox("记住登录信息（加密保存在本地）")
        self._save_checkbox.setChecked(True)

        self._connect_button = QPushButton("连接")
        self._connect_button.setProperty("variant", "primary")
        self._connect_button.setMinimumHeight(36)
        self._connect_button.clicked.connect(self._on_connect_clicked)
        self._connect_button.setDefault(True)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setVerticalSpacing(12)
        form.addRow("DSM 地址", self._host_edit)
        form.addRow("端口", self._port_edit)
        form.addRow("用户名", self._username_edit)
        form.addRow("密码", self._password_edit)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)
        card_layout.addLayout(form)
        card_layout.addWidget(self._secure_checkbox)
        card_layout.addWidget(self._save_checkbox)
        card_layout.addSpacing(4)
        card_layout.addWidget(self._connect_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 40, 48, 40)
        layout.setSpacing(6)
        layout.addWidget(logo_label)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addSpacing(20)
        layout.addWidget(card)

        self.setMinimumWidth(440)

        self._saved_settings: DsmConnectionSettings | None = None
        self._prefill_saved_settings()
        self._maybe_auto_connect()

    def _prefill_saved_settings(self) -> None:
        saved = load_settings()
        if saved is None:
            return
        self._saved_settings = saved
        self._host_edit.setText(saved.host)
        self._port_edit.setText(saved.port)
        self._username_edit.setText(saved.username)
        self._password_edit.setText(saved.password)
        self._secure_checkbox.setChecked(saved.secure)

    def _maybe_auto_connect(self) -> None:
        """On startup, silently retry the last successful connection instead
        of making the user click "连接" again. The form stays visible (and
        prefilled) underneath so that if the auto-connect fails, the user
        immediately sees it and can edit/retry manually -- no separate mode
        or extra window is needed for that fallback.
        """
        if self._saved_settings is None:
            return
        self._auto_connecting = True
        self._connect_button.setEnabled(False)
        self._connect_button.setText("正在使用上次的登录信息自动连接...")
        self._start_login(self._saved_settings)

    def _on_connect_clicked(self) -> None:
        settings = DsmConnectionSettings(
            host=self._host_edit.text().strip(),
            port=self._port_edit.text().strip(),
            username=self._username_edit.text().strip(),
            password=self._password_edit.text(),
            secure=self._secure_checkbox.isChecked(),
        )
        if not all([settings.host, settings.port, settings.username, settings.password]):
            QMessageBox.warning(self, "信息不完整", "请填写 DSM 地址、端口、用户名和密码。")
            return

        self._connect_button.setEnabled(False)
        self._connect_button.setText("正在连接...")
        self._start_login(settings)

    def _start_login(self, settings: DsmConnectionSettings) -> None:
        self._worker = _LoginWorker(settings)
        self._worker.succeeded.connect(lambda client: self._on_login_succeeded(client, settings))
        self._worker.failed.connect(self._on_login_failed)
        self._worker.start()

    def _on_login_succeeded(self, client: FileStationClient, settings: DsmConnectionSettings) -> None:
        if self._save_checkbox.isChecked():
            save_settings(settings)
        self._connect_button.setEnabled(True)
        self._connect_button.setText("连接")
        self.login_succeeded.emit(client, settings)

    def _on_login_failed(self, message: str) -> None:
        self._connect_button.setEnabled(True)
        self._connect_button.setText("连接")
        if self._auto_connecting:
            # Auto-connect used the last saved settings without the user
            # asking for it, so don't interrupt with a modal dialog -- just
            # leave the (already prefilled) form visible and ready to edit,
            # with the failure reason shown inline so they know why.
            self._auto_connecting = False
            QMessageBox.warning(
                self,
                "自动连接失败",
                f"使用上次保存的登录信息自动连接失败：{message}\n请检查并更新下方的连接信息后重试。",
            )
            return
        QMessageBox.critical(self, "登录失败", message)
