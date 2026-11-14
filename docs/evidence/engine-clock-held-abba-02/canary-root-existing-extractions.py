import ast
from pathlib import Path
p=Path('/tmp/accept-held-abba-v2-canary.py')
class ExistingOriginals(ast.NodeTransformer):
    def visit_Expr(self,node):
        if isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Attribute) and node.value.func.attr in ('mkdir','write_bytes','chmod'):return None
        return self.generic_visit(node)
    def visit_With(self,node):
        for item in node.items:
            c=item.context_expr
            if isinstance(c,ast.Call) and isinstance(c.func,ast.Attribute) and c.func.attr=='open' and c.args and isinstance(c.args[0],ast.Constant) and c.args[0].value in ('xb','wb'):
                return None
        return self.generic_visit(node)
namespace={};tree=ExistingOriginals().visit(ast.parse(p.read_text()));ast.fix_missing_locations(tree)
exec(compile(tree,str(p),'exec'),namespace)
out=namespace['out'];report=namespace['report'];n=namespace['n']
with (out/'root-acceptance.json').open('xb') as f:f.write(n.canonical(report))
print('ALL_ROOT_ASSERTIONS_RECHECKED_WITH_EXISTING_ORIGINAL_EXTRACTIONS; corrected only root metadata expected_context argument; failed metadata-selected prefix preserved')
