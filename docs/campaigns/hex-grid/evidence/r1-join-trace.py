"""Read UE protocol-7 game-thread frame and NetTrace content records offline."""
from collections import Counter
from pathlib import Path
import struct


def decompress(block, expected):
    out = bytearray()
    i = 0
    def length(n):
        nonlocal i
        if n == 15:
            while True:
                value = block[i]
                i += 1
                n += value
                if value != 255:
                    break
        return n
    while i < len(block):
        token = block[i]
        i += 1
        n = length(token >> 4)
        out.extend(block[i:i+n])
        i += n
        if i == len(block):
            break
        distance = struct.unpack_from("<H", block, i)[0]
        i += 2
        assert 0 < distance <= len(out)
        n = 4 + length(token & 15)
        start = len(out) - distance
        if n <= distance:
            out.extend(out[start:start+n])
        else:
            out.extend((out[start:] * ((n + distance - 1) // distance))[:n])
    assert len(out) == expected
    return out


def streams(path):
    data = path.read_bytes()
    assert data[:4] == b"2CRT"
    header = struct.unpack_from("<H", data, 4)[0] + 6
    assert data[header+1] == 7
    curs = header + 2
    result = {i: bytearray() for i in (0, 1, 2, 3)}
    while curs < len(data):
        size, key = struct.unpack_from("<HH", data, curs)
        assert 4 <= size <= len(data) - curs
        stream = result.get(key & 0x3fff)
        if stream is not None:
            block = data[curs+4:curs+size]
            if key & 0x8000:
                block = decompress(block[2:], int.from_bytes(block[:2], "little"))
            stream.extend(block)
        curs += size
    return result


def important(data):
    pos = 0
    while pos < len(data):
        uid, size = struct.unpack_from("<HH", data, pos)
        end = pos + 4 + size
        assert end <= len(data)
        yield uid, data[pos+4:end]
        pos = end


def declarations(data):
    schema = {}
    for event, payload in important(data):
        assert event == 0
        uid, count, flags, logger_len, name_len = struct.unpack_from("<HBBBB", payload)
        offset = 6 + 8 * count
        name = payload[offset:offset+logger_len+name_len].decode()
        size = 0
        for i in range(count):
            family, _, off, length, info, n = struct.unpack_from("<BBHHBB", payload, 6 + i*8)
            assert family <= 2
            if family:
                length = 1 << ((info if family == 1 else n) & 3)
            size = max(size, off + length)
        schema[uid] = (name, flags, size)
    return schema


def ordinary(data, schema):
    pos = 0
    view = memoryview(data)
    while pos < len(data):
        raw = data[pos]
        if raw & 1:
            raw = struct.unpack_from("<H", data, pos)[0]
            pos += 1
        pos += 1
        uid = raw >> 1
        if uid == 1:
            size = struct.unpack_from("<I", data, pos-1)[0] >> 13
            pos += 3
            name = "Aux"
        elif uid < 16:
            size = {3: 0, 4: 0, 5: 0, 6: 8, 7: 8, 8: 7, 9: 7}[uid]
            name = "EndAux" if uid == 3 else "Scope"
        else:
            name, flags, size = schema[uid]
            if not flags & 4:
                pos += 3
        end = pos + size
        assert end <= len(data)
        yield name, view[pos:end]
        pos = end


def content_events(data):
    i = 0
    def varint():
        nonlocal i
        n = shift = 0
        while True:
            v = data[i]
            i += 1
            n |= (v & 127) << shift
            if not v & 128:
                return n
            shift += 7
            assert shift <= 63
    while i < len(data):
        category = data[i]
        i += 1
        if category in (0, 1):
            depth = data[i]
            i += 1
            key = varint()
            varint()
            bits = varint()
            yield category, key, bits, depth
        elif category == 2:
            varint()
            varint()
        elif category == 3:
            varint()
            if varint():
                varint()
        else:
            raise ValueError(f"Unknown NetTrace content event {category}")


def read_trace(path):
    data = streams(Path(path))
    schema = declarations(data[0])
    names = {}
    phase_logpoint = None
    for uid, payload in important(data[1]):
        if schema[uid][0] == "NetTraceNameEvent":
            name_id, aux = struct.unpack_from("<II", payload)
            length = aux >> 13
            assert payload[-1] == 3 and len(payload) == 9 + length
            names[name_id] = payload[8:-1].rstrip(b"\0").decode("utf-8", errors="replace")
        elif (schema[uid][0] == "LoggingLogMessageSpec"
              and b"CkHexDenseAcceptance.cpp" in payload
              and struct.unpack_from("<I",payload,16)[0]==169):
            assert phase_logpoint is None
            phase_logpoint = struct.unpack_from("<Q", payload)[0]
    freq = struct.unpack_from("<Q", data[3], 10)[0]
    starts, ends, packets, transitions, phase_times = [], [], [], [], []
    events, field_counts = Counter(), Counter()
    chunks = bytearray()
    collect = False
    incoming = set()
    phase_cycle = None
    for name, payload in ordinary(data[2], schema):
        if name == "Aux" and phase_cycle is not None:
            for expected in (0,5,6):
                text = f"HexDense [client] phase={expected}"
                if text.encode("utf-16-le") in bytes(payload) or text.encode() in bytes(payload):
                    phase_times.append((expected, phase_cycle))
                    break
            phase_cycle = None
        elif name != "Aux":
            phase_cycle = None
        if name == "Aux" and collect:
            chunks.extend(payload)
            continue
        if chunks:
            assert name == "EndAux", name
            for kind, key, bits, depth in content_events(chunks):
                if kind == 1 and names[key] in ("_Placements", "_BindingId", "_OccupantBindingId", "_PlacementId"):
                    field = names[key]
                    events[field] += bits
                    field_counts[field] += 1
            chunks.clear()
        collect = False
        if name in ("MiscBeginFrame", "MiscEndFrame"):
            cycle, typ = struct.unpack_from("<QB", payload)
            if typ == 0:
                (starts if name == "MiscBeginFrame" else ends).append(cycle)
        elif name == "LoggingLogMessage":
            logpoint, cycle = struct.unpack_from("<QQ", payload)
            if logpoint == phase_logpoint:
                phase_cycle = cycle
        elif name == "NetTraceConnectionStateUpdatedEvent":
            connection, instance, state = struct.unpack_from("<HBB", payload)
            transitions.append((len(starts)-1, connection, instance, state))
        elif name == "NetTraceConnectionClosedEvent":
            connection, instance = struct.unpack_from("<HB", payload)
            transitions.append((len(starts)-1, connection, instance, -1))
        elif name == "NetTracePacketContentEvent":
            connection, instance, direction = struct.unpack_from("<HBB", payload)
            collect = direction == 1
            if collect:
                incoming.add((connection,instance))
        elif name == "NetTracePacketEvent":
            cycle, packet_bits, seq, connection, instance, direction = struct.unpack_from("<QIIHBB", payload)
            if direction == 1:
                incoming.add((connection,instance))
                packets.append((cycle, packet_bits, seq, events, field_counts))
                events, field_counts = Counter(), Counter()
    assert not events
    assert len(incoming) == 1
    assert len(starts) == len(ends)
    assert all(a < b for a, b in zip(starts, ends))
    assert all(a <= b for a, b in zip(ends, starts[1:]))
    return freq, starts, ends, packets, transitions, phase_times
