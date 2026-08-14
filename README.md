# Charlie ESP32 固件

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-08-14 | 初始固件（从原厂 patch） |
| **v1.1.0** | **2026-08-14** | **优化版：device_id、ping/pong、goodbye、MQTT fallback** |

---

## v1.1.0 固件

**文件**: `flash_16MB_v1.1.0.bin` (16MB 全量 flash 镜像)

| 属性 | 值 |
|------|-----|
| 固件版本 | xiaozhi v2.1.0 (优化版) |
| ESP-IDF | v5.5.1 |
| 板型 | lc-s3-wifi-1.54tft |
| UUID | `909b14d1-...` |
| NVS WiFi | `CMCC-egTm` / `fneme97c` ✅ |
| NVS WebSocket | `ws://192.168.1.3:8000/ws/xiaozhi` ✅ |
| NVS MQTT | **已清空** → 自动使用 Charlie fallback ✅ |
| 屏幕 | ST7789 240x240 SPI ✅ |

### v1.1.0 改进内容

| # | 改进 | 说明 |
|---|------|------|
| 1 | **hello 含 device_id** | UUID 加入 hello JSON，Charlie 可跨重连识别设备 |
| 2 | **ping/pong 心跳** | 每 30s 发送 ping，防止 NAT 超时断开 |
| 3 | **goodbye 消息** | WebSocket 关闭时发送 goodbye，服务端及时清理会话 |
| 4 | **MQTT 本地化** | NVS 清空旧配置，固件自动使用 `192.168.1.12:1883` fallback |

---

## 烧录（macOS 重要：ESP32-S3 原生 USB）

> ⚠️ **LC-S3 使用 ESP32-S3 原生 USB，macOS 上必须手动进入下载模式！**

### 方法一：命令行烧录（需手动操作）

```bash
# 第 1 步：按住板子上的 BOOT 按钮不放
# 第 2 步：插入 USB 数据线（或重新插入）
# 第 3 步：等待 1 秒后松开 BOOT 按钮
# 第 4 步：立即执行以下命令：

python3 -m esptool --chip esp32s3 \
  --port /dev/cu.usbmodem101 \
  --before=default-reset --after=hard-reset \
  write-flash \
  --flash-mode dio --flash-size 16MB --flash-freq 80m \
  0x0 flash_16MB_v1.1.0.bin
```

### 方法二：自动脚本（自动检测下载模式窗口）

```bash
# 使用 idf.py（对原生 USB 支持更好）
export IDF_PATH=/Users/sxliuyu/esp-idf-v5.5.2
export IDF_SKIP_CHECK_SUBMODULES=1
cd /Users/sxliuyu/repos/xz

# 先编译
/Users/sxliuyu/.espressif/python_env/idf5.5_py3.14_env/bin/python \
  /Users/sxliuyu/esp-idf-v5.5.2/tools/idf.py build

# 然后按方法一的步骤，在 idf.py flash 前按住 BOOT
/Users/sxliuyu/.espressif/python_env/idf5.5_py3.14_env/bin/python \
  /Users/sxliuyu/esp-idf-v5.5.2/tools/idf.py \
  -p /dev/cu.usbmodem101 \
  flash
```

### 方法三：Charlie 应用内烧录（推荐）

1. 启动 Charlie 应用
2. 打开「ESP32 配置向导」（`http://localhost:8000/esp32-setup`）
3. 点「检测串口」→ 选择 `/dev/cu.usbmodem101`
4. 点「开始烧录」→ 按提示操作（按住 BOOT → 插 USB → 松开）

---

## Mac 端 IP 别名（每次重启后执行）

```bash
IFACE=$(route get default 2>/dev/null | grep interface | head -1 | awk '{print $2}')
[ -z "$IFACE" ] && IFACE="en1"
sudo ifconfig $IFACE delete 192.168.1.3 2>/dev/null
sudo ifconfig $IFACE alias 192.168.1.3 255.255.255.0
sudo route delete 192.168.1.3 2>/dev/null
sudo route add -host 192.168.1.3 -interface lo0
```

---

## 验证（烧录后串口日志）

```
I SKU=lc-s3-wifi-1.54tft
I UUID=909b14d1-850c-4e16-80bf-04916553597c
I Connecting to websocket server: ws://192.168.1.3:8000/ws/xiaozhi with version: 1
I Ping timer started (interval=30s)    ← 新增
I Session ID: xxx
>> <STT text>                          ← 识别结果显示在屏幕
<< <TTS text>                          ← TTS 字幕显示
I Sent goodbye, session_id=xxx         ← 新增（对话结束时）
```

---

## 分区布局

| 分区 | 偏移 | 大小 | 说明 |
|------|------|------|------|
| bootloader | 0x0000 | 32KB | ESP-IDF bootloader |
| nvs | 0x9000 | 16KB | WiFi/WebSocket/设备参数 |
| otadata | 0xD000 | 8KB | OTA 切换标志 |
| phy_init | 0xF000 | 4KB | 射频校准 |
| ota_0 | 0x20000 | 4MB | 当前固件 |
| ota_1 | 0x410000 | 4MB | 备用分区 |
| assets | 0x800000 | 8MB | 字体/SenseVoice 模型/表情 |

---

## 通信协议

### WebSocket（默认）
- **URL**: `ws://<IP>:8000/ws/xiaozhi`
- **Hello**: 含 `device_id`（UUID），用于设备级会话持久化
- **心跳**: 每 30s ping，服务器回复 pong
- **关闭**: 发送 goodbye + session_id

### MQTT（备选，OTA 切换）
- 固件 NVS 无 MQTT 配置时自动使用 Charlie fallback
- **Endpoint**: `192.168.1.12:1883`（本地 Charlie MQTT broker）
- **Topics**: `charlie/esp32/{uuid_short}/up` + `/down`
- **音频**: UDP AES-CTR 加密 Opus

---

## macOS 烧录故障排查

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `Failed to connect` | ESP32-S3 原生 USB 未进入下载模式 | **按住 BOOT 按钮 → 插 USB → 等 1 秒 → 松开 → 立即烧录** |
| `No serial ports found` | 驱动问题 | `brew install wch-ch34x-usb-serial-driver` 后重启 |
| 端口不存在 | USB 接触不良 | 换数据线（确保是数据线非充电线） |
| 烧录后屏幕不亮 | 板型不匹配 | 确认使用 `lc-s3-wifi-1.54tft` 编译的固件 |
| 连不上 Charlie | IP 别名未设置 | 执行上面的 IP 别名脚本 |

---

## 源码修改（v1.1.0）

修改文件在 `/Users/sxliuyu/repos/xz`（xiaozhi-esp32 仓库）：

| 文件 | 改动 |
|------|------|
| `main/protocols/websocket_protocol.h` | 新增 `esp_timer.h`、`ping_timer_`、`StartPingTimer/StopPingTimer` |
| `main/protocols/websocket_protocol.cc` | hello 添加 `device_id`、30s ping 心跳、goodbye 消息 |
| `main/protocols/mqtt_protocol.cc` | hello 添加 `device_id` |

---

## 注意事项

1. **IP 别名必须设置** — `192.168.1.3` 是 WebSocket URL 硬编码地址
2. **不要 erase_flash** — 会清掉 WiFi 配置
3. **MQTT fallback 优先** — NVS 清空后固件自动连接本地 Charlie
4. **v1.0.0 → v1.1.0 升级** — 直接烧录全量镜像即可

---

## 参考

- Charlie 服务端: https://github.com/SxLiuYu/charlie-voice-assistant
- xz 固件源码: `/Users/sxliuyu/repos/xz` (xiaozhi-esp32)
- 固件规格详情: [FIRMWARE_SPEC.md](FIRMWARE_SPEC.md)
