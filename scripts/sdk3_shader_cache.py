"""Expected-source-only subset of pinned Panda GLSL cache preprocessing."""
import re
POLICY_ID='panda1.10.13-observed-subset-v1'
PANDA_SHADER_CXX_SHA256='aad792a474792b1d7af5c524f8326e718a4ae4cbaecb3b844824910d2d5dccf6'
DIRECTIVES={'version','define','line','if','ifdef','ifndef','elif','else','endif','undef'}

def preprocess_cache(source):
    if not isinstance(source,str) or not source.isascii() or not 0<len(source.encode('ascii'))<=262144 or '\x00' in source:raise ValueError('bounded ASCII GLSL source')
    if '/*' in source or '\\\n' in source or '\\\r\n' in source:raise ValueError('unsupported GLSL block comment or continuation')
    lines=source.split('\n')
    if lines[-1]=='':lines.pop()
    result=[];versions=0
    for line in lines:
        code=line.split('//',1)[0].rstrip(' \t\r\v\f')
        if '"' in code or "'" in code:raise ValueError('unsupported GLSL quoted token')
        directive=re.match(r'^\s*#\s*([A-Za-z_]\w*)',code)
        if directive:
            name=directive[1]
            if name not in DIRECTIVES:raise ValueError('unsupported GLSL directive: '+name)
            if name=='version':versions+=1
        result.append(code+'\n')
    if versions!=1:raise ValueError('one GLSL version directive required')
    return ''.join(result).rstrip(' \t\r\n\v\f')+'\n'
