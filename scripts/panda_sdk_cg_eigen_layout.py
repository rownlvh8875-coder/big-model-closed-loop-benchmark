"""Extract a bounded relocation-free literal section from inert compiler object DATA."""
import struct
from scripts import panda_sdk_cg_eigen_inputs as inputs
need=inputs.need;sha=inputs.sha
MAGIC=0x50414e4441434732;SECTION=b'.panda_cg_layout_v2'
def extract_literal(raw):
 need(type(raw) is bytes and 64<=len(raw)<=1024**2 and raw[:6]==b'\x7fELF\x02\x01','bounded ELF64LE parent');h=struct.unpack_from('<16sHHIQQQIHHHHHH',raw);need(h[1:4]==(1,62,1) and h[4]==h[5]==0 and h[8]==64 and h[10]==0 and h[11]==64 and 1<=h[12]<=256 and 0<h[13]<h[12],'AMD64 relocatable DATA parent');off=h[6];end=off+64*h[12];need(64<=off and end<=len(raw),'parent section table');sections=[struct.unpack_from('<IIQQQQIIQQ',raw,off+64*i) for i in range(h[12])];need(sections[0]==(0,)*10,'null section');strings=sections[h[13]];need(strings[1]==3 and strings[5]<=65536 and 64<=strings[4] and strings[4]+strings[5]<=len(raw),'bounded names');names=raw[strings[4]:strings[4]+strings[5]];need(names[:1]==names[-1:]==b'\0','terminated names');selected=[];spans=[];labels=[]
 for i,s in enumerate(sections):
  need(s[0]<len(names),'section name offset');nend=names.find(b'\0',s[0]);need(s[0]<=nend<=s[0]+512,'bounded section name');name=names[s[0]:nend];labels.append(name)
  if i:
   need(s[4]<=len(raw) and (s[1]==8 or s[4]+s[5]<=len(raw)),'section file bounds')
   if s[1]!=8 and s[5]:need(64<=s[4] and (s[4]+s[5]<=off or s[4]>=end),'metadata alias');spans.append((s[4],s[4]+s[5]))
  if name==SECTION:need(s[1]==1 and s[2]==2 and s[3]==0 and s[5]==128 and s[6]==s[7]==s[9]==0 and 8<=s[8]<=4096 and s[8]&(s[8]-1)==0 and s[4]%8==0,'fixed read-only literal section');selected.append(i)
 spans.sort();need(all(a[1]<=b[0] for a,b in zip(spans,spans[1:])),'overlapping parent sections');need(len(selected)==1,'unique literal section');index=selected[0]
 for i,s in enumerate(sections):
  if s[1] not in (4,9):continue
  unit=24 if s[1]==4 else 16;need(s[9]==unit and s[5]%unit==0 and 0<s[6]<len(sections) and 0<s[7]<len(sections),'relocation associations');target=sections[s[7]];symbols=sections[s[6]];need(symbols[1] in (2,11) and symbols[9]==24 and symbols[5]%24==0,'relocation symbol table');need(labels[i]==(b'.rela' if s[1]==4 else b'.rel')+labels[s[7]],'relocation name/info binding');need(s[7]!=index or s[5]==0,'literal section has relocations')
  for pos in range(s[4],s[4]+s[5],unit):
   address,info=struct.unpack_from('<QQ',raw,pos);need(address<target[5] and info>>32<symbols[5]//24,'relocation target/symbol extent')
 s=sections[index];literal=raw[s[4]:s[4]+128];return dict(schema='panda-cg-eigen-literal-extraction-v2',raw=literal,parent_sha256=sha(raw),parent_nbytes=len(raw),section_index=index,section_offset=s[4],section_nbytes=128,section_sha256=sha(literal),targeting_relocations=0,parent_loaded=False,target_execution=False)
def validate_descriptor(raw):
 need(type(raw) is bytes and len(raw)==128,'fixed128byte descriptor');w=struct.unpack('<16Q',raw);need(w[:5]==(MAGIC,2,8,0,1) and w[12:]==(1,1,16,16),'descriptor ABI/Cg/effective Eigen/alignment');need(32<=w[5]<=2**20 and all(0<v<=2**20 for v in w[6:9]),'measured class sizes');need(w[9]+8<=w[8] and w[10]+4<=w[8] and w[11]+4<=w[8],'member bounds');return dict(schema='panda-cg-eigen-layout-v2',descriptor_sha256=sha(raw),shader_caps_size=w[5],graphics_pipe_size=w[6],gsg_size=w[7],gl_gsg_size=w[8],offsets=dict(vendor=w[9],major=w[10],minor=w[11]),have_eigen=True,effective_linmath_align=True,vector_alignment=w[14],memory_alignment=w[15],target_execution=False)
def verify_pair(parent,raw):
 r=extract_literal(parent);need(r['raw']==raw,'raw descriptor/parent substitution');return validate_descriptor(raw)
