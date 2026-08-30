# AGENTS.md

本文件指导在 `ds_video` 仓库中进行开发的 Copilot / AI 代理，确保后续工作按照统一的流程和结构推进。

## 项目简介

`ds_video` 是一个跨平台的 Python 客户端，用于连接群晖（Synology）DSM 7.2 NAS：

- 使用用户名/密码登录 DSM
- 通过 **File Station** 浏览共享文件夹与目录中的视频文件（详见下方"变更记录"：
  原计划对接的 Video Station 套件在用户实际的 DSM 7.2 设备上已不存在）
- 在本地播放视频，支持多种常见格式
- 使用 PyQt6 实现跨平台图形界面（macOS + Linux）

项目目前处于**编码/测试阶段**：需求文档与设计文档均已确认（见 `docs/requirements.md`、
`docs/design.md`），实现（File Station API 客户端、播放后端、PyQt6 UI）与自动化测试已完成，
并已通过真实 DSM 设备验证登录、浏览、流式播放（含拖动/seek）。

## 必须遵守的开发流程

在编写任何业务实现代码之前，必须按以下顺序推进，每个阶段结束后需与用户确认，得到明确同意后才能进入下一阶段：

1. **需求澄清**
   - 与用户逐项确认功能范围、非功能需求（性能、支持平台、认证方式、网络环境等）以及边界情况。
   - 澄清完成后，将结果整理写入 `docs/requirements.md`。

2. **设计文档**
   - 基于已确认的需求编写 `docs/design.md`，至少包含：
     - 总体架构（模块划分、数据流、时序）
     - DSM / Video Station API 调用方案（登录认证、目录浏览、获取视频播放地址、错误码处理）
     - 播放器技术选型（PyQt/PySide + 媒体后端，如 QtMultimedia、VLC、mpv 等）及理由
     - 跨平台注意事项（Windows / macOS / Linux 的差异与依赖）
     - 配置与凭证存储方案（避免明文保存密码）
     - 日志与错误处理策略
     - 测试策略（单元测试范围、如何 mock DSM API、UI/集成测试方式）

3. **设计确认**
   - 将设计文档提交用户审阅，获得明确同意后才能开始编码。
   - 未确认设计前，不要创建业务代码文件（本文件中规划的空目录骨架除外）。

4. **实现与测试**
   - 编码的同时同步编写自动化测试，确保关键路径（登录、目录浏览、视频地址解析、播放控制）都有测试覆盖。
   - 依赖管理、构建、测试工具链选型（如 poetry/pip、pytest 等）在设计文档中确定后，落地为 `pyproject.toml` 等配置文件，并同步更新本文件的“构建/测试命令”章节。

若需求或设计发生变化，先更新对应文档，再继续开发，保持文档与代码同步。

## 目录结构

```
ds_video/
├── AGENTS.md                  # 本文件：开发流程与目录规划指导
├── pyproject.toml             # 依赖、构建、pytest 配置
├── docs/
│   ├── requirements.md        # 需求文档（已确认）
│   └── design.md              # 设计文档（已确认）
├── src/
│   └── ds_video/              # 主 Python 包
│       ├── api/               # FileStationClient：登录（复用 synology-api 的
│       │                      # filestation.FileStation）、共享文件夹/目录浏览、
│       │                      # 拼接带 _sid+SynoToken 的流媒体直链；exceptions.py 统一异常类型
│       ├── ui/                # PyQt6：LoginWindow / MainWindow（树形目录+文件列表）/
│       │                      # VlcLauncher（双击视频后直接调用系统 VLC 播放，不弹出播放窗口/对话框，
│       │                      # 只在真正失败时弹出错误提示）；app.py 是程序入口（console script: ds-video）
│       │                      # theme.py 统一深色 QSS 主题 + 程序图标（应用启动时调用 apply_theme(app)）
│       ├── config/            # DsmConnectionSettings 的加密存储（Fernet）+ 跨平台路径
│       └── logging_setup.py   # 统一日志配置（控制台 + 滚动文件）
├── tests/
│   ├── unit/                  # 不联网：mock request_data / 文件系统临时目录
│   └── integration/           # 需要真实 DSM，通过环境变量注入连接信息，默认自动跳过
└── resources/                  # 图标、样式表（QSS）等静态资源（当前为空，按需添加）
```

## 技术要点与注意事项

- DSM 通过官方 WebAPI（`webapi/entry.cgi`）提供接口；File Station 由 `synology-api` 库
  **原生支持**（`synology_api.filestation.FileStation`），`api/file_station.py` 中的
  `FileStationClient` 包装该类，提供 `list_shares()` / `list_folder(path)` / `get_stream_url(path)`。
- **关键鉴权细节（已在真实 DSM 7.2 设备上验证）**：`SYNO.FileStation.Download`
  (method=download, mode=open) 除 `_sid` 外还必须携带 CSRF token，且该 token 可以作为
  **查询参数 `SynoToken`**（而非仅 `X-SYNO-TOKEN` 请求头）传递——这样可以构造一个
  libvlc 能直接播放、无需自定义 HTTP 头的自包含 URL。缺少 token 时接口会返回 HTTP 200
  但 body 为 `{"error":{"code":119},"success":false}`，容易被误判为成功，需特别注意。
  已验证 DSM 支持 Range 请求（`Accept-Ranges: bytes`），VLC 拖动/seek 可正常工作。
- 播放采用直接播放 File Station 返回的下载直链（不下载、不做本地转码），格式支持依赖
  系统安装的 VLC 自身解码能力，不依赖 DSM 转码。
- 视频播放：统一调用系统安装的 VLC 独立进程（`subprocess.Popen(["vlc", url])`）播放，不使用
  `python-vlc`/嵌入播放（曾实测：无论嵌入还是走 python-vlc 自带视频输出，在无 `xcb` 平台插件的
  纯 Wayland 桌面上都会导致应用假死）。播放/暂停/进度/音量在 VLC 自己的窗口中操作；系统未安装
  VLC 时会弹窗提示安装方式。详见 `docs/design.md` 2026-08-29 变更记录与 `vlc_launcher.py`。
- 双击视频后不再弹出"播放中"提示窗口/对话框：`VlcLauncher.play_file()` 直接调用系统 VLC，
  仅在真正出错时（获取播放地址失败、未安装 VLC、启动 VLC 失败）弹出 `QMessageBox` 错误提示。
- `LoginWindow` 启动时若本地存在已保存的登录信息（`config/credentials.py`），会自动使用该信息
  发起连接，无需用户再次点击"连接"；表单始终保持可见并已预填，若自动连接失败，仅弹出一次性的
  提示（说明是自动连接失败、需检查/更新信息），随后用户可直接在同一表单中修改并手动点击"连接"
  重试，不会进入单独的模式或弹出额外窗口。
- UI 视觉风格：`ui/theme.py` 提供统一的深色（Operate 模式，克制配色）QSS 样式表与程序图标，
  `app.py` 在 `QApplication` 创建后立即调用 `apply_theme(app)` 全局生效。新增/修改界面组件时，
  优先复用其中已定义的角色化 QSS 选择器（如 `QPushButton[variant="primary"|"danger"]`、
  `QLabel[variant="title"|"subtitle"|"section"|"hint"|"status-ok"|"status-error"]`、
  `QFrame[variant="card"]`），保持三个窗口（登录/浏览/播放器）视觉语言一致，不要引入新的一次性配色。
- Linux 任务栏/程序坞图标：`app.py` 的 `main()` 在创建 `QApplication` 后调用
  `app.setDesktopFileName("ds-video")`，使 Qt 的 Wayland `app_id`（原生 Wayland 会话下无法
  通过 `xprop`/`WM_CLASS` 观察）与已安装的 `resources/ds-video.desktop` 对应，桌面环境（如
  GNOME）才能据此解析出正确的任务栏图标，而非通用的 Python 图标。图标资源同时安装为用户级
  `hicolor` 主题图标（`~/.local/share/icons/hicolor/256x256/apps/ds-video.png`），`.desktop`
  文件的 `Icon=` 用图标名 `ds-video` 而非绝对路径引用，兼容性更好；`StartupWMClass=ds-video`
  也需与之保持一致。若图标或 `.desktop` 有更新，需重新执行
  `cp resources/ds-video.desktop ~/.local/share/applications/` 与
  `cp resources/ds_video.png ~/.local/share/icons/hicolor/256x256/apps/ds-video.png` 并运行
  `gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor` 刷新缓存。（该配置下会在日志中看到
  一条无害的 `qt.qpa.services: Failed to register with host portal` 警告，是 Qt6 与
  xdg-desktop-portal 的已知良性提示，不影响功能。）
- 账号密码通过 `config/credentials.py` 用 `cryptography` 的 Fernet 对称加密后存于本地配置文件，密钥单独存放在同目录 `secret.key`，不依赖系统钥匙串。
- 仅支持 macOS + Linux（不支持 Windows）、局域网访问、单账号无 2FA、无下载离线播放、无打包分发，详见 `docs/requirements.md` 的"非目标"章节。

## 构建 / 测试命令

项目采用 `src/` 布局，依赖通过 `pyproject.toml` 管理。系统若未预装 `pip`（`ModuleNotFoundError: No
module named pip` 且 `ensurepip` 也不可用），可用以下方式引导：
`python3 -m venv --without-pip .venv && .venv/bin/python3 get-pip.py`（`get-pip.py` 从
`https://bootstrap.pypa.io/get-pip.py` 下载）。

```bash
# 创建虚拟环境（若尚不存在）
python3 -m venv .venv

# 安装项目 + 开发依赖（可编辑模式）
.venv/bin/python3 -m pip install -e ".[dev]"

# 运行单元测试（不联网，不需要真实 DSM）
QT_QPA_PLATFORM=offscreen .venv/bin/python3 -m pytest tests/unit -q

# 运行单个测试文件 / 单个用例
QT_QPA_PLATFORM=offscreen .venv/bin/python3 -m pytest tests/unit/test_file_station_client.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python3 -m pytest tests/unit/test_file_station_client.py::test_list_shares_parses_response -q

# 运行集成测试（需要真实 DSM 设备，见 docs/design.md 7.2；未设置环境变量时自动跳过）
DS_VIDEO_TEST_HOST=<ip> DS_VIDEO_TEST_PORT=5000 \
DS_VIDEO_TEST_USERNAME=<user> DS_VIDEO_TEST_PASSWORD=<pass> \
QT_QPA_PLATFORM=offscreen .venv/bin/python3 -m pytest -m integration tests/integration -q

# 启动应用（需要图形环境）
.venv/bin/ds-video
```

> 任何涉及 PyQt6 的命令在无图形界面的环境（CI/远程终端）下运行，需设置
> `QT_QPA_PLATFORM=offscreen`，否则会因找不到显示服务器而报错。
>
> 播放功能通过启动系统安装的 `vlc` 可执行文件实现（`subprocess.Popen`），不在本项目 pip
> 依赖范围内，需用户自行安装（macOS: `brew install --cask vlc`；Linux: 发行版对应的
> `vlc` 包，如 `sudo apt install vlc`）。若未安装，应用会弹窗提示安装方式。
