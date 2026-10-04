"""Static reader for the AirStrike2 APK format. Never runs game code.

Recovered from AirStrike2.exe VAs 0x405db0, 0x405df0, 0x4064c0.
Usage: python reconstruct_apk.py ARCHIVE.apk OUTPUT_DIRECTORY
"""
import argparse, collections, hashlib, json, pathlib, struct

def xor_bytes(data, key, position=0):
    if len(key) != 1024 or position < 0:
        raise ValueError('Expected a 1024-byte key and nonnegative position')
    return bytes(value ^ key[(position + i) % 1024] for i, value in enumerate(data))

def extract(source, destination):
    data = pathlib.Path(source).read_bytes()
    if len(data) < 1040:
        raise ValueError('Truncated APK header')
    version, tag, table_offset, count = struct.unpack_from('<IIII', data)
    if (version, tag) != (0x3f800000, 0x9999):
        raise ValueError('Unrecognized APK header')
    if not 1040 <= table_offset <= len(data) or count > (len(data)-table_offset)//76:
        raise ValueError('Directory outside archive')
    key = data[16:1040]
    table = xor_bytes(data[table_offset:table_offset+count*76], key)
    root = pathlib.Path(destination).resolve(); root.mkdir(parents=True, exist_ok=True)
    entries = []
    for i in range(count):
        entry = table[i*76:(i+1)*76]
        raw_name = entry[:64].split(b'\0',1)[0]
        name = raw_name.decode('cp1251').replace('\\','/')
        relative = pathlib.PurePosixPath(name)
        if not name or relative.is_absolute() or any(p in ('..','.') or ':' in p for p in relative.parts):
            raise ValueError(f'Unsafe archive path: {name!r}')
        offset, size, flags = struct.unpack_from('<III', entry, 64)
        if offset < 1040 or offset > table_offset or size > table_offset-offset:
            raise ValueError(f'Payload outside data area: {name}')
        blob = data[offset:offset+size]
        if flags: blob = xor_bytes(blob, key)
        target = root.joinpath(*relative.parts).resolve()
        if not target.is_relative_to(root): raise ValueError('Path escaped output directory')
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(blob)
        entries.append({'name':name,'offset':offset,'size':size,'flags':flags,'sha256':hashlib.sha256(blob).hexdigest()})
    manifest = {'archive':str(source),'sha256':hashlib.sha256(data).hexdigest(),'version_bits':hex(version),'tag':hex(tag),'table_offset':table_offset,'count':count,'extensions':dict(collections.Counter(pathlib.PurePosixPath(e['name']).suffix for e in entries)),'entries':entries}
    (root/'_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest

if __name__ == '__main__':
    key=bytes(range(256))*4; payload=b'archive self-check'*90
    assert xor_bytes(xor_bytes(payload,key,1019),key,1019)==payload
    assert xor_bytes(payload,key)==xor_bytes(payload[:77],key)+xor_bytes(payload[77:],key,77)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive'); parser.add_argument('destination')
    args=parser.parse_args(); result=extract(args.archive,args.destination)
    print(json.dumps({k:v for k,v in result.items() if k!='entries'},indent=2))
