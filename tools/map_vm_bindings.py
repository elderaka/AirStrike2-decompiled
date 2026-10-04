"""Read VM binding tables and dispatch handlers from the PE without loading it."""
import pathlib,sys,struct,json
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/packages'))
import pefile
pe=pefile.PE(str(ROOT/'game/AirStrike2.exe')); base=pe.OPTIONAL_HEADER.ImageBase
def string(va): return pe.get_data(va-base,512).split(b'\0',1)[0].decode('cp1251')
bindings=[]
for i in range(512):
 name,fn=struct.unpack('<II',pe.get_data(0x61f38+i*8,8))
 if not name: break
 bindings.append({'name':string(name),'handler_va':hex(fn)})
else: raise ValueError('Unterminated function table')
defs=[]
for i in range(512):
 name,selector0,selector1=struct.unpack('<III',pe.get_data(0x62270+i*12,12))
 if not name: break
 defs.append({'name':string(name),'selector0_va':hex(selector0),'selector1_va':hex(selector1)})
else: raise ValueError('Unterminated definition table')
handlers=struct.unpack('<31I',pe.get_data(0x26e90,124))
result={'interpreter_va':'0x4268f0','dispatch_table_va':'0x426e90','functions':bindings,'definitions':defs,'opcode_handlers':[{'opcode':i,'va':hex(va)} for i,va in enumerate(handlers)]}
(ROOT/'analysis/vm_bindings.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(len(bindings),'function bindings;',len(defs),'definition bindings;',len(handlers),'opcode handlers')
