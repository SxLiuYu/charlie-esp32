# 方案A：ESP32 集成 Charlie 系统 — 完整文档

## 原理

利用原始固件 (ESP-IDF v5.5.1) 的二进制补丁，将 URL 指向 Charlie voice_server，无需编译固件。Charlie 系统已有完整的 ASR/LLM/TTS 管线，ESP32 作为语音终端接入。

## 通信架构

```
┌──────────────┐   HTTP POST (OTA)    ┌───────────────────────┐
│  ESP32-S3    │ ───────────────────→ │  Charlie voice_server │
│  v2.1.0      │←──────────────────── │  :8000                │
│  MqttProtocol│  {"mqtt":{...},      │                       │
│              │   "websocket":{...}} │  ┌─────────────────┐  │
│              │                      │  │ mosquitto :1883 │  │
│   MQTT ──────┼──────────────────────┼──┤ (MQTT Broker)   │  │
│   常驻连接    │  charlie/esp32/+/up  │  └─────────────────┘  │
│              │  charlie/esp32/+/down│                       │
│              │                      │  ┌─────────────────┐  │
│   UDP ───────┼──────────────────────┼──┤ UDP :8888       │  │
│   加密音频    │  AES-CTR Opus 16kHz  │  │ (音频通道)      │  │
│              │                      │  └─────────────────┘  │
│              │                      │  ┌─────────────────┐  │
│              │                      │  │ ASR→LLM→TTS     │  │
│              │                      │  │ (Brain Pipeline) │  │
│              │                      │  └─────────────────┘  │
└──────────────┘                      └───────────────────────┘
```

### 协议流程

```
1. 设备开机 → WiFi 连接 → POST /xiaozhi/ota
2. OTA 响应返回 mqtt + websocket 配置
3. 有 mqtt 节时设备用 MqttProtocol（常驻 MQTT 连接）
4. 设备连 mosquitto:1883，订阅 charlie/esp32/{id}/down
5. 设备处于唤醒词待机模式（WakeNet 离线检测）
6. 唤醒词检测 → MQTT 发 hello → 服务器回复 UDP 配置
7. 设备建立 UDP 音频通道 → 加密 Opus 双向传输
8. 对话结束 → goodbye → 回到待机模式（MQTT 保持连接）
```

## 已完成功能

### ✅ 核心通信
| 功能 | 状态 | 说明 |
|------|------|------|
| OTA 端点 | ✅ | Charlie `POST /xiaozhi/ota`，返回 mqtt + websocket |
| MQTT 常驻连接 | ✅ | 设备连 mosquitto:1883，持续在线 |
| UDP 加密音频 | ✅ | AES-CTR 加密，16kHz Opus，端口 8888 |
| 主动推送文字 | ✅ | MQTT `notification` / `tts sentence_start` 显示在屏幕 |
| 主动推送音频 | ✅ | 需 UDP 会话（hello 后），MQTT 通知 + UDP Opus 帧 |

### ✅ 语音管线（Charlie 提供）
| 功能 | 实现 | 说明 |
|------|------|------|
| ASR | `agent/asr_tts.py` | SenseVoice 本地 → 百度 → Vosk 三级降级 |
| LLM | `voice_agent.py` | Brain 引擎，支持 MCP 工具调用 |
| TTS | `agent/asr_tts.py` | 百度 TTS → Qwen TTS 降级，支持缓存 |
| Opus 编解码 | `app/xiaozhi_codec.py` | opuslib 绑定，支持缓存 |
| 端点检测 | `app/mqtt_server.py` | Silero VAD + RMS 自适应阈值 |

### ✅ Charlie 推送管线
| 路径 | 触发方式 | 条件 |
|------|----------|------|
| WebSocket 直推 | `push_tts_to_xiaozhi` | 设备连 WS 时 |
| MQTT 直推 | `push_tts_to_mqtt` | 有活跃 UDP 会话时 |
| MQTT 通知 | `push_notification` | 无会话时推文字到默认设备 |
| 入队待 flush | `enqueue_xiaozhi_pending` | 以上都不可用时排队 |

### ✅ 可用 MCP 工具（固件内置）
- `self.light.get_power` / `turn_on` / `turn_off` — 板载灯控
- `get_system_info` / `get_device_status` — 系统信息
- `audio_speaker.set_volume` — 音量控制
- `camera.take_photo` — 拍照
- `screen.get_info` / `preview_image` / `set_brightness` / `set_theme` / `snapshot` — 屏幕控制

## 文件清单

| 文件 | 路径 | 说明 |
|------|------|------|
| 补丁固件 | `flash_16MB_charlie.bin` | URL→192.168.1.12:8000 |
| 原始固件 | `flash_16MB_original.bin` | 出厂固件备份 |
| 补丁脚本 | `patch_local.py` | 二进制补丁生成 |
| Charlie 服务端 | `../charlie/charlie/voice_server.py` | FastAPI 主入口 |
| MQTT 服务端 | `../charlie/charlie/app/mqtt_server.py` | MQTT+UDP 协议 |
| WebSocket 端 | `../charlie/charlie/app/xiaozhi_ws.py` | WS 协议（备用） |
| 编解码 | `../charlie/charlie/app/xiaozhi_codec.py` | Opus/WAV/MP3 |
| ASR/TTS | `../charlie/charlie/agent/asr_tts.py` | 语音识别/合成 |
| 推送管线 | `../charlie/charlie/app/notifications.py` | 推送调度 |
| OTA 路由 | `../charlie/charlie/app/routes/reminders.py` | /xiaozhi/ota |
| 测试 | `../charlie/charlie/tests/test_mqtt_server.py` | 37 tests ✅ |
| 测试 | `../charlie/charlie/tests/test_esp32_wizard.py` | 7 tests ✅ |

## 修改记录

### 固件补丁
```python
# flash_16MB_charlie.bin 补丁内容
PATCHES = [
    (b"wss://api.tenclass.net/xiaozhi/v1/",   # 34 bytes
     b"ws://192.168.1.12:8000/ws/xiaozhi"),     # 33 bytes + 1 NUL
    (b"https://api.tenclass.net/xiaozhi/ota/",  # 37 bytes
     b"http://192.168.1.12:8000/xiaozhi/ota"),  # 36 bytes + 1 NUL
]
```

### Charlie 配置修改
```
# .env
MQTT_ENABLE_OTA=1          # OTA 响应包含 mqtt 节
MQTT_BROKER=192.168.1.12   # MQTT broker 地址
MQTT_PORT=1883
MQTT_DEVICE_ID=esp32-default
```

### 代码修复
1. **`mktt_server.py` — timestamp 溢出修复**：`ts = int(time.time() * 1000)` 超过 uint32 范围，改为 `& 0xFFFFFFFF`
2. **`mktt_server.py` — push_notification 增强**：无活跃会话时也能向默认设备推送文字通知

## 测试覆盖

```bash
# 运行所有 ESP32 相关测试
cd charlie && .venv/bin/python -m pytest tests/test_mqtt_server.py tests/test_esp32_wizard.py -v
```

| 测试类 | 数量 | 覆盖 |
|--------|------|------|
| TestAesKeyGeneration | 3 | AES 密钥生成 |
| TestAesCtrCrypt | 2 | 加密/解密往返 |
| TestBuildAudioPacket | 3 | UDP 音频包构造 |
| TestExtractDeviceId | 3 | topic 设备 ID 提取 |
| TestHandleHello | 3 | hello 处理 + 会话创建 |
| TestHandleGoodbye | 1 | 会话清理 |
| TestHandleListen | 3 | listen 状态处理 |
| TestPushTts | 3 | TTS 推送（无会话/无地址/完整） |
| TestProactiveTextPush | 4 | 主动推送（默认设备/注册设备/自定义/无会话） |
| TestOnMqttMessage | 4 | MQTT 消息路由 |
| TestDeviceCountAndConnected | 3 | 设备计数和连接状态 |
| TestModuleFunctions | 2 | 模块级函数 |
| ESP32 Wizard | 7 | 烧录向导 API |
| **总计** | **44** | **全部通过** |

## 待实现

| 功能 | 优先级 | 说明 |
|------|--------|------|
| OTA 固件升级 | 中 | Charlie 响应 firmware 节触发设备 OTA |
| 多设备支持 | 低 | 多个 ESP32 同时连 Charlie |
| 自定义唤醒词 | 低 | 修改 WakeNet 模型 |
| LED 灯控集成 | 低 | 实现 self.light MCP 工具响应 |