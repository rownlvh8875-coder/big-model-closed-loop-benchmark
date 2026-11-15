"""Two tiny parent challenges, not scientific image/model equivalence."""
import base64,hashlib,re
def need(v,m='real GLX contract rejected'):
 if not v:raise ValueError(m)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def challenge(nonce,index):
 need(type(nonce) is str and re.fullmatch('[0-9a-f]{32}',nonce) and type(index) is int and index in (0,1),'frame challenge scope');h=hashlib.sha256(('panda-real-glx-v1:'+nonce).encode()).digest();return [32+v%64+128*index for v in h[:3]]
def frame_packet(raw,nonce,index):
 need(type(raw) is bytes,'RGB bytes');return dict(schema='panda-real-glx-frame-v1',nonce=nonce,index=index,width=8,height=8,channels=3,render_calls=2,ram_reads=1,nbytes=len(raw),sha256=sha(raw),base64=base64.b64encode(raw).decode())
def validate_frame(frame,nonce,index):
 rgb=challenge(nonce,index)
 for name,want in dict(nonce=nonce,index=index,width=8,height=8,channels=3,render_calls=2,ram_reads=1,nbytes=192).items():need(type(frame.get(name)) is type(want) and frame[name]==want,'frame field: '+name)
 raw=base64.b64decode(frame['base64'],validate=True);need(len(raw)==192 and sha(raw)==frame['sha256'],'frame payload identity');need(all(abs(value-rgb[i%3])<=1 for i,value in enumerate(raw)),'fresh challenged color');return raw
