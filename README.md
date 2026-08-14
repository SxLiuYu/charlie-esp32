# Charlie ESP32 固件

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-08-14 | 初始固件（从原厂 patch，硬编码 IP/MQTT） |
| **v1.1.0** | **2026-08-14** | **优化版：device_id、ping/pong、goodbye、MQTT fallback 本地化** |

---

## v1.1.0 固件

**文件**: `flash_16MB_v1.1.0.bin` (16MB 全量 flash 镜像)

| 属性 | 值 |
|------|-----|
| 固件版本 | xiaozhi v2.1.0 (优化版) |
| ESP-IDF | v5.5.1 |
| 板型 | lc-s3-wifi-1.54tft |
| NVS WiFi | `CMCC-egTm` / `fneme97c` ✅ |
| NVS WebSocket | `ws://192.168.1.3:8000/ws/xiaozhi` ✅ |
| NVS MQTT | **已清空** → 自动使用 Charlie fallback ✅ |
| UUID | `909b14d1-...` ✅ |
| 屏幕 | ST7789 240x240 SPI ✅ |

### v1.1.0 改进内容

| # | 改进 | 说明 |
|---|------|------|
| 1 | **hello 含 device_id** | UUID 加入 hello JSON，Charlie 可跨重连识别设备 |
| 2 | **ping/pong 心跳** | 每 30s 发送 ping，防止 NAT 超时断开 |
| 3 | **goodbye 消息** | WebSocket 关闭时发送 goodbye，服务端及时清理会话 |
| 4 | **MQTT 本地化** | NVS 中清空旧 MQTT 配置，固件自动使用 `192.168.1.12:1883` fallback |

---

## 烧录 v1.1.0

```bash
# 方法一：应用内烧录向导（推荐）
# 启动 Charlie → 访问 http://localhost:8000/esp32-setup → 点「开始烧录」

# 方法二：命令行烧录（全量 16MB）
python3 -m esptool --chip esp32s3 \
  -p /dev/cu.usbmodem101 -b 115200 \
  --before=default_reset --after=hard_reset \
  write_flash \
  --flash_mode dio --flash_freq 80m --flash_size 16MB \
  0x0 flash_16MB_v1.1.0.bin
```

### Mac 端 IP 别名（每次重启后执行）

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

## 从源码重新编译

```bash
export IDF_PATH=/Users/sxliuyu/esp-idf-v5.5.2
export IDF_SKIP_CHECK_SUBMODULES=1
cd /Users/sxliuyu/repos/xz

# 构建（sdkconfig 已配置为 LC-S3 板型）
/Users/sxliuyu/.espressif/python_env/idf5.5_py3.14_env/bin/python \
  /Users/sxliuyu/esp-idf-v5.5.2/tools/idf.py build

# 打包全量镜像（含 NVS 清理）
python3 ../charlie-esp32/scripts/clean_nvs_mqtt.py \
  flash_16MB_local.bin flash_16MB_v1.1.0_clean.bin

python3 << 'EOF'
import struct
# 合并 bootloader + partition table + cleaned NVS + app + assets
with open('build/bootloader/bootloader.bin','rb') as f: bt=f.read()
with open('build/partition_table/partition-table.bin','rb') as f: pt=f.read()
with open('build/ota_data_initial.bin','rb') as f: od=f.read()
with open('build/xiaozhi.bin','rb') as f: app=f.read()
with open('flash_16MB_v1.1.0_clean.bin','rb') as f: orig=f.read()
img=bytearray(16*1024*1024)
img[0:len(bt)]=bt
img[0x8000:0x8000+len(pt)]=pt
img[0x9000:0x9000+0x4000]=orig[0x9000:0xD000]
img[0xD000:0xD000+len(od)]=od
img[0xF000:0xF000+0x1000]=orig[0xF000:0x10000]
img[0x20000:0x20000+len(app)]=app
img[0x800000:0x800000+0x800000]=orig[0x800000:]
open('flash_16MB_v1.1.0.bin','wb').write(img)
print('✅ flash_16MB_v1.1.0.bin created')
EOF
```

---

## 分区布局

| 分区 | 偏移 | 大小 | 说明 |
|------|------|------|------|
| bootloader | 0x0000 | 32KB | ESP-IDF bootloader |
| nvs | 0x9000 | 16KB | WiFi/WebSocket/设备参数（v1.1.0 已清空 MQTT） |
| otadata | 0xD000 | 8KB | OTA 切换标志 |
| phy_init | 0xF000 | 4KB | 射频校准 |
| ota_0 | 0x20000 | 4MB | 当前固件 |
| ota_1 | 0x410000 | 4MB | 备用分区 |
| assets | 0x800000 | 8MB | 字体/SenseVoice 模型/表情 |

---

## 通信协议（v1.1.0）

### WebSocket 默认通道
- **URL**: `ws://<IP>:8000/ws/xiaozhi`
- **Hello**: 含 `device_id`（UUID），用于设备级会话持久化
- **心跳**: 每 30s ping，服务器回复 pong
- **关闭**: 发送 goodbye + session_id

### MQTT 备选通道（OTA 切换）
- 固件 NVS 无 MQTT 配置时自动使用 Charlie fallback
- **Endpoint**: `192.168.1.12:1883`（本地 Charlie MQTT broker）
- **Topics**: `charlie/esp32/{uuid_short}/up` + `/down`
- **音频**: UDP AES-CTR 加密 Opus

---

## 注意事项

1. **IP 别名必须设置** — `192.168.1.3` 是 WebSocket URL 硬编码地址
2. **不要 erase_flash** — 会清掉 WiFi 配置
3. **MQTT fallback 优先** — NVS 清空后固件自动连接本地 Charlie
4. **v1.0.0 → v1.1.0 升级** — 直接烧录全量镜像即可
