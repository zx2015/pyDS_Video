# 设计文档

## 状态
- [x] 设计中（草稿，已确认）
- [x] 设计已确认（编码前必须勾选）

> 用户已确认本设计，且确认有真实 DSM 设备可用于集成测试（需要时提供地址/账号，通过环境变量注入测试配置，见第 7.2 节）。

> 本文档基于已确认的 `docs/requirements.md` 编写。用户确认本设计后，方可开始编码。

> **变更记录（2026-08-29）**：真实设备实测确认该 DSM 未安装 Video Station 套件（DSM 7.2 已从
> Package Center 下架），第 2 节已改为基于 DSM 内置的 **File Station**（`SYNO.FileStation.*`）
> 实现浏览与流式播放，其余章节的结论基本不变（详见各节内的更新说明）。

> **变更记录（2026-08-29 续二）**：进一步测试发现，即使不嵌入视频，libvlc 在该桌面环境（原生 Wayland、
> 无 `xcb` 平台插件）下仍会自行卡死（其内置的 X11/Wayland 视频输出模块均无法正常创建输出，但
> 卡在等待而非快速失败）。因此简化为**统一直接调用系统安装的 VLC 独立进程播放**（不再尝试
> python-vlc 嵌入，也不再区分平台/桌面环境）：`PlayerWindow` 通过 `subprocess.Popen(["vlc", url])`
> 启动系统 VLC 播放视频，播放/暂停/进度/音量均在 VLC 自己的窗口中操作；若系统未安装 VLC，则
> 提示用户安装（macOS: `brew install --cask vlc`；Linux: `sudo apt install vlc` 等）。据此移除了
> `python-vlc` 依赖及 `player/` 包（`PlayerBackend`/`VlcPlayerBackend`）。

> **变更记录（2026-08-30）**：双击视频后不再弹出独立的"播放器窗口"（原 `PlayerWindow`，带状态
> 标签与停止按钮）；改为 `VlcLauncher`（`ui/vlc_launcher.py`）直接调用系统 VLC 播放，成功路径
> 无任何弹窗，仅在真正失败（获取播放地址失败、未安装 VLC、启动 VLC 失败）时弹出 `QMessageBox`
> 错误提示。每次双击都会独立启动一个新的 VLC 进程（不追踪/终止先前的进程），与此前多播放窗口
> 可并存的行为一致。

> **变更记录（2026-08-30 续）**：`LoginWindow` 启动时若检测到本地已保存的登录信息，会自动尝试
> 使用该信息登录，无需用户再次点击"连接"；连接表单始终保持可见并已用保存的信息预填。若自动
> 连接失败，仅弹出一次性提示说明失败原因，随后用户可直接在表单中修改信息并手动点击"连接"重试
> （不引入单独的"自动连接模式"或额外窗口）。

## 1. 总体架构

### 1.1 模块划分

```
┌─────────────────────────────────────────────────────────┐
│                       ui (PyQt6)                         │
│  LoginWindow │ MainWindow(目录树+文件列表) │ VlcLauncher（无窗口） │
└───────────────┬───────────────────────────┬──────────────┘
                │ 调用                      │ 调用
                ▼                            ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│  api (FileStation 客户端)   │   │  player (播放后端封装)     │
│  - 登录/会话（复用 synology- │   │  - VlcPlayerBackend       │
│    api 内置的 FileStation） │   │    (基于 python-vlc)      │
│  - 共享文件夹/目录/文件列表   │   │  - 统一播放控制接口        │
│  - 拼装带鉴权信息的流式 URL   │   └───────────────────────────┘
└───────────────┬───────────┘
                │ HTTP(S) / WebAPI
                ▼
        ┌───────────────────┐
        │  DSM 7.2 NAS       │
        │  File Station（内置）│
        └───────────────────┘

        config（配置/凭证管理，被 ui 与 api 共用）
```

### 1.2 数据流（典型场景：浏览并播放一个视频）

1. 用户在 `LoginWindow` 输入 DSM 地址、用户名、密码（或从 `config` 加载已保存的凭证）。
2. `api.FileStationClient` 内部复用 `synology-api` 内置的 `synology_api.filestation.FileStation` 完成 `SYNO.API.Auth` 登录，获得 `_sid`（session id）与 `_syno_token`（CSRF token）。
3. 登录成功后，`MainWindow` 调用 `api` 层：先列出共享文件夹（`SYNO.FileStation.List` 的 `list_share` 方法）作为目录树根节点，展开时再用 `get_file_list` 逐级列出子目录/文件，以树形+列表方式展示。
4. 用户双击某个视频文件，`MainWindow` 调用 `api` 拼装该文件的可播放流式 URL：`SYNO.FileStation.Download`（`method=download&mode=open`），并将 `_sid` 与 `SynoToken` 都作为 URL 查询参数携带（已实测确认二者都能作为 query string 传递，无需自定义 HTTP 请求头，便于 VLC 直接播放）。
5. `VlcLauncher` 直接调用系统 VLC（`subprocess.Popen(["vlc", url])`）播放该 URL，无中间播放窗口；DSM 端支持 HTTP Range 请求（已实测返回 `206 Partial Content` / `Accept-Ranges: bytes`），因此可正常拖动进度条。

## 2. DSM / File Station API 调用方案

### 2.1 登录认证
- 直接使用 `synology-api` **内置**的 `synology_api.filestation.FileStation`（无需再像 Video Station 方案那样自行继承 `BaseApi` 拼接未知 API，File Station 是该库官方支持的模块）完成：
  - `SYNO.API.Auth` 登录，获取 `_sid` 与 `_syno_token`。
  - 后续请求自动附带 `_sid`，无需自己重新实现登录流程。
- 仅支持单账号、无 2FA（`otp_code=None`），符合已确认需求。
- 会话失效（如 session 过期）时，`api` 层捕获对应错误码，触发重新登录或提示用户重新输入密码。

### 2.2 浏览与流式播放（已用真实 DSM 7.2 设备验证通过）
- **列出共享文件夹**（作为目录树根节点）：`fsclient.get_list_share()` → `SYNO.FileStation.List`（`list_share`）。
- **列出子目录/文件**：`fsclient.get_file_list(path)` → `SYNO.FileStation.List`（`list`），返回项通过 `isdir` 区分文件夹/文件。
- **获取流式播放 URL**：不使用库自带的 `get_file`（该方法会把整个文件下载到内存/磁盘，不适合流式播放），而是在 `api/file_station.py` 中自行拼装 URL：
  ```
  {base_url}{path}?api=SYNO.FileStation.Download&version={ver}&method=download
    &path={urlencode(文件路径)}&mode=open&_sid={sid}&SynoToken={syno_token}
  ```
  该 URL 是一个完整的、自包含鉴权信息的 HTTP(S) 链接，支持 Range 请求，可直接交给 VLC 播放/拖动进度条，无需任何自定义请求头。
- 错误处理：包一层 `FileStationClient`，把 `synology_api.exceptions.FileStationError` 等异常统一转换为 `ds_video.api.exceptions.ApiError`。

### 2.3 错误处理
- 统一将 WebAPI 返回的 `error.code` 映射为自定义异常（如 `AuthError`、`SessionExpiredError`、`ApiError`），供 UI 层捕获并提示用户。

## 3. 播放器技术选型

- **GUI 框架**：PyQt6。
- **播放引擎**：`python-vlc`（基于系统安装的 VLC 库/`libvlc`）。
  - 通过 `vlc.Instance()` 创建播放实例，`media_player_new()` 播放 `api` 返回的流媒体 URL。
  - 在 PyQt6 界面中，通过原生窗口句柄（macOS: `set_nsobject`；Linux: `set_xwindow`）把 VLC 视频输出嵌入到 Qt Widget 中。
- **依赖前提**：用户系统需已安装 VLC（提供 `libvlc`），随需求确认，暂不做打包/自动安装处理。
- **播放控制接口**（`player/backend.py` 中定义抽象接口，当前唯一实现为 VLC）：
  - `play(url)` / `pause()` / `resume()` / `stop()`
  - `seek(position_ms)` / `get_position()` / `get_duration()`
  - `set_volume(level)`

## 4. 跨平台注意事项（macOS / Linux）

| 方面 | macOS | Linux |
|---|---|---|
| VLC 依赖 | 需安装 VLC.app 或通过 Homebrew 安装 libvlc | 需安装发行版对应的 `vlc`/`libvlc` 包 |
| 视频嵌入窗口 | 使用 `media_player.set_nsobject(int(widget.winId()))` | 使用 `media_player.set_xwindow(int(widget.winId()))`（依赖 X11，Wayland 下可能需要 XWayland 兼容） |
| 凭证存储路径 | 遵循 `~/Library/Application Support/ds_video/` | 遵循 `~/.config/ds_video/`（或 XDG 规范） |
| PyQt6 安装 | pip 安装即可，Apple Silicon 需确认 wheel 可用性 | pip 安装，注意部分发行版需要额外系统库（如 `libxcb`） |

## 5. 配置与凭证存储方案

- 配置文件路径：按平台使用对应用户配置目录（见上表），文件名如 `config.json` / `credentials.enc`。
- 存储内容：DSM 服务器地址、端口、用户名、**加密后的密码**。
- 加密方式：使用对称加密（如 `cryptography` 库的 Fernet），密钥可基于机器/用户本地派生并存储在同一配置目录下的单独密钥文件中（不依赖系统钥匙串，符合已确认需求）。
- 首次运行且无配置文件时，`LoginWindow` 要求用户输入信息，登录成功后询问是否保存。

## 6. 日志与错误处理策略

- 使用标准库 `logging`，按模块划分 logger（`ds_video.api`、`ds_video.player`、`ds_video.ui`）。
- 日志级别：默认 `INFO`，网络请求/响应细节以 `DEBUG` 输出，便于排查登录/播放问题。
- 日志输出：控制台 + 本地日志文件（同配置目录下 `logs/`），避免影响 GUI 主线程。
- UI 层统一通过弹窗/状态栏展示用户可理解的错误信息（如"登录失败：用户名或密码错误"），底层异常堆栈记录到日志文件。

## 7. 测试策略

### 7.1 单元测试（`tests/unit`）
- 覆盖 `api` 层：mock HTTP 响应（如使用 `responses` 或 `unittest.mock`），验证登录、目录解析、流媒体 URL 拼装、错误码映射等逻辑，不依赖真实网络。
- 覆盖 `config` 层：加密/解密、配置文件读写的正确性。
- 覆盖 `player` 抽象接口：对播放控制逻辑（如状态切换）做可 mock 部分的测试；`python-vlc` 底层调用可通过接口抽象后 mock 掉。

### 7.2 集成测试（`tests/integration`）
- 针对真实或模拟的 DSM 环境（用户提供测试 NAS，或使用可控的 mock WebAPI 服务）进行端到端联调：登录 → 获取目录 → 获取流媒体 URL 是否可达。
- 默认不在无网络的 CI 环境强制运行（可通过环境变量/pytest marker 跳过，如 `@pytest.mark.integration`，需要显式指定测试环境的 DSM 地址/账号）。
- 用户已确认拥有真实 DSM 设备用于集成测试。测试连接信息通过环境变量注入，不写入代码库：
  - `DS_VIDEO_TEST_HOST`、`DS_VIDEO_TEST_PORT`、`DS_VIDEO_TEST_USERNAME`、`DS_VIDEO_TEST_PASSWORD`
  - 未设置这些环境变量时，集成测试自动跳过（`pytest.mark.skipif`）。

### 7.3 测试工具链（待确认）
- 建议使用 `pytest` 作为测试框架，`pytest-mock`/`responses` 辅助 mock HTTP。
- 依赖管理建议使用 `pyproject.toml` + `pip`（或 `poetry`，具体在确认设计后落地）。

## 8. 确认记录

以上设计已经用户确认（含播放器嵌入方案、加密方案、集成测试使用真实 DSM 设备）。2026-08-29 已将 API
方案由 Video Station 切换为 File Station，并在真实 DSM 7.2 设备上完整验证登录、浏览共享文件夹/子目录/
文件、拼装流式播放 URL（含 Range 请求）均可正常工作，无需再等待进一步实测确认。
