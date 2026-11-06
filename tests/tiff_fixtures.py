"""Small literal TIFF encodings for actual browser worker rejection/mask checks."""
import struct
import zlib


def literal_lzw(raw):
    # Clear before each literal: legal TIFF LZW with a fixed nine-bit code width.
    codes = [code for value in raw for code in (256, value)] + [257]
    bits = ''.join(f'{code:09b}' for code in codes)
    bits += '0' * (-len(bits) % 8)
    return bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8))


def tiff(values=(0., float("nan"), 10., 20.), *, width=2, height=2, epsg=4326, nodata="nan", metadata=None, kind=0, sparse=False, compression=1, bomb=False, big_endian=False, loop=False, large_entries=False, tile_width=None, tile_height=None, rows_per_strip=None, dx=.1, dy=.1):
    def pack(fmt, *args):
        return struct.pack("<" + fmt, *args)
    keys = [1, 1, 0, 3, 1024, 0, 1, 2, 1025, 0, 1, 1, 2048, 0, 1, epsg]
    raw = pack("f" * len(values), *values)
    if bomb:
        compression = 8
        raw = zlib.compress(b"\0" * 1000000)
    elif compression == 8:
        raw = zlib.compress(raw)
    elif compression == 5:
        raw = literal_lzw(raw)
    tags = [(254,4,pack("I",kind)), (256,4,pack("I",width)), (257,4,pack("I",height)), (258,3,pack("H",32)), (259,3,pack("H",compression)), (262,3,pack("H",1)), (273,4,pack("II",0,0) if sparse else pack("I",0)), (277,3,pack("H",1)), (278,4,pack("I",rows_per_strip if rows_per_strip is not None else 1 if sparse else height)), (279,4,pack("II",0,8) if sparse else pack("I",len(raw))), (284,3,pack("H",1)), (339,3,pack("H",3)), (33550,12,pack("ddd",dx,dy,0)), (33922,12,pack("dddddd",0,0,0,10,20,0)), (34735,3,pack("H"*len(keys),*keys))]
    if tile_width is not None or tile_height is not None:
        tags = [(324 if tag == 273 else 325 if tag == 279 else tag, kind_, value) for tag,kind_,value in tags if tag != 278]
        tags.extend([(322,4,pack('I',width if tile_width is None else tile_width)),(323,4,pack('I',height if tile_height is None else tile_height))])
    if nodata is not None:
        tags.append((42113,2,(nodata+"\0").encode()))
    if metadata:
        tags.append((42112,2,(metadata+"\0").encode()))
    tags.sort()
    end = 8+2+12*len(tags)+4
    offsets = {}
    for tag, type_, value in tags:
        if len(value)>4:
            offsets[tag] = end
            end += len(value)
    output = bytearray(end)
    output[:8] = b"II"+pack("H",42)+pack("I",8)
    output[8:10] = pack("H",5000 if large_entries else len(tags))
    sizes = {2:1,3:2,4:4,12:8}
    for index,(tag,type_,value) in enumerate(tags):
        if tag in (273,324):
            value=pack("II",0,end) if sparse else pack("I",end)
        at=10+index*12
        output[at:at+8]=pack("HHI",tag,type_,len(value)//sizes[type_])
        if len(value)>4:
            output[at+8:at+12]=pack("I",offsets[tag])
            output[offsets[tag]:offsets[tag]+len(value)]=value
        else:
            output[at+8:at+8+len(value)]=value
    if loop:
        output[10+12*len(tags):14+12*len(tags)]=pack("I",8)
    output.extend(pack("ff",10,20) if sparse else raw)
    if big_endian:
        output[:2]=b"MM"
    return bytes(output)
