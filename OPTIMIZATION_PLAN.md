# v1.1.0 固件优化计划

> 基于 `flash_16MB_local.bin` 二进制分析 + xz 固件源码对比
> 目标: 满足 Charlie 语音助手的全部功能要求

## 问题清单（来自二进制分析）

| # | 问题 | 位置 |
|---|------|------|
| 1 | hello 消息缺少 device_id，Charlie 无法识别设备 | `websocket_protocol.cc:GetHelloMessage()` |
| 2 | MQTT endpoint 指向公网 `mqtt.xiaozhi.me`，非本地 | NVS `mqtt/endpoint` |
| 3 | MQTT publish_topic 为 `device-server`，非标准格式 | NVS `mqtt/publish_topic` |
| 4 | MQTT subscribe_topic 为 `null`，无法接收推送 | NVS `mqtt/subscribe_topic` |
| 5 | 无 ping/pong 心跳，WebSocket 可能 NAT 超时断开 | `websocket_protocol.cc` |
| 6 | WebSocket 不发送 goodbye，服务端只能超时清理 | `websocket_protocol.cc:CloseAudioChannel()` |

## 修复方案

### 修复 1: hello 添加 device_id

**修改文件**: `xz/main/protocols/websocket_protocol.cc` (GetHelloMessage)

```cpp
// 在 audio_params 之后添加
auto uuid = Board::GetInstance().GetUuid();
cJSON_AddStringToObject(root, "device_id", uuid.c_str());
```

**Charlie 服务端**: `xiaozhi_ws.py` hello 处理已支持 `device_id` 字段（第895-901行）。

### 修复 2+3+4: 修复 MQTT 默认配置

**方案**: 利用固件已有的 Charlie fallback 机制（`mqtt_protocol.cc:76-89`）：

当 NVS 中 `mqtt/endpoint` 为空时，固件自动使用：
- endpoint: `CHARLIE_MQTT_FALLBACK_ENDPOINT`
- client_id: `charlie-esp32-{uuid_short}`
- publish_topic: `charlie/esp32/{uuid_short}/up`
- subscribe_topic: `charlie/esp32/{uuid_short}/down`

**操作**: 烧录时用 `nvs_flash` 清空 mqtt namespace，或直接编译时设置 `CHARLIE_MQTT_FALLBACK_ENDPOINT` 为本地 IP。

### 修复 5: 添加 ping/pong

**修改文件**: `xz/main/protocols/websocket_protocol.cc`

```cpp
// 在 Start() 中添加定时 ping
esp_timer_create_args_t ping_args = {
    .callback = [](void* arg) {
        auto* proto = static_cast<WebsocketProtocol*>(arg);
        if (proto->IsAudioChannelOpened()) {
            proto->SendText("{\"type\":\"ping\"}");
        }
    },
    .arg = this,
    .dispatch_method = ESP_TIMER_TASK,
    .name = "ws_ping"
};
esp_timer_create(&ping_args, &ping_timer_);
esp_timer_start_periodic(ping_timer_, 30'000'000); // 30s
```

Charlie 服务端已支持（`xiaozhi_ws.py:961`）：收到 ping → 回复 pong。

### 修复 6: WebSocket 发送 goodbye

**修改文件**: `xz/main/protocols/websocket_protocol.cc` (CloseAudioChannel)

```cpp
void WebsocketProtocol::CloseAudioChannel(bool send_goodbye) {
    // 原来: (void)send_goodbye;  // 忽略参数
    // 改为:
    if (send_goodbye) {
        std::string message = "{\"session_id\":\"" + session_id_ + 
                              "\",\"type\":\"goodbye\"}";
        SendText(message);
    }
    // ... 其余不变
}
```

## 编译步骤

```bash
export IDF_PATH=/Users/sxliuyu/esp-idf-v5.5.2
export IDF_SKIP_CHECK_SUBMODULES=1
cd /Users/sxliuyu/repos/xz

# 1. 确认板型
python3 -c "
import re
with open('sdkconfig','r') as f: c=f.read()
c=re.sub(r'CONFIG_BOARD_TYPE_BREAD_COMPACT_WIFI=y','# CONFIG_BOARD_TYPE_BREAD_COMPACT_WIFI is not set',c)
if 'CONFIG_BOARD_TYPE_LC_S3_WIFI_1_54TFT=y' not in c:
    c=c.replace('# CONFIG_BOARD_TYPE_XINGZHI_ABS_2_0 is not set','CONFIG_BOARD_TYPE_LC_S3_WIFI_1_54TFT=y\n# CONFIG_BOARD_TYPE_XINGZHI_ABS_2_0 is not set')
with open('sdkconfig','w') as f: f.write(c)
print('sdkconfig updated')
"

# 2. 构建
/Users/sxliuyu/.espressif/python_env/idf5.5_py3.14_env/bin/python \
  /Users/sxliuyu/esp-idf-v5.5.2/tools/idf.py build

# 3. 打包为全量镜像
/Users/sxliuyu/.espressif/python_env/idf5.5_py3.14_env/bin/python \
  /Users/sxliuyu/esp-idf-v5.5.2/components/esptool_py/esptool/esptool.py \
  -cp /dev/tty.usbmodem101 -ca 0x0 -ef flash_16MB_v1.1.0.bin

# 4. 烧录
/Users/sxliuyu/.espressif/python_env/idf5.5_py3.14_env/bin/python \
  /Users/sxliuyu/esp-idf-v5.5.2/tools/idf.py -p /dev/tty.usbmodem101 flash
```

## 验证

烧录后串口应显示：
```
I SKU=lc-s3-wifi-1.54tft
I UUID=909b14d1-...
I Connecting to websocket server: ws://192.168.1.3:8000/ws/xiaozhi
I Session ID: xxx
>> <STT text>     ← stt 消息正常显示
<< <TTS text>     ← tts sentence_start 正常显示
```

## 待确认

- [ ] Charlie 服务端 hello 处理对 device_id 的支持是否完整
- [ ] ping/pong 定时是否需要在 esp_timer 中做边界检查
- [ ] NVS 清除方案（全量烧录 vs 增量 patch）
