# LC-S3 WiFi 1.54" TFT 固件深度分析报告

**分析对象**: `flash_16MB_original.bin` (6月13日购买时自带固件)  
**报告日期**: 2026-08-16  
**分析工具**: esptool v5.3.1, strings, 二进制 diff

---

## 一、硬件参数

### 1.1 主控芯片

| 项目 | 值 |
|------|------|
| 芯片型号 | ESP32-S3 (QFN56 封装) |
| 芯片版本 | v0.2 |
| MAC 地址 | 14:c1:9f:3a:9a:88 |
| CPU 架构 | Xtensa LX7 双核 + LP 核心 |
| 主频 | 240 MHz |
| 晶振频率 | 40 MHz |
| 功能 | Wi-Fi, BT 5 (LE), Dual Core + LP Core |
| USB 模式 | USB-Serial/JTAG (原生, 无外部 CH340) |
| 最小芯片版本 | v0.0 |
| 最大芯片版本 | v0.99 |

### 1.2 存储配置

| 项目 | 值 |
|------|------|
| Flash 容量 | 16 MB |
| Flash 厂商 | GigaDevice (ID: 0xC8) |
| Flash 型号 | GD25Q128 (Device: 0x4018) |
| Flash 类型 | Quad SPI (eFuse 设置) |
| Flash 电压 | 3.3V |
| Flash 频率 | 80 MHz |
| Flash 模式 | DIO |
| WP pin | 0xEE (disabled) |
| PSRAM 容量 | 8 MB (嵌入式) |
| PSRAM 类型 | AP_3v3 |
| PSRAM 模式 | Octal SPI |

### 1.3 外设引脚分配 (从固件和 config.h 提取)

| 功能 | GPIO | 说明 |
|------|------|------|
| **显示屏** | | |
| Display MOSI (SDA) | GPIO3 | SPI 数据 |
| Display SCL | GPIO4 | SPI 时钟 |
| Display DC | GPIO5 | 数据/命令选择 |
| Display CS | GPIO6 | 片选 |
| Display RES | GPIO7 | 复位 |
| Display Backlight | GPIO2 | PWM 调光 |
| **音频** | | |
| I2S MCLK | GPIO14 | 主时钟 |
| I2S WS | GPIO11 | 字选择 |
| I2S BCLK | GPIO13 | 位时钟 |
| I2S DIN | GPIO12 | 数据输入 (麦克风) |
| I2S DOUT | GPIO10 | 数据输出 (扬声器) |
| Codec I2C SDA | GPIO9 | ES8311 控制 |
| Codec I2C SCL | GPIO8 | ES8311 控制 |
| Codec PA Pin | GPIO21 | 功放使能 |
| **按键** | | |
| Boot Button | GPIO0 | BOOT 键 |
| Built-in LED | GPIO1 | 指示灯 |
| Volume Up | GPIO42 | 音量+ |
| Volume Down | GPIO41 | 音量- |
| **电源管理** | | |
| PowerManager ADC | GPIO38 | 电池电量检测 |

### 1.4 显示屏参数

| 项目 | 值 |
|------|------|
| 驱动 IC | ST7789 |
| 分辨率 | 240 x 240 |
| 接口 | SPI (SPI3_HOST, DMA) |
| 颜色格式 | RGB565 (16-bit) |
| 偏移 | X=0, Y=0 |
| 镜像 | X=false, Y=false |
| 交换XY | false |
| 背光 | PWM (LEDC), 可调亮度 |

### 1.5 音频参数

| 项目 | 值 |
|------|------|
| 编解码器 | ES8311 |
| 接口 | I2C (控制) + I2S (数据) |
| I2C 地址 | ES8311_CODEC_DEFAULT_ADDR (0x18) |
| 输入采样率 | 16000 Hz |
| 输出采样率 | 16000 Hz |
| MCLK 使用 | 是 |
| 音频编码 | Opus (编码/解码) |
| PA 使能引脚 | GPIO21 |

---

## 二、固件结构

### 2.1 固件基本信息

| 项目 | 值 |
|------|------|
| 项目名称 | xiaozhi (小智 AI) |
| **App 版本** | **2.1.0** |
| ESP-IDF 版本 | v5.5.1 |
| 编译时间 | 2026-01-30 17:37:26 |
| Bootloader 编译 | 2026-01-30 17:37:49 |
| Bootloader 版本 | 1 |
| 入口地址 | 0x4037970c |
| 镜像大小 | 4,128,768 bytes (3.94 MB) |
| 校验和 | 0xdb (有效) |
| 验证哈希 | f495a3dd... (有效) |
| ELF SHA256 | ce36220d4c2e0fae... |
| MMU 页大小 | 64 KB |
| Secure Version | 0 |
| 板级类名 | `lc_s3_wifi_1_54tft` |

### 2.2 Flash 分区布局

| 分区 | 类型 | 子类型 | 偏移地址 | 大小 | 状态 |
|------|------|--------|----------|------|------|
| nvs | data | nvs | 0x009000 | 16 KB | 有数据 |
| otadata | data | ota | 0x00D000 | 8 KB | seq=1, 指向 ota_0 |
| phy_init | data | phy | 0x00F000 | 4 KB | 射频校准 |
| ota_0 | app | ota_0 | 0x020000 | ~4 MB | **活动固件** (magic 0xE9) |
| ota_1 | app | ota_1 | 0x410000 | ~4 MB | 空 (0xFF) |
| assets | data | 0x30 | 0x800000 | 8 MB | 资源 (1.55MB 已用) |

### 2.3 应用内存段布局

| 段 | 加载地址 | 大小 | 内存类型 | 说明 |
|----|----------|------|----------|------|
| 0 | 0x3C1D0020 | 825 KB | DROM | Flash 只读数据 (.rodata) |
| 1 | 0x3FCA1A00 | 25 KB | DRAM | 已初始化数据 (.data) |
| 2 | 0x42000020 | 1805 KB | IROM | 代码段 (.text) |
| 3 | 0x3FCA7D18 | 8 KB | DRAM | 补充数据段 |
| 4 | 0x40378000 | 102 KB | IRAM | 快速代码段 (.iram) |
| 5 | 0x50000000 | 32 B | RTC_DATA | RTC 内存数据 |
| **合计** | | **~2765 KB** | | |

### 2.4 NVS 存储内容

| 键 | 值 | 说明 |
|----|-----|------|
| UUID | 909b14d1-850c-4e16-80bf-04916553597c | 设备唯一标识 |
| WiFi SSID | CMCC-egTm | 主 WiFi |
| WiFi Password | fneme97c | 主 WiFi 密码 |
| WiFi SSID (备) | LCTECH-02 | 备用 WiFi |
| WebSocket URL | wss://api.tenclass.net/xiaozhi/v1/ | 默认 WS 端点 |
| MQTT 端点 | mqtt.xiaozhi.me | MQTT 服务器 |
| OTA URL | https://api.tenclass.net/xiaozhi/ota/ | 固件检查/配置端点 |
| cal_data | (射频校准) | PHY 校准数据 |

### 2.5 资源分区 (Assets)

| 文件 | 说明 |
|------|------|
| `font_puhui_common_20_4.bin` | 阿里巴巴普惠体 20pt |
| `srmodels.bin` | 语音唤醒模型 (WakeNet) |
| `index.json` | 资源索引 |
| `angry.png` ~ `winking.png` | 21 个表情 PNG |
| **实际使用** | **~1.55 MB / 8 MB** |

---

## 三、固件功能清单

### 3.1 板级初始化方法

| 方法 | 功能 |
|------|------|
| `InitializeDisplay()` | ST7789 240x240 SPI 显示初始化 |
| `InitializeI2c()` | ES8311 编解码器 I2C 总线 |
| `InitializeSpi()` | 显示屏 SPI 总线 (SPI3_HOST) |
| `InitializeButtons()` | 4 个按键 (Boot/Volume Up/Volume Down/其他) |
| `InitializePowerManager()` | 电池电量 ADC 检测 (GPIO38) |
| `InitializeTools()` | MCP 工具注册 (灯控) |

### 3.2 MCP 工具清单 (共 13 个)

**板级专属工具 (3 个)** — 由 `InitializeTools()` 注册:

| 工具名 | 功能 |
|--------|------|
| `self.light.get_power` | 获取灯控状态 |
| `self.light.turn_on` | 开灯 |
| `self.light.turn_off` | 关灯 |

**框架标准工具 (10 个)** — 由 Application 基类注册:

| 工具名 | 功能 |
|--------|------|
| `self.get_system_info` | 系统信息 |
| `self.get_device_status` | 设备状态 |
| `self.assets.set_download_url` | 设置资源下载地址 |
| `self.audio_speaker.set_volume` | 设置音量 |
| `self.camera.take_photo` | 拍照 |
| `self.screen.get_info` | 屏幕信息 |
| `self.screen.preview_image` | 预览图片 |
| `self.screen.set_brightness` | 设置亮度 |
| `self.screen.set_theme` | 设置主题 |
| `self.screen.snapshot` | 屏幕截图 |

### 3.3 通信协议架构

```
┌─────────────────────────────────────────────────┐
│                 设备启动流程                       │
├─────────────────────────────────────────────────┤
│ 1. WiFi 连接                                      │
│ 2. OTA 版本检查 (POST → OTA URL)                 │
│    ↓ 服务器返回 JSON 配置                          │
│ 3. 协议选择:                                      │
│    ├─ 有 "mqtt" 节  → MqttProtocol               │
│    ├─ 有 "websocket" 节 → WebsocketProtocol      │
│    └─ 都没有       → 默认 MqttProtocol (失败)      │
│ 4. 激活流程 (如需)                                 │
│ 5. 进入主循环                                      │
└─────────────────────────────────────────────────┘
```

**WebSocket 协议**:
- 端点: `wss://api.tenclass.net/xiaozhi/v1/`
- 用途: 双向实时通信 + 音频流 (Opus 编码)
- 全双工: 文本消息 (JSON) + 二进制音频帧

**MQTT 协议**:
- MQTT 用于信令 (JSON 文本消息)
- UDP 用于音频流 (AES-CTR 加密, Opus 编码)
- 端点: `mqtt.xiaozhi.me` (从 OTA 响应获取)
- 发布主题: `publish_topic` (设备→服务器)
- 订阅主题: `subscribe_topic` (服务器→设备)
- 保活间隔: 240 秒
- 音频通道: MQTT 协商 → UDP 直传 (加密)

### 3.4 关键功能模块

| 模块 | 实现 | 说明 |
|------|------|------|
| 语音唤醒 | WakeNet + srmodels.bin | 离线唤醒词检测 |
| 语音识别 | (服务器端) | 通过 WebSocket/MQTT 发送音频 |
| 语音合成 | (服务器端) | 接收 Opus 音频播放 |
| 音频编解码 | Opus (编码/解码) | 16kHz, libopus |
| 显示驱动 | ST7789 SPI + LVGL | 240x240 RGB565 |
| 背光控制 | PWM (LEDC) | GPIO2, 可调亮度 |
| 按键 | 4 路独立按键 | Boot + 3 功能键 |
| 电池检测 | ADC 读取 | PowerManager GPIO38 |
| WiFi | 内置 | 多 SSID 支持 |
| OTA | 双分区 OTA | ota_0/ota_1, 当前 ota_0 |
| Web 配置 | HTTP 服务器 | SSID/密码/OTA URL/高级设置 |
| 多语言 | 20+ 语言 | i18n 字符串内置 |
| 相机 | JPEG 编码 | (如有相机模块) |
| 表情 | 21 个 PNG | LVGL 渲染 |
| 字体 | 阿里巴巴普惠体 | 20pt CJK |
| TLS | esp-tls | WebSocket over TLS |

### 3.5 与上游 v2.1.0 genjutech-s3-1.54tft 对比

| 特性 | 本固件 (lc_s3_wifi_1_54tft) | 上游 v2.1.0 (GenJuTech_s3_1_54TFT) |
|------|-----|------|
| GPIO 配置 | **完全一致** | **完全一致** |
| 类名 | `lc_s3_wifi_1_54tft` | `GenJuTech_s3_1_54TFT` |
| InitializeTools | **有** (灯控 3 工具) | **无** |
| InitializePowerManager | 有 | 有 |
| PowerSaveTimer | **无** | **有** |
| GetBatteryLevel | **无** | **有** |
| ES8311 编解码器 | 有 | 有 |
| SparkBotEs8311AudioCodec | 未知 | 有 (自定义编解码器子类) |
| IDF 要求 | v5.5.1 (实际编译) | >=5.4.0 |

---

## 四、三个固件版本的二进制差异

### 4.1 补丁总览

| 版本 | 日期 | WebSocket URL | OTA URL |
|------|------|---------------|---------|
| `flash_16MB_original.bin` | 6月13日 | `wss://api.tenclass.net/xiaozhi/v1/` | `https://api.tenclass.net/xiaozhi/ota/` |
| `flash_16MB_patched.bin` | 7月7日 | `ws://192.168.1.7:8088/ws/xiaozhi` | (未修改) |
| `flash_16MB_local.bin` | 8月11日 | `ws://192.168.1.3:8000/ws/xiaozhi` | `http://192.168.1.3:8000/xiaozhi/ota` |

### 4.2 二进制补丁位置

**补丁区域 1 — WebSocket URL** (DROM 段, 偏移 0x9CA2):
```
原始: 77 73 73 3A 2F 2F 61 70 69 2E 74 65 6E 63 6C 61 73 73 2E 6E 65 74 2F 78 69 61 6F 7A 68 69 2F 76 31 2F
      w  s  s  :  /  /  a  p  i  .  t  e  n  c  l  a  s  s  .  n  e  t  /  x  i  a  o  z  h  i  /  v  1  /  (35 bytes)

本地: 77 73 3A 2F 2F 31 39 32 2E 31 36 38 2E 31 2E 33 3A 38 30 30 30 2F 77 73 2F 78 69 61 6F 7A 68 69 00 00
      w  s  :  /  /  1  9  2  .  1  6  8  .  1  .  3  :  8  0  0  0  /  w  s  /  x  i  a  o  z  h  i  NUL NUL  (33+2 bytes)
```

**补丁区域 2 — OTA URL** (IROM 段, 偏移 0x28FE3):
```
原始: 68 74 74 70 73 3A 2F 2F 61 70 69 2E 74 65 6E 63 6C 61 73 73 2E 6E 65 74 2F 78 69 61 6F 7A 68 69 2F 6F 74 61 2F
      h  t  t  p  s  :  /  /  a  p  i  .  t  e  n  c  l  a  s  s  .  n  e  t  /  x  i  a  o  z  h  i  /  o  t  a  /  (37 bytes)

本地: 68 74 74 70 3A 2F 2F 31 39 32 2E 31 36 38 2E 31 2E 33 3A 38 30 30 30 2F 78 69 61 6F 7A 68 69 2F 6F 74 61 00 00
      h  t  t  p  :  /  /  1  9  2  .  1  6  8  .  1  .  3  :  8  0  0  0  /  x  i  a  o  z  h  i  /  o  t  a  NUL NUL  (35+2 bytes)
```

**补丁原理**: 等长覆盖, 新串短于旧串时用 `\x00` 填充, 利用 C 字符串 NUL 终止特性, 不破坏相邻数据。

### 4.3 NVS 中的 MQTT 端点

固件二进制中硬编码了 `mqtt.xiaozhi.me`, 但 MQTT 端点实际来自 OTA 响应并存储在 NVS `mqtt` 命名空间。**三个版本均未修改 MQTT 端点**——MQTT 地址由服务器 OTA 响应动态下发。

---

## 五、固件完善方案: 实现 Charlie MQTT 功能

### 5.1 当前固件通信流程详解

```
设备开机
  │
  ├─ 1. WiFi 连接 (SSID 从 NVS 读取: CMCC-egTm)
  │
  ├─ 2. OTA 版本检查 (POST → OTA URL)
  │     │
  │     │  请求体: { "version":"2.1.0", "chip":"esp32s3", "board":"lc-s3-wifi-1.54tft", ... }
  │     │
  │     │  服务器响应 JSON:
  │     │  {
  │     │    "mqtt": {                          ← 有此节 → 选 MQTT 协议
  │     │      "endpoint": "mqtt://xxx:1883",
  │     │      "client_id": "xxx",
  │     │      "publish_topic": "xxx",
  │     │      "subscribe_topic": "xxx",
  │     │      "username": "xxx",
  │     │      "password": "xxx",
  │     │      "keepalive": 240
  │     │    },
  │     │    "websocket": { "url": "ws://xxx" },  ← 或有此节 → 选 WS 协议
  │     │    "activation": { "challenge": "..." },
  │     │    "firmware": { "version": "...", "url": "..." }
  │     │  }
  │     │
  │     └─ 协议选择: 有 mqtt 节 → MqttProtocol, 否则 → WebsocketProtocol
  │
  ├─ 3. 激活 (POST → OTA URL + /activate)  ← 如有 activation.challenge
  │
  ├─ 4. 协议连接
  │     ├─ MqttProtocol: 连接 MQTT broker → 信令通过 MQTT, 音频通过 UDP (AES-CTR 加密)
  │     └─ WebsocketProtocol: 连接 WebSocket → 信令+音频全走 WS (Opus 编码)
  │
  └─ 5. 主循环: 语音唤醒 → 录音 → Opus 编码 → 发送 → 接收 TTS → 播放
```

### 5.2 方案 A: 纯二进制补丁 (推荐, 无需编译)

**原理**: 仅修改固件中的两个硬编码 URL, 通过 Charlie 服务器的 OTA 响应下发 MQTT 配置。

**步骤**:

1. **补丁固件** (已有 `patch_local.py`):
   ```python
   PATCHES = [
       (b"wss://api.tenclass.net/xiaozhi/v1/", b"ws://CHARLIE_IP:PORT/ws/xiaozhi"),
       (b"https://api.tenclass.net/xiaozhi/ota/", b"http://CHARLIE_IP:PORT/xiaozhi/ota"),
   ]
   ```

2. **Charlie 服务器需实现**: `POST /xiaozhi/ota`
   - 请求体: 设备系统信息 JSON (版本/芯片/板名/MAC/UUID)
   - 响应体:
   ```json
   {
     "mqtt": {
       "endpoint": "mqtt://CHARLIE_IP:1883",
       "client_id": "charlie-device-909b14d1",
       "publish_topic": "xiaozhi/v1/909b14d1/s",
       "subscribe_topic": "xiaozhi/v1/909b14d1/c",
       "username": "charlie",
       "password": "charlie-pass",
       "keepalive": 240
     }
   }
   ```

3. **Charlie MQTT Broker**: 运行 Mosquitto/EMQX 等
   - 监听 1883 端口
   - 接收设备发布消息 (音频数据/状态/事件)
   - 向设备下发指令 (TTS/控制/MCP 工具调用)

4. **音频通道** (MQTT 协议下):
   - MQTT 消息协商 UDP 音频通道 (交换 IP/端口/密钥)
   - UDP 传输 Opus 音频 (AES-CTR 加密)
   - 需要 Charlie 服务器支持 UDP 音频接收

**优点**: 零编译, 用现有 v5.5.1 固件直接烧录, 硬件兼容性 100%
**缺点**: MQTT 端点不可直接二进制补丁 (由服务器 OTA 响应动态下发)

### 5.3 方案 B: 源码修改 + 重新编译

**原理**: 用 upstream `genjutech-s3-1.54tft` 板代码 (GPIO 完全一致), 添加灯控工具, 修改配置后编译。

**步骤**:

1. **代码准备**:
   - 基于 upstream v2.1.0 tag (IDF >=5.4.0, v5.5.2 兼容)
   - 使用 `genjutech-s3-1.54tft` 板配置
   - 添加 `InitializeTools()` 方法 (3 个灯控 MCP 工具)
   - 修改 `Kconfig.projbuild` 中的 `CONFIG_OTA_URL` 默认值

2. **ESP-IDF 版本**:
   - **推荐**: ESP-IDF v5.5.1 (与原始固件一致)
   - **已知问题**: v5.5.2 编译的固件无法启动 app_main (启动挂起)
   - **替代**: 如必须用 v5.5.2, 需定位并修复启动挂起的具体代码变更

3. **组件依赖**:
   - `78/esp-ml307` v3.6.5 要求 `idf >=5.5.2`
   - 如用 v5.5.1: 需降级该组件或移除 ML307 支持 (此板无 4G 模块, 可安全移除)
   - 或: 从 `CMakeLists.txt` 移除 `esp-ml307` 组件依赖

4. **需要添加的板级代码**:
   ```cpp
   void InitializeTools() {
       // 灯控 MCP 工具
       McpServer::GetInstance().AddTool("self.light.get_power",
           "获取灯光状态", ...);
       McpServer::GetInstance().AddTool("self.light.turn_on",
           "开灯", ...);
       McpServer::GetInstance().AddTool("self.light.turn_off",
           "关灯", ...);
   }
   ```

5. **sdkconfig 关键配置**:
   ```
   CONFIG_IDF_TARGET="esp32s3"
   CONFIG_BOARD_TYPE_GENJUTECH_S3_1_54TFT=y
   CONFIG_SPIRAM_MODE_OCT=y          # Octal PSRAM
   CONFIG_SPIRAM_SPEED_80M=y         # 80MHz PSRAM
   CONFIG_SPIRAM_BOOT_INIT=y        # 启动时初始化 PSRAM
   CONFIG_FLASHMODE_DIO=y            # DIO Flash 模式
   CONFIG_SPI_FLASH_FREQ_80M=y       # 80MHz Flash
   CONFIG_SPIRAM=y                   # 启用 PSRAM
   ```

**优点**: 完全可控, 可添加任意自定义功能
**缺点**: 需解决 ESP-IDF v5.5.2 启动挂起问题或降级组件依赖

### 5.4 方案 C: 混合方案 (推荐用于 Charlie 项目)

**原理**: 保持原始固件二进制不变, 仅补丁 URL, 通过服务器端配置实现 MQTT。

1. 用 `flash_16MB_local.bin` (已补丁到 192.168.1.3:8000) 烧录
2. Charlie 服务器实现 `/xiaozhi/ota` 端点, 返回 MQTT 配置
3. MQTT broker 运行在 Charlie 服务器
4. 音频通道: WebSocket (简单) 或 MQTT+UDP (低延迟)

**选择建议**:
- **如果 Charlie 服务器已有 WebSocket 服务**: 用 WebSocket 协议 (OTA 响应返回 `websocket` 节)
- **如果需要 MQTT 接入现有智能家居系统**: 用 MQTT 协议 (OTA 响应返回 `mqtt` 节)
- **音频传输**: WebSocket 更简单 (全双工 TCP); MQTT+UDP 延迟更低但实现复杂

### 5.5 Charlie MQTT 消息协议 (需要实现)

设备通过 MQTT 发布的消息 (publish_topic):
```json
{"type":"hello","session_id":"xxx","audio_params":{"format":"opus","sample_rate":16000,"channels":1,"frame_size":60}}
{"type":"audio","data":"<base64_opus_data>","is_last":false}
{"type":"goodbye","session_id":"xxx"}
{"type":"iot","cmd":"get_power","params":{}}    // MCP 工具调用结果
```

服务器通过 MQTT 下发的消息 (subscribe_topic):
```json
{"type":"tts","text":"你好","voice":"xxx"}
{"type":"audio","data":"<base64_opus_data>"}
{"type":"stt","text":"识别结果"}
{"type":"llm","emotion":"happy","emoji":"happy"}
{"type":"mcp","tool":"self.light.turn_on","args":{}}
```

UDP 音频通道协商 (MQTT 信令):
```json
{"type":"audio_channel","session_id":"xxx","udp_port":12345,"key":"<base64_aes_key>","nonce":"<base64_nonce>"}}
```

---

## 六、文件清单

| 文件 | 大小 | 说明 |
|------|------|------|
| `flash_16MB_original.bin` | 16 MB | 原始固件 (6月13日购买自带, 官方服务器) |
| `flash_16MB_patched.bin` | 16 MB | 补丁版 (7月7日, WS 指向 192.168.1.7:8088) |
| `flash_16MB_local.bin` | 16 MB | 补丁版 (8月11日, WS+OTA 指向 192.168.1.3:8000) |
| `patch_local.py` | 2.6 KB | 二进制补丁脚本 |
| `FLASH_ANALYSIS_REPORT.md` | 4.7 KB | 原始分析报告 (7月12日) |
| `ANALYSIS_REPORT.md` | 本文件 | 深度分析报告 (8月16日) |

---

## 七、结论与建议

### 核心发现

1. **固件版本是 v2.1.0**, 不是之前认为的 v1.0.0
2. **固件源码不在任何公共 GitHub 仓库**: 类名 `lc_s3_wifi_1_54tft` 和 `InitializeTools` 灯控功能是定制代码, 从未提交
3. **GPIO 与 upstream `genjutech-s3-1.54tft` 完全一致**: 可以用上游板代码替代
4. **MQTT 端点由 OTA 响应动态下发**, 不是硬编码 — 二进制补丁只需改 OTA URL, MQTT 配置由服务器控制
5. **ESP-IDF v5.5.2 编译的固件无法启动**: 这是一个独立的启动挂起问题, 与板代码无关

### 推荐路径

**短期 (最快)**: 方案 A — 用 `flash_16MB_local.bin` 烧录 + Charlie 服务器实现 OTA/MQTT 端点

**中期 (最灵活)**: 方案 C — 用上游 genjutech 代码 + 灯控工具 + v5.5.1 编译 (需解决组件依赖)

**长期 (完整定制)**: Fork upstream, 完整实现 Charlie 定制板代码 + MQTT + 灯控 + 其他自定义功能
