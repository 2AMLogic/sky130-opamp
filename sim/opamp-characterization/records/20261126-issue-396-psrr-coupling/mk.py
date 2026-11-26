import re,sys
# usage: mk.py out inst:L=..:W=..:m=.. ...
src=open('/home/ubuntu/GitHub/sky130-opamp/.loom/worktrees/issue-396/design/netlist/opamp_core.spice').read()
out=sys.argv[1]
for spec in sys.argv[2:]:
    parts=spec.split(':'); inst=parts[0]
    for kv in parts[1:]:
        k,v=kv.split('=')
        pat=re.compile(r'(^'+inst+r' [^\n]*?(?:\n\+[^\n]*?)?)(?<=[ ])'+k+r'=[^ \n]+',re.M)
        # simple: operate on the instruction block
        m=re.search(r'^'+inst+r' .*(?:\n\+.*)*',src,re.M)
        blk=m.group(0); nb=re.sub(r'(?<=[ ])'+k+r'=[^ \n]+',k+'='+v,blk)
        src=src.replace(blk,nb)
open(out,'w').write(src)
