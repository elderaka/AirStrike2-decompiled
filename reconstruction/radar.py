"""Semantic reconstruction of radar.scr and its rotatez engine binding.

Recovered from radar.scr and AirStrike2.exe VAs 0x427f40, 0x4268f0,
0x426f10. This does not execute any original machine code and is not a
complete script VM. The angle unit/convention remains unverified.
Run this file to check the recovered behavior against the script fixture.
"""
from dataclasses import dataclass
import pathlib, struct, sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from decode_scripts import parse

def f32(value):
    return struct.unpack('<f',struct.pack('<f',value))[0]

@dataclass
class ScriptContext:
    angle_z: float = 0.0

def rotatez(context, rate, frametime):
    # Original: context+0x40 += parameter[0] * global frame_seconds.
    # Store rounding is modeled. Full x87 extended-precision equivalence is not.
    context.angle_z=f32(f32(context.angle_z)+f32(rate)*f32(frametime))

def radar_frame(context, frametime):
    rotatez(context, 60.0, frametime)

def check():
    fixture=ROOT/'assets/pak1/scripts/radar.scr'
    script=parse(fixture.read_bytes()); code=script['instructions']
    assert script['entry_pc']==0 and script['functions']==['rotatez']
    assert len(code)==3
    assert (code[0]['opcode'],code[0]['flags'],code[0]['a'],code[0]['b_immediate'])==(17,16,0,60.0)
    assert (code[1]['opcode'],code[1]['a'],code[1]['b'],code[1]['function'])==(28,-1,0,'rotatez')
    assert code[2]['opcode']==0
    context=ScriptContext()
    radar_frame(context,0.1); assert abs(context.angle_z-6.0)<0.00001
    for _ in range(9): radar_frame(context,0.1)
    assert abs(context.angle_z-60.0)<0.0001
    paused=ScriptContext(12.5); radar_frame(paused,0); assert paused.angle_z==12.5
    back=ScriptContext(12); rotatez(back,-60,0.1); assert abs(back.angle_z-6)<0.00001
    print('PASS: binary script fixture matches reconstructed radar; elapsed-time rotation, zero step, and negative rate checks passed.')

if __name__=='__main__': check()
