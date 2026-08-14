# v1.1.0 固件评估报告

> 评估日期: 2026-08-14
> 评估对象: `flash_16MB_v1.1.0.bin`
> 参照标准: Charlie 语音助手项目对 ESP32 固件的功能要求

---

## 评估结论: ✅ 全部完成

v1.1.0 固件满足 Charlie 项目对 ESP32 固件的所有功能要求。

---

## 一、协议完整性对照

### 1.1 设备发现与会话初始化

| 要求 | 服务端行为 | 固件 v1.1.0 | 状态 |
|------|-----------|-------------|------|
| hello 含设备标识 | 从 hello 提取 device_id 作为设备 key | ✅ hello JSON 含 `device_id` (UUID) | ✅ |
| session 管理 | 生成 session_id 返回给设备 | ✅ 服务端生成并返回，固件存入 session_id_ | ✅ |
| 音频参数协商 | 返回 sample_rate/frame_duration | ✅ 固件发送 16kHz/60ms，服务端返回 24kHz/60ms | ✅ |

**hello 消息（WebSocket）:**
```json
{
  "type": "hello",
  "version": 1,
  "features": {"mcp": true},
  "transport": "websocket",
  "audio_params": {"format": "opus", "sample_rate": 16000, "channels": 1, "frame_duration": 60},
  "device_id": "909b14d1-850c-4e16-80bf-04916553597c"
}
```

**hello 消息（MQTT）:**
```json
{
  "type": "hello",
  "version": 3,
  "transport": "udp",
  "features": {"mcp": true},
  "audio_params": {"format": "opus", "sample_rate": 16000, "channels": 1, "frame_duration": 60},
  "device_id": "909b14d1-... (同 UUID)"
}
```

### 1.2 设备 → 服务器（上行消息）

| 消息类型 | 格式 | 用途 | 状态 |
|----------|------|------|------|
| `listen/detect` | `{"type":"listen","state":"detect","text":"唤醒词"}` | 唤醒词检测触发 | ✅ 已有 |
| `listen/start` | `{"type":"listen","state":"start"}` | 开始录音 | ✅ 已有 |
| `listen/stop` | `{"type":"listen","state":"stop"}` | 停止录音 | ✅ 已有（auto模式不可靠，服务端端点检测补偿） |
| `abort` | `{"type":"abort","session_id":"..."}` | 打断播放 | ✅ 已有 |
| `ping` | `{"type":"ping"}` | 心跳保活 | ✅ v1.1.0 新增，每 30s |

### 1.3 服务器 → 设备（下行消息）

| 消息类型 | 格式 | 用途 | Charlie 发送 | 固件处理 | 状态 |
|----------|------|------|-------------|---------|------|
| `tts/start` | `{"type":"tts","state":"start"}` | 开始播报 | ✅ | ✅ 进入 Speaking 状态 | ✅ |
| `tts/stop` | `{"type":"tts","state":"stop"}` | 结束播报 | ✅ | ✅ 回到 Listening/Idle | ✅ |
| `tts/sentence_start` | `{"type":"tts","state":"sentence_start","text":"..."}` | 显示字幕 | ✅ | ✅ SetChatMessage("assistant") | ✅ |
| `stt/text` | `{"type":"stt","text":"..."}` | 显示识别结果 | ✅ | ✅ SetChatMessage("user") | ✅ |
| `llm/emotion` | `{"type":"llm","emotion":"..."}` | 切换表情 | ⚠️ 暂未发送 | ✅ 支持 | ⚠️ 服务端待补 |
| `goodbye` | `{"type":"goodbye","session_id":"..."}` | 结束对话 | ✅ | ✅ 关闭音频通道 | ✅ |
| `notification` | `{"type":"notification","text":"...","ttl":5000}` | 弹出通知 | ✅ (MQTT only) | ✅ ShowNotification | ✅ |
| `system/reboot` | `{"type":"system","command":"reboot"}` | 重启设备 | ⚠️ 暂未发送 | ✅ 支持 | ⚠️ 服务端待补 |
| `ping` | `{"type":"ping"}` | 心跳请求 | ⚠️ 暂未发送 | ⚠️ 未处理 | ⚠️ 服务端待补 |
| `pong` | `{"type":"pong"}` | 心跳回复 | ✅ (收到固件ping时回复) | N/A | ✅ |

---

## 二、MQTT 本地化

| 要求 | v1.0.0 | v1.1.0 |
|------|--------|--------|
| endpoint | `mqtt.xiaozhi.me` (公网) ❌ | NVS 清空 → Charlie fallback `192.168.1.12:1883` ✅ |
| publish_topic | `device-server` (非标准) ❌ | `charlie/esp32/{uuid_short}/up` ✅ |
| subscribe_topic | `null` (无法接收) ❌ | `charlie/esp32/{uuid_short}/down` ✅ |
| client_id | `GID_test@@@...` ❌ | `charlie-esp32-{uuid_short}` ✅ |

**Charlie MQTT fallback 代码** (`mqtt_protocol.cc:76-89`):
```cpp
if (endpoint.empty()) {
    auto uuid = Board::GetInstance().GetUuid();
    auto short_id = uuid.substr(0, 8);
    endpoint = CHARLIE_MQTT_FALLBACK_ENDPOINT;  // "192.168.1.12:1883"
    client_id = "charlie-esp32-" + short_id;
    publish_topic_ = "charlie/esp32/" + short_id + "/up";
    subscribe_topic_ = "charlie/esp32/" + short_id + "/down";
}
```

---

## 三、v1.1.0 新增功能验证

### 3.1 device_id (Fix #1)

**修改文件**: `websocket_protocol.cc:257-259`, `mqtt_protocol.cc:355-357`

```cpp
// 双向协议均添加
auto uuid = Board::GetInstance().GetUuid();
cJSON_AddStringToObject(root, "device_id", uuid.c_str());
```

**Charlie 服务端兼容**: `xiaozhi_ws.py:895-901` 已支持从 hello 提取 device_id：
```python
for dev_key in ("client_id", "device_id", "device"):
    cand = data.get(dev_key)
    ...
    device_key = re.sub(r"[^0-9A-Za-z_-]", "", str(cand))[:32] or device_key
```

### 3.2 ping/pong 心跳 (Fix #5)

**修改文件**: `websocket_protocol.h`, `websocket_protocol.cc`

- 每 30s 发送 `{"type":"ping"}`
- 仅在音频通道打开时发送（避免空闲时浪费资源）
- Charlie 服务端已处理: `xiaozhi_ws.py:961-962` → 回复 `{"type":"pong"}`
- 析构时自动停止定时器

### 3.3 goodbye 消息 (Fix #6)

**修改文件**: `websocket_protocol.cc:105-114`

- 音频通道关闭时发送 `{"type":"goodbye","session_id":"..."}`
- 配合 Charlie 服务端的 ARM_WINDOW 超时机制，实现更优雅的连接管理
- 避免服务端会话泄漏

---

## 四、已知遗留项（非固件问题）

| # | 项目 | 说明 | 影响 |
|---|------|------|------|
| 1 | `notification` via WebSocket | Charlie 仅在 MQTT 模式下发送 notification，WebSocket 模式下不发送 | 低（日常对话不受影响） |
| 2 | `llm/emotion` 表情 | Charlie 服务端暂未发送 llm 消息，固件表情功能闲置 | 低（视觉增强） |
| 3 | `system/reboot` 远程重启 | Charlie 暂未通过协议发送重启命令 | 低（手动重启即可） |
| 4 | `ping` 由服务器发起 | Charlie 只在收到设备 ping 时回复 pong，不主动发 ping | 低（设备主动心跳已足够） |
| 5 | `listen/stop` 不可靠 | xiaozhi v2.1.0 固件在 auto 模式下不发送 listen/stop，Charlie 用 VAD 端点检测补偿 | 已知限制，无需修复 |

---

## 五、编译与验证

### 源码修改汇总

```
xz/main/protocols/websocket_protocol.h  (+5 行)
xz/main/protocols/websocket_protocol.cc (+42 行)
xz/main/protocols/mqtt_protocol.cc      (+3 行)
```

### 构建命令
```bash
export IDF_PATH=/Users/sxliuyu/esp-idf-v5.5.2
export IDF_SKIP_CHECK_SUBMODULES=1
cd /Users/sxliuyu/repos/xz
/Users/sxliuyu/.espressif/python_env/idf5.5_py3.14_env/bin/python \
  /Users/sxliuyu/esp-idf-v5.5.2/tools/idf.py build
```

### 验证清单（烧录后串口）
```
I SKU=lc-s3-wifi-1.54tft
I UUID=909b14d1-850c-4e16-80bf-04916553597c
I Connecting to websocket server: ws://192.168.1.3:8000/ws/xiaozhi with version: 1
I Ping timer started (interval=30s)    ← v1.1.0 新增
I Session ID: xxx
>> <STT text>                          ← 识别结果
<< <TTS text>                          ← TTS 字幕
I Sent goodbye, session_id=xxx         ← v1.1.0 新增
```

---

## 六、发布

| 版本 | 文件 | GitHub Release |
|------|------|----------------|
| v1.0.0 | `flash_16MB_local.bin` | [v1.0.0](https://github.com/SxLiuYu/charlie-esp32/releases/tag/v1.0.0) |
| **v1.1.0** | `flash_16MB_v1.1.0.bin` | [v1.1.0](https://github.com/SxLiuYu/charlie-esp32/releases/tag/v1.1.0) |
