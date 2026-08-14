#!/usr/bin/env python3
"""Clear mqtt namespace from NVS partition in a flash bin.

NVS entries are 16-byte aligned. The mqtt namespace starts at offset 0x90C8
in the NVS partition (which is at flash offset 0x9000).
This script zeroes out mqtt-related entries to force Charlie fallback on next boot.
"""
import sys

if len(sys.argv) < 3:
    print(f"Usage: {sys.argv[0]} <input.bin> <output.bin>")
    sys.exit(1)

with open(sys.argv[1], 'rb') as f:
    data = bytearray(f.read())

nvs_offset = 0x9000
nvs_size = 0x4000

mqtt_keys = [b'endpoint', b'client_id', b'username', b'password', b'publish_topic', b'subscribe_topic']

cleared = 0
offset = nvs_offset
while offset < nvs_offset + nvs_size - 16:
    entry = data[offset:offset+16]
    if entry[0] == 0xFF or all(b == 0 for b in entry[:4]):
        offset += 8
        continue
    entry_str = bytes(entry).decode('ascii', errors='replace')
    for key in mqtt_keys:
        if key.decode() in entry_str:
            for i in range(16):
                data[offset + i] = 0xFF
            cleared += 1
            print(f"  Cleared mqtt entry at offset 0x{offset:04X}: {entry_str.strip()!r}")
            break
    offset += 8

# Also clear the mqtt namespace key itself
mqtt_ns_pos = data.find(b'mqtt\x00', nvs_offset, nvs_offset + nvs_size)
if mqtt_ns_pos != -1:
    for i in range(16):
        data[mqtt_ns_pos + i] = 0xFF
    cleared += 1
    print(f"  Cleared mqtt namespace at offset 0x{mqtt_ns_pos:04X}")

print(f"\nCleared {cleared} mqtt NVS entries")

with open(sys.argv[2], 'wb') as f:
    f.write(data)
print(f"Written to {sys.argv[2]}")
