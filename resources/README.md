# resources

静态资源目录：图标、样式表（QSS）等 UI 资源文件。

## Linux 桌面快捷方式

- `ds-video.desktop`：应用启动器模板。使用前需要：
  1. 编辑 `Exec=` 行，将 `/path/to/ds_video` 替换为本机项目的实际绝对路径
     （例如 `/home/<你的用户名>/git/ds_video/.venv/bin/ds-video`）。
  2. 将图标安装到用户级图标主题目录，使 `Icon=ds-video` 能被解析：
     ```bash
     mkdir -p ~/.local/share/icons/hicolor/256x256/apps
     cp resources/ds_video.png ~/.local/share/icons/hicolor/256x256/apps/ds-video.png
     gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor
     ```
  3. 安装桌面入口：
     ```bash
     cp resources/ds-video.desktop ~/.local/share/applications/ds-video.desktop
     chmod +x ~/.local/share/applications/ds-video.desktop
     update-desktop-database ~/.local/share/applications
     ```
  4. 之后即可在应用菜单/任务栏中看到「DS Video」及其自定义图标（应用本身也通过
     `QApplication.setDesktopFileName("ds-video")` 与该 `.desktop` 文件关联，详见
     `AGENTS.md` 中的说明）。

- `ds_video.png`：程序图标（由 `ui/theme.py` 中的 `make_app_icon()` 生成的 128×128 图标导出而来）。
