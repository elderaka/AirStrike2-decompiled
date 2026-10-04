"""One focused check for malformed RCSL input and corpus consistency."""
import pathlib,struct
from decode_scripts import parse,ROOT

def must_reject(data):
    try: parse(data)
    except ValueError: return
    raise AssertionError('Malformed script was accepted')

data=(ROOT/'assets/pak1/scripts/radar.scr').read_bytes()
must_reject(data[:20]); must_reject(data[:-1])
bad=bytearray(data);struct.pack_into('<I',bad,56+4,0xffffffff);must_reject(bad)
bad=bytearray(data);struct.pack_into('<i',bad,32,4);must_reject(bad)
bad=bytearray(data);bad[89]=255;must_reject(bad)
bad=bytearray(data);struct.pack_into('<i',bad,89+14+2,-2);must_reject(bad)
count=0
for p in (ROOT/'assets/pak1').rglob('*'):
    if p.suffix not in ('.sc','.scr'):continue
    script=parse(p.read_bytes())
    assert script['version']==16
    for pc in script['header_words'][9:14]:
        assert pc==-1 or 0<=pc<len(script['instructions']),str(p)
    count+=1
assert count==631
print('PASS: malformed/truncated data rejected; all 631 containers and their five entry-point fields validated.')
