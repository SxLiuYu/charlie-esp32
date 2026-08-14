# Charlie ESP32 固件规格与优化文档

> 分析日期: 2026-08-14
> 来源: 对 `flash_16MB_local.bin` 的二进制逆向分析 + xz 固件源码对比
> 状态: 待优化 v1.1.0

---

## 一、固件现状（二进制分析结果）

### 1.1 硬件身份

| 属性 | 值 | 来源 |
|------|-----|------|
| 芯片 | ESP32-S3 | 固件 ELF |
| 板型 SKU | `lc-s3-wifi-1.54tft` | NVS + 启动日志 |
| UUID | `909b14d1-850c-4e16-80bf-04916553597c` | NVS (`uuid`) |
| ESP-IDF | v5.5.1 | 启动日志 |
| 屏幕 | ST7789 240×240 SPI (GPIO3/4/5/6/7) | 启动日志 `Turning display on` |
| 音频编解码器 | ES8311 (I2C: GPIO8/9) + I2S | 启动日志 `Es8311AudioCodec initialized` |
| 背光 | GPIO2 (active-high) | config.h |
| Flash | 16MB DIO 80MHz | bootloader signature 0x03E9 |
| PSRAM | 已检测 | `Found %luMB PSRAM device` |

### 1.2 NVS 配置（从二进制提取）

#### WiFi
| Key | Value |
|-----|-------|
| `wifi/ssid` | `CMCC-egTm` |
| `wifi/password` | `fneme97c` |
| `wifi/ssid1` | `-5!LCTECH-02` |
| `wifi/password1` | `1234567890abc` |

#### WebSocket
| Key | Value |
|-----|-------|
| `websocket/url` | `ws://192.168.1.3:8000/ws/xiaozhi` |
| `websocket/token` | `test-token` |
| `websocket/version` | 1（默认） |

#### MQTT（fallback 用）
| Key | Value |
|-----|-------|
| `mqtt/endpoint` | `mqtt.xiaozhi.me` ⚠️ 公网地址 |
| `mqtt/client_id` | `GID_test@@@14_c1_9f_3a_9a_88@@@909b14d1-850c-4e16-80bf-04916553597c` |
| `mqtt/username` | `eyJpcCI6IjExNy4xMjkuNDAuMjE0In0=` （base64，含 IP `117.129.40.214`） |
| `mqtt/password` | `^apKh/2imwQq+U9BXxC8DTuQylF/z6UOtXT3AC1qPx24=` |
| `mqtt/publish_topic` | `device-server` ⚠️ 非标准 topic |
| `mqtt/subscribe_topic` | `null` ⚠️ 未配置 |

#### 系统
| Key | Value |
|-----|-------|
| `assets/version` | 2（已检测） |
| `display/theme` | `light` |
| `ota_url` | `http://192.168.1.3:8000/xiaozhi/ota` |

### 1.3 分区布局（从二进制解析）

| 分区 | 偏移 | 大小 | 说明 |
|------|------|------|------|
| bootloader | 0x0000 | 32KB | ESP-IDF bootloader |
| nvs | 0x9000 | 16KB | WiFi/MQTT/设备参数 |
| otadata | 0xD000 | 8KB | OTA 切换标志 |
| phy_init | 0xF000 | 4KB | 射频校准数据 |
| ota_0 | 0x20000 | 4MB | 当前运行固件 |
| ota_1 | 0x410000 | 4MB | 备用分区（空闲） |
| assets | 0x800000 | 8MB | 字体/SenseVoice模型/表情图 |

### 1.4 Assets 分区内容

```
font_puhui_common_20_4.bin      # 中文字体
srmodels.bin                    # SenseVoice ASR 模型
index.json                      # 资产清单
*.png                           # 23 种表情图 (happy/sad/angry/thinking/...)
```

---

## 二、通信协议（固件实际行为）

### 2.1 WebSocket 协议流程

```
┌──────┐          hello          ┌─────────┐
│ ESP32│ ──────────────────────→ │Charlie  │
│      │  {type:hello,version:1, │         │
│      │   features:{mcp:true},  │ 回复 hello
│      │   transport:"websocket",│         │
│      │   audio_params:{...}}   │{type:hello,
└──────┘                         │ session_id,transport:"websocket",
                                 │ audio_params:{sample_rate:24000}}
┌──────┐          Opus           ┌─────────┐
│ ESP32│ ←─ 60ms Opus frames ─── │Charlie  │  (双向音频流)
│      │ ── 60ms Opus frames →  │         │
└──────┘                         └─────────┘
```

**固件发出的 Hello:**
```json
{
  "type": "hello",
  "version": 1,
  "features": {"mcp": true},
  "transport": "websocket",
  "audio_params": {
    "format": "opus",
    "sample_rate": 16000,
    "channels": 1,
    "frame_duration": 60
  }
}
```

**Charlie 回复的 Hello:**
```json
{
  "type": "hello",
  "id": "<session_id>",
  "session_id": "<session_id>",
  "transport": "websocket",
  "protocol_version": "1",
  "audio_params": {
    "format": "opus",
    "sample_rate": 24000,
    "channels": 1,
    "frame_duration": 60
  }
}
```

### 2.2 MQTT 协议流程（备选）

固件通过 OTA 返回的 `mqtt` 段切换至 MqttProtocol：
1. ESP32 连接 MQTT broker，订阅 `charlie/esp32/{device_id}/down`
2. 发 `hello` 到 `charlie/esp32/{device_id}/up`
3. 服务器回复 `hello`（含 AES key + UDP 地址）
4. ESP32 建 UDP → 加密 Opus 双向传输
5. 保持 MQTT 常驻，支持主动推送

### 2.3 消息格式

| 方向 | type | 字段 | 用途 |
|------|------|------|------|
| ↑ 设备→服务器 | `listen` | `state:detect`, `text:<wake_word>` | 唤醒词检测 |
| ↑ 设备→服务器 | `listen` | `state:start` | 开始录音 |
| ↑ 设备→服务器 | `listen` | `state:stop` | 停止录音（auto模式不可靠） |
| ↑ 设备→服务器 | `abort` | `session_id` | 打断播放 |
| ↓ 服务器→设备 | `tts` | `state:start/stop/sentence_start` | 播报控制 |
| ↓ 服务器→设备 | `stt` | `text:<transcript>` | 显示识别结果 |
| ↓ 服务器→设备 | `llm` | `emotion:<emoji>` | 表情切换 |
| ↓ 服务器→设备 | `mcp` | `payload:{...}` | MCP 工具调用 |
| ↓ 服务器→设备 | `notification` | `text`, `ttl` | 通知（MQTT only） |
| ↓ 服务器→设备 | `goodbye` | `session_id` | 结束对话 |
| ↓ 服务器→设备 | `system` | `command:reboot` | 重启设备 |

### 2.4 屏幕显示映射

| 消息 | 屏幕行为 |
|------|----------|
| `stt` text | `display->SetChatMessage("user", text)` |
| `tts` sentence_start | `display->SetChatMessage("assistant", text)` |
| `tts` start | `SetDeviceState(kDeviceStateSpeaking)` |
| `tts` stop | 回到 Listening/Idle |
| `llm` emotion | `display->SetEmotion(emotion_str)` |
| `notification` text | `display->ShowNotification(text, ttl)` |
| hello 成功 | 显示时间/待机界面 |

---

## 三、功能差距分析

### 3.1 已知问题

| # | 问题 | 严重程度 | 影响 |
|---|------|----------|------|
| 1 | **无 device_id/client_id 在 hello 中** | 高 | Charlie 无法识别设备身份，每次新连都生成随机 session_id |
| 2 | **MQTT endpoint 指向公网** `mqtt.xiaozhi.me` | 中 | 如果公网 broker 不可用，MQTT fallback 失效 |
| 3 | **MQTT subscribe_topic = null** | 中 | 无法接收服务器主动推送通知 |
| 4 | **MQTT publish_topic = "device-server"** | 中 | 非标准 topic 格式，与 Charlie 期望的 `charlie/esp32/{id}/up` 不符 |
| 5 | **硬编码 IP `192.168.1.3`** | 低 | IP 变化需重新烧录固件或手动改 NVS |
| 6 | **无 ping/pong 心跳** | 低 | WebSocket 连接无保活机制，可能因路由器 NAT 超时断开 |
| 7 | **WebSocket 不发送 goodbye** | 低 | 服务端只能靠 ARM_WINDOW 超时清理会话 |

### 3.2 与 Charlie 服务端对照

| Charlie 期望 | 固件现状 | 状态 |
|-------------|----------|------|
| hello 含 device_id/client_id | 无 | ❌ 需修复 |
| /xiaozhi/ota 返回 ws_url | ✅ 已支持 | ✅ |
| /ws/xiaozhi WebSocket 语音对话 | ✅ 已支持 | ✅ |
| `tts/start` → `tts/stop` 播报 | ✅ 已支持 | ✅ |
| `stt/text` 显示识别结果 | ✅ 已支持 | ✅ |
| `sentence_start/text` 显示字幕 | ✅ 已支持 | ✅ |
| `notification/text` 弹出通知 | ✅ 已支持(MQTT) | ✅ |
| `goodbye` 结束对话 | ✅ 已支持 | ✅ |
| `abort` 打断播放 | ✅ 已支持 | ✅ |
| `llm/emotion` 表情切换 | ✅ 固件支持 | ✅ |
| `ping/pong` 心跳 | ❌ 固件不支持 | ⚠️ 建议新增 |
| `listen/stop` 可靠触发 ASR | ❌ auto模式不可靠 | ⚠️ 已知限制 |

---

## 四、优化计划（v1.1.0）

### 4.1 固件端优化

#### 优化 1: Hello 消息添加 device_id

**文件**: `xz/main/protocols/websocket_protocol.cc` + `mqtt_protocol.cc`

```cpp
// GetHelloMessage() 中添加：
auto uuid = Board::GetInstance().GetUuid();
cJSON_AddStringToObject(root, "device_id", uuid.c_str());
```

**效果**: Charlie 服务端可从 hello 提取设备身份，实现设备级会话持久化。

#### 优化 2: MQTT 默认指向本地 Charlie

**文件**: `xz/main/protocols/mqtt_protocol.cc` (CHARLIE_MQTT_FALLBACK_ENDPOINT)

```cpp
// 将 fallback endpoint 改为本地
#define CHARLIE_MQTT_FALLBACK_ENDPOINT "192.168.1.12:1883"
// 或更通用：从环境变量/编译配置获取
```

**效果**: 不依赖公网 broker，完全本地化。

#### 优化 3: 添加 ping/pong 心跳

**文件**: `xz/main/protocols/websocket_protocol.cc`

```cpp
// 每 30 秒发送 ping，服务器回复 pong
esp_timer_create_args_t ping_timer_args = {
    .callback = [](void* arg) {
        auto* proto = static_cast<WebsocketProtocol*>(arg);
        proto->SendText("{\"type\":\"ping\"}");
    },
    .arg = this,
};
esp_timer_create(&ping_timer_args, &ping_timer_);
esp_timer_start_periodic(ping_timer_, 30'000'000); // 30s
```

**Charlie 服务端**: 已在 `xiaozhi_ws.py:961` 处理 `ping` → 回复 `pong`。

#### 优化 4: NVS MQTT 默认配置

烧录时默认写入：
- `mqtt/endpoint` = 空（触发 Charlie fallback）
- `mqtt/publish_topic` = `charlie/esp32/{uuid_short}/up`
- `mqtt/subscribe_topic` = `charlie/esp32/{uuid_short}/down`

### 4.2 服务端适配

Charlie 服务端（`xiaozhi_ws.py`）需增强：

```python
# hello 处理中增加 device_id 支持
if mtype == "hello":
    device_id = data.get("device_id") or data.get("client_id") or data.get("device", {})
    if isinstance(device_id, dict):
        device_id = device_id.get("device_id") or device_id.get("mac")
    # 用 device_id 替代随机 session_id 作为设备标识
```

### 4.3 构建命令

```bash
# 编译优化后的固件
export IDF_PATH=/Users/sxliuyu/esp-idf-v5.5.2
export IDF_SKIP_CHECK_SUBMODULES=1
cd /Users/sxliuyu/repos/xz

# 修改 sdkconfig 使用 LC-S3 板型
python3 -c "
import re
with open('sdkconfig', 'r') as f:
    content = f.read()
content = re.sub(r'CONFIG_BOARD_TYPE_BREAD_COMPACT_WIFI=y', '# CONFIG_BOARD_TYPE_BREAD_COMPACT_WIFI is not set', content)
if 'CONFIG_BOARD_TYPE_LC_S3_WIFI_1_54TFT=y' not in content:
    content = content.replace('# CONFIG_BOARD_TYPE_XINGZHI_ABS_2_0 is not set', 'CONFIG_BOARD_TYPE_LC_S3_WIFI_1_54TFT=y\n# CONFIG_BOARD_TYPE_XINGZHI_ABS_2_0 is not set')
with open('sdkconfig', 'w') as f:
    f.write(content)
"

# 构建
/Users/sxliuyu/.espressif/python_env/idf5.5_py3.14_env/bin/python \
  /Users/sxliuyu/esp-idf-v5.5.2/tools/idf.py build

# 烧录
/Users/sxliuyu/.espressif/python_env/idf5.5_py3.14_env/bin/python \
  /Users/sxliuyu/esp-idf-v5.5.2/tools/idf.py -p /dev/tty.usbmodem101 flash
```

---

## 五、验证清单（v1.1.0 烧录后）

```bash
python3 << 'EOF'
import serial, time, subprocess, sys

port = "/dev/tty.usbmodem101"
subprocess.run(['python3', '-m', 'esptool', '--chip', 'esp32s3', 
                '--port', port, '--before', 'default_reset', 
                '--after', 'hard_reset', 'read_mac'], capture_output=True)

ser = serial.Serial(port, 115200, timeout=1)
time.sleep(1)
output = b''
start = time.time()
while time.time() - start < 15:
    if ser.in_waiting:
        output += ser.read(ser.in_waiting)
ser.close()

text = output.decode('utf-8', errors='replace')

checks = {
    "Board SKU": "SKU=lc-s3-wifi-1.54tft" in text,
    "Display on": "Turning display on" in text,
    "WiFi connected": "Connected to WiFi" in text,
    "WebSocket connected": "websocket" in text.lower() and ("connected" in text.lower() or "established" in text.lower()),
    "UUID present": "909b14d1" in text or "UUID=" in text,
}

all_pass = True
for name, passed in checks.items():
    status = '✅' if passed else '❌'
    print(f"  {status} {name}")
    if not passed:
        all_pass = False

if all_pass:
    print("\n🎉 所有检查通过！")
else:
    print("\n⚠️ 部分检查未通过，请查看串口日志")
EOF
```

---

## 六、故障排除

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 屏幕不亮 | 板型选错（xingzhi-cube vs lc-s3） | 确认 `CONFIG_BOARD_TYPE_LC_S3_WIFI_1_54TFT=y` |
| WebSocket 连不上 | IP 别名未设置 | 执行 `sudo ifconfig en1 alias 192.168.1.3` |
| MQTT 连不上 | endpoint 指向公网 broker | 清空 NVS mqtt/endpoint，触发 Charlie fallback |
| 设备无法识别 | hello 无 device_id | 需编译 v1.1.0 固件 |
| I2C 错误 | ES8311 软失败 | 正常现象，不影响功能 |
| 重启循环 | sdkconfig 被重置 | 恢复 NVS 配置或重新烧录 |

---

## 七、历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-08-14 | 初始固件（从原厂 patch） |
| v1.1.0 | 待定 | 优化: device_id、ping/pong、本地 MQTT |

---

## 八、参考

- Charlie 服务端: https://github.com/SxLiuYu/charlie-voice-assistant
- xz 固件源码: `/Users/sxliuyu/repos/xz` (xiaozhi-esp32)
- Charlie ESP32 固件仓库: https://github.com/SxLiuYu/charlie-esp32
