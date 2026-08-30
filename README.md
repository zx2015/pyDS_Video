# DS Video

跨平台（macOS / Linux）PyQt6 桌面客户端，用于连接群晖（Synology）DSM 7.2 NAS，
浏览并播放 File Station 中的视频文件。

> 原计划对接 DSM 的 Video Station 套件，但在真实设备上确认该套件已从 Package Center
> 下架，因此改为基于 DSM 内置的 **File Station**（`SYNO.FileStation.*`）实现浏览与
> 流式播放。详见 `docs/design.md` 中的变更记录。

## 功能特性

- 使用用户名/密码登录 DSM（不支持 2FA），登录信息可加密保存在本地，下次启动自动登录。
- 以目录树 + 文件列表的方式浏览共享文件夹，默认只显示 `video`/`电影` 目录下的内容。
- 双击视频文件后直接调用系统安装的 VLC 独立播放（不下载、不转码），支持基于 HTTP
  Range 请求的拖动/seek；未安装 VLC 时会提示安装方式。
- 统一的深色 QSS 主题界面（Operate 模式，克制配色），窗口默认尺寸 1280×800。
- 仅支持 macOS + Linux、局域网访问、单账号无 2FA，详见 `docs/requirements.md`
  的“非目标”章节。

## 快速开始

```bash
# 创建虚拟环境
python3 -m venv .venv

# 安装项目 + 开发依赖（可编辑模式）
.venv/bin/python3 -m pip install -e ".[dev]"

# 启动应用（需要图形环境；播放功能依赖系统安装的 VLC，见下文）
.venv/bin/ds-video
```

> 若系统未预装 `pip`（`ModuleNotFoundError: No module named pip`），可用
> `python3 -m venv --without-pip .venv && .venv/bin/python3 get-pip.py` 引导安装
> （`get-pip.py` 来自 https://bootstrap.pypa.io/get-pip.py ）。
>
> 播放功能通过启动系统安装的 `vlc` 可执行文件实现，不在本项目 pip 依赖范围内，需自行
> 安装（macOS: `brew install --cask vlc`；Linux: `sudo apt install vlc` 等）。若未安装，
> 应用会弹窗提示安装方式。
>
> 在无图形界面的环境（CI/远程终端）下运行任何涉及 PyQt6 的命令，需设置
> `QT_QPA_PLATFORM=offscreen`，否则会因找不到显示服务器而报错。

### Linux 桌面快捷方式（可选）

参见 `resources/README.md`，可将应用安装为带自定义图标的桌面/任务栏启动项。

## 运行测试

```bash
# 单元测试（不联网，不需要真实 DSM）
QT_QPA_PLATFORM=offscreen .venv/bin/python3 -m pytest tests/unit -q

# 集成测试（需要真实 DSM 设备，未设置环境变量时自动跳过，详见 docs/design.md 7.2）
DS_VIDEO_TEST_HOST=<ip> DS_VIDEO_TEST_PORT=5000 \
DS_VIDEO_TEST_USERNAME=<user> DS_VIDEO_TEST_PASSWORD=<pass> \
QT_QPA_PLATFORM=offscreen .venv/bin/python3 -m pytest -m integration tests/integration -q
```

## 项目文档

- [`docs/requirements.md`](docs/requirements.md) — 需求文档
- [`docs/design.md`](docs/design.md) — 设计文档（含各阶段变更记录）
- [`AGENTS.md`](AGENTS.md) — 面向后续开发（含 AI 代理）的目录结构与技术要点说明

## 目录结构

```
ds_video/
├── AGENTS.md                  # 开发流程与目录规划指导
├── pyproject.toml             # 依赖、构建、pytest 配置
├── docs/                      # 需求文档、设计文档
├── resources/                 # 图标、桌面启动器模板等静态资源
├── src/ds_video/
│   ├── api/                   # FileStationClient：登录、目录浏览、流媒体直链拼装
│   ├── ui/                    # PyQt6：LoginWindow / MainWindow / VlcLauncher / 主题
│   ├── config/                # 连接设置的加密存储 + 跨平台路径
│   └── logging_setup.py       # 统一日志配置
└── tests/
    ├── unit/                  # 不联网的单元测试
    └── integration/           # 需要真实 DSM 设备的集成测试
```

## 许可证

MIT
