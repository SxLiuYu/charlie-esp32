# Charlie ESP32 固件

## 最终版本（当前使用）

**文件**: `flash_16MB_local.bin` (16MB 全量flash镜像)

| 属性 | 值 |
|------|-----|
| 固件版本 | xiaozhi v2.1.0 |
| 编译时间 | 2026-01-30 |
| ESP-IDF | v5.5.1 |
| 板子 | lc-s3-wifi-1.54tft (LC-S3 1.54寸 TFT WiFi) |
| Flash大小 | 16MB |
| OTA URL | `http://192.168.1.3:8000/xiaozhi/ota` |
| WS URL | `ws://192.168.1.3:8000/ws/xiaozhi` |
| WiFi | CMCC-egTm / fneme97c (硬编码在NVS) |
| 屏幕 | ST7789 240x240 SPI, 1.54寸 TFT (亮✅) |

> ⚠️ **此版本是最终版本，不要再重新编译烧录。** xz项目用xingzhi-cube板子编译的固件屏幕不亮（显示引脚不同）。这个版本是从ESP32原厂固件patch而来，直接修改OTA/WS地址指向Charlie本地服务。

## 烧录命令

```bash
# 前置：安装esptool
# pip install esptool

# 烧录（全量16MB，会覆盖所有分区）
python3 -m esptool --chip esp32s3 \
  -p /dev/cu.usbmodem101 \
  -b 115200 \
  --before=default_reset \
  --after=hard_reset \
  write_flash \
  --flash_mode dio \
  --flash_freq 80m \
  --flash_size 16MB \
  0x0 firmware/flash_16MB_local.bin
```

## Mac端配套设置（每次重启后执行）

固件里OTA地址是 `192.168.1.3`，但Mac的实际IP是 `192.168.1.12`。需要给Mac加IP别名：

```bash
#!/bin/bash
# esp32-alias.sh — 给Mac加192.168.1.3别名
# 用法: sudo bash scripts/esp32-alias.sh

IFACE=$(route get default 2>/dev/null | grep interface | head -1 | awk '{print $2}')
if [ -z "$IFACE" ]; then
  IFACE="en1"
fi

# 删除旧别名（如果存在）
sudo ifconfig $IFACE delete 192.168.1.3 2>/dev/null

# 添加IP别名
sudo ifconfig $IFACE alias 192.168.1.3 255.255.255.0

# 修复路由（让192.168.1.3指向本地）
sudo route delete 192.168.1.3 2>/dev/null
sudo route add -host 192.168.1.3 -interface lo0

# 验证
curl -s --connect-timeout 3 http://192.168.1.3:8000/health && echo "✅ 192.168.1.3 可达" || echo "❌ 不可达"
```

## 分区布局

| 分区 | 偏移 | 大小 | 说明 |
|------|------|------|------|
| nvs | 0x9000 | 16KB | WiFi配置、设备参数 |
| otadata | 0xD000 | 8KB | OTA状态 |
| phy_init | 0xF000 | 4KB | 射频校准 |
| ota_0 | 0x20000 | 4032KB | 固件镜像（有效） |
| ota_1 | 0x410000 | 4032KB | 备用分区（空） |
| assets | 0x800000 | 8MB | 字体/表情/语音模型 |

## 历史

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-01-30 | v2.1.0 | 原厂固件，从tenclass.net OTA获取 |
| 2026-06-13 | - | 从ESP32完整备份flash到 `flash_16MB.bin` |
| 2026-06-13 | - | patch OTA/WS地址为 `192.168.1.3`（`flash_16MB_local.bin`） |
| 2026-08-11 | - | 尝试用xz项目编译xingzhi-cube固件 → **屏幕不亮**（引脚不匹配） |
| 2026-08-11 | - | 恢复 `flash_16MB_local.bin` → **屏幕亮，最终版本** |

## 注意事项

1. **不要用xz项目重新编译** — xingzhi-cube-1.54tft-wifi板子的显示引脚与lc-s3不同
2. **不要擦除flash** — `erase_flash` 会清掉NVS里的WiFi配置和phy_init
3. **OTA自动升级已禁用** — OTA地址指向本地Charlie服务，不会从tenclass.net升级
4. **IP别名必须设置** — 没有别名ESP32连不上Charlie服务
5. **Mac静态IP** — 已设为 `192.168.1.12`（固定不变），ESP32通过 `192.168.1.3` 别名访问

---

# ESP32 固件完整规范（来自 charlie-voice-assistant 项目）

> 来源: https://github.com/SxLiuYu/charlie-voice-assistant  
> 最后更新: 2026-08-14

## 一、硬件规格

| 参数 | 值 |
|------|-----|
| 芯片 | ESP32-S3 |
| 开发板 | LC-S3 WiFi 1.54" TFT |
| USB 芯片 | CH343 (串口: `/dev/tty.usbmodem101`) |
| 显示屏 | ST7789, 240x240 彩色 TFT |
| Flash | 16MB |
| Flash 模式 | DIO |
| Flash 频率 | 80MHz |
| 源码仓库 | `/Users/sxliuyu/repos/xz` (xiaozhi-esp32) |

### 引脚分配

```
显示 SPI:    SDA=GPIO3, SCL=GPIO4, DC=GPIO5, CS=GPIO6, RES=GPIO7
背光:        GPIO2 (active-high)
I2S 音频:    MCLK=14, WS=11, BCLK=13, DIN=12, DOUT=10
I2C:         SDA=9, SCL=8
按键:        BOOT=GPIO0, VOL_UP=42, VOL_DOWN=41
LED:         GPIO1
红外发射:    GPIO39, 38KHz
```

### config.h 完整定义

```c
// 音频
#define AUDIO_INPUT_SAMPLE_RATE  16000
#define AUDIO_OUTPUT_SAMPLE_RATE 16000
#define AUDIO_I2S_GPIO_MCLK  GPIO_NUM_14
#define AUDIO_I2S_GPIO_WS    GPIO_NUM_11
#define AUDIO_I2S_GPIO_BCLK  GPIO_NUM_13
#define AUDIO_I2S_GPIO_DIN   GPIO_NUM_12
#define AUDIO_I2S_GPIO_DOUT  GPIO_NUM_10

// I2C 音频编解码器 ES8311
#define AUDIO_CODEC_I2C_SDA_PIN  GPIO_NUM_9
#define AUDIO_CODEC_I2C_SCL_PIN  GPIO_NUM_8
#define AUDIO_CODEC_ES8311_ADDR  ES8311_CODEC_DEFAULT_ADDR
#define AUDIO_CODEC_PA_PIN       GPIO_NUM_21

// 显示屏
#define DISPLAY_WIDTH   240
#define DISPLAY_HEIGHT  240
#define DISPLAY_MIRROR_X false
#define DISPLAY_MIRROR_Y false
#define DISPLAY_SWAP_XY false
#define DISPLAY_OFFSET_X  0
#define DISPLAY_OFFSET_Y  0
#define DISPLAY_SDA GPIO_NUM_3
#define DISPLAY_SCL GPIO_NUM_4
#define DISPLAY_DC  GPIO_NUM_5
#define DISPLAY_CS  GPIO_NUM_6
#define DISPLAY_RES GPIO_NUM_7
#define DISPLAY_BACKLIGHT_PIN GPIO_NUM_2
#define DISPLAY_BACKLIGHT_OUTPUT_INVERT false
#define BACKLIGHT_INVERT false

// 按键 / LED
#define BUILTIN_LED_GPIO        GPIO_NUM_1
#define BOOT_BUTTON_GPIO        GPIO_NUM_0
#define VOLUME_UP_BUTTON_GPIO   GPIO_NUM_42
#define VOLUME_DOWN_BUTTON_GPIO GPIO_NUM_41

// 红外
#define IR_LED_GPIO          GPIO_NUM_39
#define IR_CARRIER_FREQ_HZ   38000
```

---

## 二、通信协议

### WebSocket (主通道)

- **URL**: `ws://<Charlie_IP>:8000/ws/xiaozhi`
- **上行音频**: 16kHz Opus, 60ms 帧
- **下行音频**: 24kHz Opus (TTS)
- **端点检测**: Silero VAD, 尾静音 0.48s (8帧)
- **对话窗口**: 唤醒后 30s ARM_WINDOW

### MQTT (信令通道，可选)

| 方向 | Topic | 说明 |
|------|-------|------|
| ESP32 → Charlie | `charlie/esp32/{device_id}/up` | 设备上报 |
| Charlie → ESP32 | `charlie/esp32/{device_id}/down` | 服务器推送 |
| Wake 摇醒 | `charlie/esp32/{device_id}/wake` | MQTT 唤醒 idle 设备 |

**MQTT 消息格式**:
```json
// TTS 播报
{"type": "tts", "state": "start"}
// 文字通知
{"type": "notification", "text": "您有一条新消息", "ttl": 5000}
// STT 识别结果
{"type": "stt", "text": "..."}
```

**环境变量**:
- `MQTT_BROKER` — broker 地址
- `MQTT_PORT` — 默认 1883
- `MQTT_USER` / `MQTT_PASSWORD` — 认证
- `MQTT_DEVICE_ID` — 默认 `esp32-default`
- `MQTT_ENABLE_OTA` — 默认 0（OTA 响应中是否返回 mqtt 段）

---

## 三、编译环境

### 必需工具链

| 工具 | 路径 / 版本 |
|------|------------|
| ESP-IDF | v5.5.2 (`/Users/sxliuyu/esp-idf-v5.5.2`) |
| Python | `/Users/sxliuyu/.espressif/python_env/idf5.5_py3.14_env/bin/python` |
| xz 源码 | `/Users/sxliuyu/repos/xz` (xiaozhi-esp32) |

### 构建命令

```bash
export IDF_PATH=/Users/sxliuyu/esp-idf-v5.5.2
export IDF_SKIP_CHECK_SUBMODULES=1

cd /Users/sxliuyu/repos/xz

# 一步完成 构建+烧录
/Users/sxliuyu/.espressif/python_env/idf5.5_py3.14_env/bin/python \
  /Users/sxliuyu/esp-idf-v5.5.2/tools/idf.py \
  -p /dev/tty.usbmodem101 build flash
```

### sdkconfig 关键配置

```bash
# 切换到 LC-S3 板型
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

# 设置 OTA URL (本地 Charlie 服务器)
sed -i '' 's|CONFIG_OTA_URL="https://api.tenclass.net/xiaozhi/ota/"|CONFIG_OTA_URL="http://192.168.1.12:8000/xiaozhi/ota"|' sdkconfig
```

---

## 四、配网方式（AP 热点门户）

出厂固件已擦除 NVS，开机无 WiFi 时自动进入 AP 热点模式：

1. 手机连接热点 `lc-s3-wifi-1.54tft-XXXX`（`XXXX` = MAC 后四位，无密码）
2. 浏览器访问 `http://192.168.4.1`
3. 选择家用 WiFi，输入密码
4. 高级设置 → OTA URL 填入 `http://<Charlie_IP>:8000/xiaozhi/ota`
5. 保存后设备重启，屏幕显示时间即成功

> 长按复位键可重新进入热点配网模式。

---

## 五、已知问题与修复

### ES8311 I2C 通信失败

**现象**: 启动日志 `I2C_If: Fail to write to dev 30`  
**原因**: ES8311 音频编解码器 I2C 地址 0x30 无响应  
**处理**: 已软失败，不影响基本功能。June 13 备份固件已包含修复。

### sdkconfig 被重置

**现象**: 编译后 board type 变回 `BREAD_COMPACT_WIFI`  
**原因**: `idf.py set-target` 或 `fullclean` 可能删除 sdkconfig  
**处理**: 用上方 Python 脚本恢复配置

### 屏幕不亮

**现象**: 编译 xingzhi-cube 固件后屏幕不亮  
**原因**: 引脚映射不同（SPI 在 GPIO10/9/8/14/18 vs GPIO3/4/5/6/7）  
**处理**: 务必使用 `CONFIG_BOARD_TYPE_LC_S3_WIFI_1_54TFT=y`

### 重启循环

**现象**: 多次 `entry 0x403c8908`  
**处理**: 恢复 June 13 备份固件

---

## 六、验证清单

烧录后用以下脚本验证：

```bash
python3 << 'EOF'
import serial, time, subprocess

subprocess.run(['python3', '-m', 'esptool', '--chip', 'esp32s3', 
                '--port', '/dev/tty.usbmodem101', 
                '--before', 'default_reset', '--after', 'hard_reset', 'read_mac'], 
               capture_output=True)

ser = serial.Serial('/dev/tty.usbmodem101', 115200, timeout=1)
time.sleep(0.3)

output = b''
start = time.time()
while time.time() - start < 8:
    if ser.in_waiting:
        data = ser.read(ser.in_waiting)
        output += data
ser.close()

text = output.decode('utf-8', errors='replace')

checks = {
    "Board SKU": "SKU=lc-s3-wifi-1.54tft" in text,
    "Display on": "Turning display on" in text,
    "LVGL init": "LVGL" in text,
    "Backlight": "brightness" in text.lower(),
    "WiFi connected": "Connected to WiFi" in text,
    "MQTT connected": "MQTT" in text and "Connected" in text,
}

for name, passed in checks.items():
    print(f"  {'✅' if passed else '❌'} {name}")
EOF
```

期望输出（Charlie 定制固件）：
```
✅ Board SKU
✅ Display on
✅ LVGL init
✅ Backlight
✅ WiFi connected
✅ MQTT connected
```

---

## 七、Charlie 服务端适配

ESP32 固件兼容 xiaozhi 协议 v2.1.0，Charlie 服务端实现见：

| 文件 | 功能 |
|------|------|
| `src/app/xiaozhi_ws.py` | WebSocket 端点，Opus 流式处理 |
| `src/app/mqtt_server.py` | MQTT broker 封装，主动推送 |
| `src/app/mqtt_push.py` | MQTT 消息发送 |
| `src/app/xiaozhi_codec.py` | Opus 编解码工具 |

### 性能指标

| 指标 | 数值 |
|------|------|
| 说完→首句 | ~1.16s |
| 端到端 | ~2.23s |
| ASR (SenseVoice 本地) | 26ms |
| ASR (百度降级) | 327ms |
| TTS (百度) | 119ms |

---

## 八、故障排除速查表

| 问题 | 解决方案 |
|------|----------|
| esptool 连不上 | 按住 BOOT 键 → 插 USB → 等 1 秒 → 松开 BOOT → 烧录 |
| 屏幕不亮 | 检查背光 GPIO2，确认 `"Turning display on"` 日志 |
| I2C 错误 | 正常现象，ES8311 软失败处理已启用 |
| WiFi 连不上 | 检查 sdkconfig 中 WiFi 密码 |
| MQTT 连不上 | 确认 Charlie 服务器 MQTT broker 在运行 |
| 推送不显示 | 检查 `subscribe_topic` 是否正确 |
| OTA 报错 | 确认 Charlie 服务器 `/xiaozhi/ota` 端点可访问 |
| 重启循环 | 恢复 June 13 备份固件 |
