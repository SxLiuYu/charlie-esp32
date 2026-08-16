#!/usr/bin/env python3
"""Patch xiaozhi flash 固件, 把 OTA/WS 全部指向本地 Charlie 服务器, 跳过官方激活。

只做等长覆盖: 新旧字符串必须编译后长度一致, 否则破坏相邻数据。
支持直接对 flash_16MB.bin 打补丁, 也支持对已 patch 的镜像再打。
"""
import re
import sys
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "flash_16MB.bin"
DST = HERE / "flash_16MB_local.bin"

# (旧串, 新串) —— 要求 len(old) == len(new)
PATCHES = [
    # 1) OTA 检查地址: 官方 -> 本地 /xiaozhi/ota
    (b"https://api.tenclass.net/xiaozhi/ota/",
     b"http://192.168.1.3:8000/xiaozhi/ota"),
    # 2) WebSocket 地址: 官方 -> 本地 /ws/xiaozhi
    (b"wss://api.tenclass.net/xiaozhi/v1/",
     b"ws://192.168.1.3:8000/ws/xiaozhi"),
]

def main():
    if not SRC.exists():
        sys.exit(f"找不到源文件: {SRC}")
    print(f"源: {SRC} ({SRC.stat().st_size} bytes)")
    data = bytearray(SRC.read_bytes())

    for old, new in PATCHES:
        # 等长或更短均可: 更短时用 \x00 填充到旧串长度, 保证 strlen 提前终止,
        # 不破坏后续相邻数据 (这是 C 字符串 NUL 终止的固有行为)。
        if len(new) > len(old):
            print(f"!! 新串更长, 跳过: {old[:30]}... ({len(old)} vs {len(new)})")
            continue
        pad = b"\x00" * (len(old) - len(new))
        full = new + pad
        count = 0
        start = 0
        while True:
            i = data.find(old, start)
            if i < 0:
                break
            data[i:i + len(old)] = full
            count += 1
            start = i + len(old)
        print(f"  [{old.decode(errors='replace')}]({len(old)}) -> {new.decode()}({len(new)}+nul{len(pad)})  替换 {count} 处")

    # 兼容: 若设备里已经存过 192.168.1.7:8088 的旧 patch (仅 ws), 一并拉平
    stale = b"ws://192.168.1.7:8088/ws/xiaozhi"
    good = b"ws://192.168.1.3:8000/ws/xiaozhi"
    if len(stale) == len(good):
        n = data.count(stale)
        if n:
            for i in range(len(data) - len(stale) + 1):
                if data[i:i + len(stale)] == stale:
                    data[i:i + len(good)] = good
            print(f"  stale ws 192.168.1.7 -> 192.168.1.3: 已处理 {n} 处")
    else:
        print("stale ws 长度不一致, 跳过")

    DST.write_bytes(data)
    print(f"写入: {DST} ({len(data)} bytes)")
    # 校验
    for old, new in PATCHES:
        print(f"  校验: 残留旧串={data.count(old)}, 出现新串={data.count(new)}")

if __name__ == "__main__":
    main()