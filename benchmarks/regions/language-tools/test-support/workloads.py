"""Bounded correctness workloads for pinned language-tool projects."""

def run(project):
    if project == "sympy":
        import sympy as s
        x=s.symbols("x")
        for text, expected in [("(x+1)**2",x*x+2*x+1),("sin(x)**2+cos(x)**2",s.Integer(1)),("(x**3-1)/(x-1)",x*x+x+1)]: assert s.simplify(s.sympify(text)-expected) == 0
        assert s.Matrix([[1,2],[3,4]]).det() == -2
    elif project == "sqlglot":
        import sqlglot
        for sql, token in [("SELECT a+1 FROM t WHERE b>2","SELECT"),("WITH x AS (SELECT 1 AS a) SELECT a FROM x","WITH"),("SELECT * FROM UNNEST(ARRAY[1,2,3])","UNNEST")]:
            tree=sqlglot.parse_one(sql); out=tree.sql(); assert token in out and sqlglot.parse_one(out) == tree
    elif project == "libcst":
        import libcst as cst
        class Rename(cst.CSTTransformer):
            def leave_Name(self, old, updated): return updated.with_changes(value="total") if old.value == "x" else updated
        for src in ("x = 1 + 2\n", "def f(x: int):\n    return x * 2\n", "class C:\n    x = [i for i in range(3)]\n"):
            module=cst.parse_module(src); assert cst.parse_module(module.code).deep_equals(module); assert "total" in module.visit(Rename()).code
    elif project == "astroid":
        import astroid
        for src,name,expected in [("x=1+2","x",3),("def f(a): return a*2\ny=f(4)","y",8),("class C:\n x=5\nz=C().x","z",5)]:
            module=astroid.parse(src); node=next(n for n in module.nodes_of_class(astroid.nodes.AssignName) if n.name==name); values=list(node.infer()); assert values and values[0].value == expected
    elif project == "jinja":
        from jinja2 import Environment, DictLoader
        env=Environment(loader=DictLoader({"base":"<{% block b %}{% endblock %}>","child":"{% extends 'base' %}{% block b %}{{ xs|map('upper')|join(',') }}{% endblock %}"}),autoescape=True)
        for xs,expected in [(["a","b"],"<A,B>"),([],"<>"),(["<x>"],"<&lt;X&gt;>")]: assert env.get_template("child").render(xs=xs) == expected
    elif project == "pyparsing":
        import pyparsing as pp
        integer=pp.pyparsing_common.signed_integer; expr=pp.infix_notation(integer,[(pp.one_of("* /"),2,pp.opAssoc.LEFT),(pp.one_of("+ -"),2,pp.opAssoc.LEFT)])
        for text,expected in [("1+2*3",[[1,"+",[2,"*",3]]]),("-4+9",[[-4,"+",9]]),("8/2-1",[[[8,"/",2],"-",1]])]: assert expr.parse_string(text,parse_all=True).as_list() == expected
        assert pp.DelimitedList(pp.Word(pp.alphas)).parse_string("red,green,blue",parse_all=True).as_list() == ["red","green","blue"]
    elif project == "lark":
        from lark import Lark, Tree
        parser=Lark('?start: sum\n?sum: atom ("+" atom)*\n?atom: NUMBER -> number\n%import common.NUMBER\n%import common.WS\n%ignore WS',parser="lalr")
        for text,count in [("1",1),("1+2",2),("1 + 2 + 30",3)]:
            tree=parser.parse(text); assert isinstance(tree,Tree); assert len(list(tree.scan_values(lambda x: getattr(x,"type",None)=="NUMBER"))) == count
    elif project == "cython":
        from Cython.Compiler.TreeFragment import parse_from_strings
        from Cython.Compiler.Nodes import CClassDefNode, DefNode, ForInStatNode, ReturnStatNode, StatListNode
        function=parse_from_strings("a.pyx","def f(int x):\n return x+1\n")
        assert isinstance(function.body,DefNode) and function.body.name == "f" and function.body.num_required_args == 1
        assert function.body.args[0].declarator.name == "x" and function.body.args[0].base_type.name == "int"
        assert isinstance(function.body.body,ReturnStatNode)
        loop=parse_from_strings("b.pyx","cdef int s=0\nfor i in range(4): s+=i\n")
        assert isinstance(loop.body,StatListNode) and len(loop.body.stats) == 2 and isinstance(loop.body.stats[1],ForInStatNode)
        assert loop.body.stats[1].target.name == "i" and loop.body.stats[1].iterator.sequence.function.name == "range"
        extension=parse_from_strings("c.pyx","cdef class C:\n cdef int x\n")
        assert isinstance(extension.body,CClassDefNode) and extension.body.class_name == "C"
        assert extension.body.body.declarators[0].name == "x" and extension.body.body.base_type.name == "int"
    else: raise AssertionError(project)
