"""Decode RCSL containers and instruction records as data; no VM execution.
Usage: python tools/decode_scripts.py [project_directory]
"""
import collections, json, pathlib, struct, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
# Labels from the 31-entry dispatch table at VA 0x426e90.
# Floating comparison labels describe ordinary finite inputs; NaN behavior is not modeled.
OPS = ['YIELD','MUL','DIV','ADD','SUB','BIT_AND_INT','BIT_OR_INT',
       'BOOL_OR_INT','BOOL_AND_INT','EQ_INT','NE_INT','GT','LT','GE','LE',
       'NOT_INT','NEG','MOVE','INDEX_ADDRESS','PUSH','POP','ALLOC',
       'NOP_22','NOP_23','RETURN','JUMP_IF_ZERO','JUMP_IF_NONZERO','JUMP',
       'CALL','CALL_WAIT','SET_WAIT']

def names(blob):
    result=[]; pos=0
    while pos<len(blob):
        n=blob[pos]; pos+=1
        if not n or pos+n>len(blob): raise ValueError('Invalid counted name')
        raw=blob[pos:pos+n]; pos+=n
        if raw[-1]!=0: raise ValueError('Unterminated counted name')
        result.append(raw[:-1].decode('cp1251'))
    return result

def parse(data):
    if len(data)<56 or data[:4]!=b'RCSL': raise ValueError('Not an RCSL file')
    words=struct.unpack_from('<14i',data)
    chunks={}; chunk_offsets={}; pos=56
    while pos<len(data):
        if len(data)-pos<8: raise ValueError('Truncated chunk header')
        tag,size=struct.unpack_from('<4sI',data,pos); start=pos+8
        if size>len(data)-start: raise ValueError('Truncated chunk payload')
        key=tag.decode('ascii')
        if key in chunks: raise ValueError('Duplicate chunk')
        chunks[key]=data[start:start+size]; chunk_offsets[key]=start; pos=start+size
    functions=names(chunks.get('FUNC',b'')); defs=names(chunks.get('DEFS',b''))
    if len(functions)!=words[4] or len(defs)!=words[3]: raise ValueError('Binding count mismatch')
    code=chunks.get('CODE',b'')
    if len(code)!=words[8]*14: raise ValueError('Instruction count mismatch')
    init=chunks.get('DATA',b'')
    if len(init)!=words[5]*8: raise ValueError('DATA count mismatch')
    if len(chunks.get('STRG',b''))!=words[7]: raise ValueError('STRG size mismatch')
    initializers=[{'type':t,'slot':s,'raw_value':v,'float_value':struct.unpack('<f',struct.pack('<I',v))[0]} for t,s,v in struct.iter_unpack('<hhI',init)]
    instructions=[]
    for pc,(op,flags,a,b,c) in enumerate(struct.iter_unpack('<BBiii',code)):
        if op>=len(OPS): raise ValueError(f'Unknown opcode {op}')
        ins={'pc':pc,'file_offset':chunk_offsets['CODE']+pc*14,'opcode':op,'name':OPS[op],'flags':flags,'a':a,'b':b,'c':c}
        if flags&1: ins['a_immediate']=struct.unpack('<f',struct.pack('<i',a))[0]
        if flags&16: ins['b_immediate']=struct.unpack('<f',struct.pack('<i',b))[0]
        if op in (28,29) and a<0:
            idx=-a-1
            if idx>=len(functions): raise ValueError('Invalid external call index')
            ins['function']=functions[idx]
        instructions.append(ins)
    return {'header_words':list(words),'version':words[1],'cached_resource_count':words[2],
            'slot_count':words[6],'entry_pc':words[10],'functions':functions,'definitions':defs,
            'chunks':{k:{'file_offset':chunk_offsets[k],'size':len(v)} for k,v in chunks.items()},
            'initializers':initializers,'instructions':instructions}

def listing(script):
    lines=[f"entry={script['entry_pc']} slots={script['slot_count']} functions={script['functions']}"]
    for i in script['instructions']:
        fields=f"a={i['a']} b={i['b']} c={i['c']} flags=0x{i['flags']:02x}"
        if 'a_immediate' in i: fields+=f" a_float={i['a_immediate']:g}"
        if 'b_immediate' in i: fields+=f" b_float={i['b_immediate']:g}"
        if 'function' in i: fields+=f" external={i['function']}"
        lines.append(f"{i['pc']:04d} {i['name']:18} {fields}")
    return '\n'.join(lines)+'\n'

def main(root):
    target=root/'analysis/scripts'; target.mkdir(parents=True,exist_ok=True)
    summary=[]; usage=collections.Counter(); opcodes=collections.Counter()
    for source in sorted((root/'assets/pak1').rglob('*')):
        if source.suffix not in ('.scr','.sc'): continue
        script=parse(source.read_bytes()); relative=source.relative_to(root/'assets/pak1')
        output=target/relative; output.parent.mkdir(parents=True,exist_ok=True)
        output.with_suffix(output.suffix+'.json').write_text(json.dumps(script,indent=2),encoding='utf-8')
        output.with_suffix(output.suffix+'.txt').write_text(listing(script),encoding='utf-8')
        usage.update(script['functions']); opcodes.update(i['name'] for i in script['instructions'])
        summary.append({'path':relative.as_posix(),'version':script['version'],'entry_pc':script['entry_pc'],'instructions':len(script['instructions']),'functions':script['functions'],'definitions':script['definitions']})
    index={'scripts':summary,'script_count':len(summary),'instruction_count':sum(s['instructions'] for s in summary),'function_script_counts':dict(usage.most_common()),'opcode_counts':dict(opcodes.most_common())}
    (target/'index.json').write_text(json.dumps(index,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in index.items() if k!='scripts'},indent=2))

if __name__=='__main__': main(pathlib.Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT)
