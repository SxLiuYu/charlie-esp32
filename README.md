# Charlie ESP32 固件

## 固件版本

| 属性 | 值 |
|------|-----|
| 固件版本 | v1.0.0 (xiaozhi v2.1.0) |
| 编译基础 | ESP-IDF v5.5.1 |
| 板型 | lc-s3-wifi-1.54tft (LC-S3 1.54寸 TFT WiFi) |
| 芯片 | ESP32-S3 |
| Flash | 16MB DIO 80MHz |
| UUID | `909b14d1-850c-4e16-80bf-04916553597c` |

## 文件

| 文件 | 说明 |
|------|------|
| `flash_16MB_local.bin` | 16MB 全量 flash 镜像（含 NVS 配置） |
| `README.md` | 烧录和使用说明 |
| `FIRMWARE_SPEC.md` | 固件完整规格与优化文档 |

---

## NVS 配置（实际内容）

### WiFi
| Key | Value |
|-----|-------|
| `wifi/ssid` | `CMCC-egTm` |
| `wifi/password` | `fneme97c` |
| `wifi/ssid1` | `-5!LCTECH-02` |
| `wifi/password1` | `1234567890abc` |

### WebSocket
| Key | Value |
|-----|-------|
| `websocket/url` | `ws://192.168.1.3:8000/ws/xiaozhi` |
| `websocket/token` | `test-token` |

### MQTT (fallback)
| Key | Value |
|-----|-------|
| `mqtt/endpoint` | `mqtt.xiaozhi.me` ⚠️ 公网地址 |
| `mqtt/client_id` | `GID_test@@@14_c1_9f_3a_9a_88@@@909b14d1-...` |
| `mqtt/publish_topic` | `device-server` ⚠️ 非标准 |
| `mqtt/subscribe_topic` | `null` ⚠️ 未配置 |

> ⚠️ **注意**: MQTT 配置指向公网 broker，如需使用 MQTT 推送功能，需重新烧录或手动修改 NVS。

---

## 烧录命令

```bash
python3 -m esptool --chip esp32s3 \
  -p /dev/cu.usbmodem101 -b 115200 \
  --before=default_reset --after=hard_reset \
  write_flash \
  --flash_mode dio --flash_freq 80m --flash_size 16MB \
  0x0 flash_16MB_local.bin
```

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

## 分区布局

| 分区 | 偏移 | 大小 | 说明 |
|------|------|------|------|
| nvs | 0x9000 | 16KB | WiFi/MQTT/设备参数 |
| otadata | 0xD000 | 8KB | OTA 状态 |
| phy_init | 0xF000 | 4KB | 射频校准 |
| ota_0 | 0x20000 | 4MB | 当前固件 |
| ota_1 | 0x410000 | 4MB | 备用分区 |
| assets | 0x800000 | 8MB | 字体/ASR模型/表情 |

---

## 通信协议

### WebSocket（默认）
- 固件 → 服务器：hello (含设备能力) → 持续 60ms Opus 音频流
- 服务器 → 固件：hello (含 session) → tts/stt/llm/notification/goodbye

### MQTT（备选，需 OTA 切换）
- Topic 格式：`charlie/esp32/{device_id}/{up,down}`
- UDP 音频（AES-CTR 加密）
- 支持主动推送通知

### 消息类型
| 方向 | type | 字段 |
|------|------|------|
| ↑ | `listen` | `state:detect/start/stop`, `text:<wake_word>` |
| ↑ | `abort` | `session_id` |
| ↓ | `tts` | `state:start/stop/sentence_start`, `text` |
| ↓ | `stt` | `text:<transcript>` |
| ↓ | `llm` | `emotion:<emoji>` |
| ↓ | `notification` | `text`, `ttl` |
| ↓ | `goodbye` | `session_id` |

---

## 注意事项

1. **IP 别名必须设置** — `192.168.1.3` 是固件硬编码的地址
2. **不要用 xingzhi-cube 板型编译** — 引脚不兼容，屏幕不亮
3. **不要 erase_flash** — 会清除 NVS 中的 WiFi 和服务器配置
4. **MQTT 为备选通道** — 默认走 WebSocket，MQTT fallback 指向公网 broker

## 优化计划

详见 [FIRMWARE_SPEC.md](FIRMWARE_SPEC.md) — v1.1.0 计划添加 device_id 识别、ping/pong 心跳、本地 MQTT。
