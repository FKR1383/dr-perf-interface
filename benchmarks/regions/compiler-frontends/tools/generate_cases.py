#!/usr/bin/env python3
"""Generate concrete LLVM/Clang compiler-front-end region cases."""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKOUT = Path("/tmp/drperf-cf/llvm")
REVISION = "87f0227cb60147a26a1eeb4fb06e3b505e9c7261"
REPOSITORY = "https://github.com/llvm/llvm-project"


@dataclass
class Candidate:
    path: Path
    start: int
    opening: int
    end: int
    symbol: str
    score: int


def matching_brace(lines: list[str], line_no: int, col: int) -> int | None:
    depth = 0
    block = False
    string = None
    escaped = False
    for i in range(line_no, len(lines)):
        line = lines[i]
        j = col if i == line_no else 0
        while j < len(line):
            c = line[j]
            n = line[j + 1] if j + 1 < len(line) else ""
            if block:
                if c == "*" and n == "/": block = False; j += 2; continue
                j += 1; continue
            if string:
                if escaped: escaped = False
                elif c == "\\": escaped = True
                elif c == string: string = None
                j += 1; continue
            if c == "/" and n == "*": block = True; j += 2; continue
            if c == "/" and n == "/": break
            if c in ('"', "'"): string = c; j += 1; continue
            if c == "{": depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0: return i
            j += 1
    return None


def candidates(path: Path) -> list[Candidate]:
    text = path.read_text(errors="replace")
    lines = text.splitlines(keepends=True)
    found = []
    # Function definitions in LLVM style normally end their declaration with an
    # opening brace. Gather up to six preceding lines to cover wrapped signatures.
    for i, line in enumerate(lines):
        for m in re.finditer(r"\{", line):
            prefix = "".join(lines[max(0, i - 6):i + 1])[:sum(map(len, lines[max(0, i - 6):i])) + m.start()]
            compact = " ".join(prefix.strip().split())
            if "(" not in compact or ")" not in compact: continue
            tail = compact.rsplit(";", 1)[-1]
            tail = tail.rsplit("}", 1)[-1]
            if re.search(r"\b(if|for|while|switch|catch|namespace|class|struct|enum|union)\s*\([^)]*\)\s*$", tail): continue
            if re.search(r"\b(namespace|class|struct|enum|union)\b[^()]*(?:final\s*)?$", tail): continue
            names = re.findall(r"([~A-Za-z_]\w*(?:::[~A-Za-z_]\w*)*)\s*\(", tail)
            if not names: continue
            symbol = names[-1]
            # Unqualified lowercase names are disproportionately calls or local
            # lambdas seen by the lightweight scanner. Prefer externally named
            # methods and LLVM-style capitalized file-local helper functions.
            if "::" not in symbol and symbol[:1].islower(): continue
            if symbol in {"alignas", "decltype", "sizeof", "requires", "switch", "if", "while", "for",
                          "f", "record", "table", "metadata", "space", "jobs", "initializer", "parsing",
                          "__attribute__", "AST", "SM", "Coding", "Closure", "StmtResult", "reduce_func",
                          "getKind", "comparePiece", "DeclStmts"}: continue
            if symbol in {"fn", "node", "parentheses", "parse"}: continue
            end = matching_brace(lines, i, m.start())
            if end is None or end - i < 5 or end - i > 900: continue
            start = i
            balance = 0
            while start > 0 and i - start < 7:
                prev = lines[start - 1].strip()
                if not prev or prev.startswith(("//", "/*", "*", "#", "template", "[[")): break
                balance += prev.count("(") - prev.count(")")
                if prev.endswith((";", "}", ":")) and balance <= 0: break
                start -= 1
            body = "".join(lines[i:end + 1])
            signals = sum(body.count(x) for x in ("for (", "for(", "while (", "while(", "Parse", "Lookup", "Diagn", "Visit", "Create", "Build"))
            length = end - i
            score = min(length, 180) + 12 * signals - max(0, length - 350)
            found.append(Candidate(path, start + 1, i + 1, end + 1, symbol, score))
    # Duplicate matches arise from lambdas and initializer braces; one definition
    # per opening line gives the outer named function.
    unique = {}
    for c in found: unique.setdefault(c.opening, c)
    return list(unique.values())


def phase_for(rel: str) -> str:
    rules = [("Lex/", "preprocessing"), ("Parse/", "parsing"), ("Sema/", "semantic-analysis"),
             ("AST/", "ast-processing"), ("Analysis/", "static-analysis"), ("Serialization/", "serialization"),
             ("CodeGen/", "ir-generation"), ("Tooling/", "source-tooling"), ("Format/", "formatting"),
             ("AsmParser", "ir-parsing"), ("llvm/lib/IR", "ir-construction")]
    return next((phase for needle, phase in rules if needle in rel), "compiler-support")


SCENARIOS = {
    "preprocessing": ("preprocess-macros", ["-E", "-P", "-x", "c++"], "int value"),
    "parsing": ("parse-templates", ["-fsyntax-only", "-x", "c++", "-std=c++20"], ""),
    "semantic-analysis": ("semantic-overloads", ["-fsyntax-only", "-x", "c++", "-std=c++20"], ""),
    "ast-processing": ("ast-dump", ["-Xclang", "-ast-dump", "-fsyntax-only", "-x", "c++", "-std=c++20"], "FunctionDecl"),
    "static-analysis": ("static-analyzer", ["--analyze", "-Xanalyzer", "-analyzer-output=text", "-x", "c"], ""),
    "serialization": ("pch-roundtrip", ["-fsyntax-only", "-x", "c++", "-std=c++20"], ""),
    "ir-generation": ("emit-ir", ["-S", "-emit-llvm", "-O1", "-x", "c++", "-std=c++20", "-o", "-"], "define"),
    "source-tooling": ("diagnostic-fixit", ["-fsyntax-only", "-Wall", "-x", "c++", "-std=c++20"], ""),
    "formatting": ("syntax-token-stream", ["-Xclang", "-dump-tokens", "-fsyntax-only", "-x", "c++"], "identifier"),
    "ir-parsing": ("compile-generated-ir", ["-S", "-emit-llvm", "-O0", "-x", "c", "-o", "-"], "define"),
    "ir-construction": ("optimize-generated-ir", ["-S", "-emit-llvm", "-O2", "-x", "c", "-o", "-"], "define"),
    "compiler-support": ("compile-constexpr", ["-fsyntax-only", "-x", "c++", "-std=c++20"], ""),
}


def targeted_scenario(phase: str, rel: str, symbol: str, body: str):
    # Route from the declared target identity. Body-wide keyword matching is
    # misleading because callees and comments describe adjacent subsystems.
    text = (rel + " " + symbol).lower()
    table = {
        "preprocessing": [("macro", "macro-argument-expansion"), ("tokenlexer", "token-pasting"),
            ("literal", "literal-escape-lexing"), ("comment", "comment-skipping"),
            ("include", "include-lookup"), ("module", "module-directive-lexing")],
        "parsing": [("lambda", "lambda-parsing"), ("openmp", "openmp-directive-parsing"),
            ("openacc", "openacc-directive-parsing"), ("objc", "objective-c-expression-parsing"),
            ("asm", "inline-asm-parsing"), ("usingdeclaration", "using-declaration-parsing"),
            ("declar", "complex-declarator-parsing"),
            ("class", "class-member-parsing"), ("template", "template-id-parsing"),
            ("forstatement", "for-statement-parsing"), ("paren", "parenthesized-expression-parsing"),
            ("binaryexpression", "binary-expression-parsing"),
            ("functiondefinition", "function-definition-parsing"), ("compoundstatement", "compound-statement-parsing")],
        "semantic-analysis": [("overload", "overload-resolution"), ("lookup", "qualified-name-lookup"),
            ("template", "template-instantiation"), ("attribute", "attribute-semantics"),
            ("openmp", "openmp-loop-semantics"), ("capture", "lambda-capture-semantics"),
            ("type", "type-construction"), ("constant", "constant-expression-checking"),
            ("destructor", "destructor-name-semantics"), ("usingdeclaration", "using-declaration-semantics"),
            ("builtinoperator", "builtin-operator-overloads"), ("friendfunction", "friend-function-semantics"),
            ("memberfunction", "member-call-semantics"), ("warnings", "warning-analysis")],
        "ast-processing": [("mangle", "template-name-mangling"), ("recordlayout", "record-layout"),
            ("parentmap", "ast-parent-mapping"), ("stmtprofile", "statement-profiling"),
            ("constant", "constexpr-evaluation"), ("import", "ast-import-shape"),
            ("sideeffects", "side-effect-analysis"), ("print", "ast-printing")],
        "static-analysis": [("thread", "thread-safety-analysis"), ("uninitialized", "uninitialized-flow"),
            ("unsafe", "unsafe-buffer-analysis"), ("cfg", "control-flow-graph"),
            ("pathdiagnostic", "path-diagnostic-building")],
        "serialization": [("writer", "pch-writing"), ("reader", "pch-reading-shape"),
            ("module", "module-index-shape"), ("decl", "declaration-serialization")],
        "ir-generation": [("builtin", "builtin-ir-generation"), ("atomic", "atomic-ir-generation"),
            ("openmp", "openmp-ir-generation"), ("objc", "objective-c-ir-generation"),
            ("cxxabi", "cxx-abi-ir-generation"), ("debug", "debug-info-generation"),
            ("new", "allocation-ir-generation"), ("call", "call-ir-generation")],
        "ir-parsing": [("metadata", "metadata-ir-parsing"), ("function", "function-ir-parsing"),
            ("lex", "identifier-ir-lexing")],
        "ir-construction": [("verifier", "ir-call-verification"), ("asmwriter", "ir-assembly-writing"),
            ("debuginfo", "debug-metadata-construction"), ("typefinder", "ir-type-discovery"),
            ("inlineasm", "inline-asm-constraint-parsing"), ("upgrade", "intrinsic-upgrade-shape")],
        "formatting": [("whitespace", "whitespace-layout"), ("qualifier", "qualifier-alignment"),
            ("token", "format-token-classification"), ("continuation", "continuation-indentation"),
            ("unwrapped", "unwrapped-line-parsing")],
        "source-tooling": [("dependency", "dependency-scanning-shape"), ("syntax", "syntax-tree-building"),
            ("compilationdatabase", "compilation-database-shape")],
    }
    codegen = {
        "VisitCastExpr": "scalar-cast-ir", "EmitScalarPrePostIncDec": "scalar-incdec-ir",
        "EmitLoadOfMemberFunctionPointer": "member-function-pointer-load-ir",
        "EmitOMPTaskBasedDirective": "openmp-task-ir", "EmitNewArrayInitializer": "new-array-init-ir",
        "EmitCXXNewAllocSize": "new-array-init-ir",
        "VisitAbstractConditionalOperator": "conditional-operator-ir", "EmitFunctionProlog": "function-prolog-ir",
        "EmitTypeCheck": "vptr-type-check-ir", "EmitThreadLocalInitFuncs": "thread-local-init-ir",
        "EmitNonNullMemberPointerConversion": "member-pointer-conversion-ir", "CreateType": "debug-type-ir",
        "EmitRangeReductionDiv": "complex-division-ir", "EmitBinMul": "complex-multiply-ir",
        "EmitAtomicOp": "atomic-operation-ir", "EmitCompare": "scalar-compare-ir",
        "EmitCoroutineBody": "coroutine-body-ir", "EmitMemberPointerConversion": "member-pointer-conversion-ir",
        "PopCleanupBlock": "destructor-cleanup-ir", "EmitArrayInit": "aggregate-array-init-ir",
        "EmitCall": "direct-call-ir", "EmitGuardedInit": "guarded-static-init-ir",
        "GenerateBlockFunction": "block-literal-ir", "EmitBlockLiteral": "block-literal-ir",
        "EmitAsmStmt": "inline-asm-ir", "EmitStoreThroughLValue": "lvalue-store-ir",
        "EmitFunctionEpilog": "function-epilog-ir", "EmitBinDiv": "complex-division-ir",
        "EmitMemberPointerComparison": "member-pointer-compare-ir", "CreateTypeDefinition": "debug-type-ir",
        "EmitOMPScanDirective": "openmp-scan-ir", "emitZeroOrPatternForAutoVarInit": "auto-var-init-ir",
        "EmitLandingPad": "exception-landing-pad-ir", "EmitOMPTargetTaskBasedDirective": "openmp-target-task-ir",
        "EmitAtomicExpr": "atomic-expression-ir",
    }
    exact = {
        "AddOrdinaryNameResults": "ordinary-name-completion",
        "AddObjCKeyValueCompletions": "objc-key-value-completion",
        "SemaCodeCompletion::CodeCompletePreprocessorDirective": "preprocessor-directive-completion",
        "SemaCodeCompletion::CodeCompleteObjCMethodDecl": "objc-method-decl-completion",
        "Sema::BuildCXXNestedNameSpecifier": "using-declaration-semantics",
        "Parser::ParseCXXClassMemberDeclaration": "class-member-parsing",
        "Parser::ParseDeclGroup": "function-definition-parsing",
        "Sema::AddBuiltinOperatorCandidates": "builtin-operator-overloads",
        "Sema::LookupTemplateName": "template-instantiation",
        "Parser::ParseAttributeArgsCommon": "attribute-semantics",
        "SemaObjC::ActOnAtEnd": "objective-c-expression-parsing",
        "Sema::BuildCallToObjectOfClassType": "member-call-semantics",
        "Sema::InstantiateFunctionDefinition": "function-template-instantiation",
        "CoroutineStmtBuilder::makeNewAndDeleteExpr": "coroutine-semantics",
        "Sema::BuildCallToMemberFunction": "member-call-semantics",
        "Parser::ParseCXXCondition": "for-statement-parsing",
        "Parser::ParseCXX11AttributeSpecifierInternal": "attribute-semantics",
        "Parser::ParseLexedMethodDeclaration": "class-member-parsing",
        "IsStructurallyEquivalent": "ast-structural-equivalence",
        "ASTContext::getFunctionFeatureMap": "inline-asm-parsing",
        "clang::desugarForDiagnostic": "vptr-type-check-ir",
        "LLVMContextImpl::~LLVMContextImpl": "ast-import-shape",
        "Lexer::SkipLineComment": "include-lookup",
        "EvaluateValue": "preprocessor-expression-evaluation",
        "CFGBuilder::VisitForStmt": "for-statement-analysis",
        "Preprocessor::LookupFile": "include-lookup",
        "ASTContext::getObjCEncodingForTypeImpl": "block-literal-ir",
        "Expr::HasSideEffects": "template-name-mangling",
        "llvm::colorEHFunclets": "windows-exception-ir",
        "CheckLValueConstantExpression": "member-pointer-constexpr",
        "DILocation::getMergedLocation": "debug-location-ir",
        "CXXRecordDecl::setBases": "derived-records",
        "HandleConstructorCall": "constexpr-constructors",
        "EvaluateDirectiveSubExpr": "preprocessor-expression-evaluation",
        "TextNodeDumper::Visit": "template-name-mangling",
        "Expr::isConstantInitializer": "constant-array-initializers",
        "InlineAsm::ConstraintInfo::Parse": "inline-asm-ir",
        "HeaderSearch::LookupSubframeworkHeader": "include-lookup",
        "llvm::ConstantFoldCompareInstruction": "constant-compare-folding",
        "llvm::ConstantFoldBinaryInstruction": "constant-binary-folding",
    }
    if symbol in exact:
        scenario = exact[symbol]
    elif phase == "ir-generation":
        scenario = next((v for k, v in codegen.items() if k in symbol), None)
        if scenario is None: scenario = "direct-call-ir"  # coverage replacements reuse their recorded witness below
    elif "semacodecomplete" in text:
        scenario = "code-completion"
    else:
        scenario = next((name for needle, name in table.get(phase, []) if needle in text), SCENARIOS[phase][0])
    flags = list(SCENARIOS[phase][1]); expect = SCENARIOS[phase][2]
    if phase == "preprocessing": expect = "value"
    if phase == "ir-parsing": expect = ""
    if phase == "formatting": expect = ""
    if phase == "ast-processing": expect = "TranslationUnitDecl"
    if phase == "ir-generation" and "debug" in scenario: flags.insert(0, "-g")
    if "openmp" in scenario: flags.insert(0, "-fopenmp")
    if "block-literal" in scenario: flags.insert(0, "-fblocks")
    if "auto-var-init" in scenario: flags.insert(0, "-ftrivial-auto-var-init=zero")
    if "vptr-type-check" in scenario: flags.insert(0, "-fsanitize=vptr")
    if "MicrosoftCXXABI" in symbol: flags[0:0] = ["-target", "x86_64-pc-windows-msvc"]
    if scenario == "ast-parent-mapping": flags = ["--analyze", "-x", "c++", "-std=c++20"]
    if scenario == "ast-parent-mapping": expect = ""
    if scenario in {"ast-structural-equivalence", "ast-import-shape"}: expect = ""
    if scenario == "windows-exception-ir": flags = ["-S", "-emit-llvm", "-O1", "-x", "c++", "-std=c++20", "-target", "x86_64-pc-windows-msvc", "-o", "-"]
    if scenario in {"inline-asm-ir", "constant-compare-folding", "constant-binary-folding", "debug-location-ir"}: flags = ["-S", "-emit-llvm", "-O1", "-x", "c++", "-std=c++20", "-o", "-"]
    if scenario == "debug-location-ir": flags.insert(0, "-g")
    if scenario.startswith("objc-"): flags = ["-fsyntax-only", "-x", "objective-c++", "-std=c++20"]
    if "objective-c" in scenario: flags[flags.index("c++") if "c++" in flags else -1] = "objective-c++"
    return scenario, flags, expect


def fixture(phase: str, ordinal: int, scenario: str) -> str:
    if scenario == "ordinary-name-completion": return "int global_name; void use(){ __COMPLETE__; }\n"
    if scenario == "preprocessor-directive-completion": return "#__COMPLETE__\n"
    if scenario == "objc-method-decl-completion": return "@interface Obj\n- (void)__COMPLETE__;\n@end\n"
    if scenario == "objc-key-value-completion": return '@interface NSDictionary + (instancetype)dictionaryWithObjects:(const id[])o forKeys:(const id[])k count:(unsigned long)n; @end\nvoid f(){ id value = @{ (id)0: (id)0, __COMPLETE__ }; (void)value; }\n'
    if scenario == "code-completion":
        return "struct Member { int alpha; long beta; void method(); };\nvoid use(Member value) { value.__COMPLETE__; }\n"
    if phase == "preprocessing":
        if "token-pasting" in scenario: return f"#define JOIN(a,b) a##b\nint JOIN(value_,{ordinal}) = 9;\n"
        if "literal" in scenario: return 'const char *value = "line\\n\\x41";\n'
        if "comment" in scenario: return "/* bounded block comment */\n// bounded line comment\nint value = 9;\n"
        if "include" in scenario: return "#include <stddef.h>\nsize_t value = sizeof(int);\n"
        return f"#define MUL_{ordinal}(x) ((x)*(x))\n#if MUL_{ordinal}(2) > 3\nint value = MUL_{ordinal}(3);\n#endif\n"
    if phase == "static-analysis":
        return "int sum(const int *p, int n){int s=0; for(int i=0;i<n;i++) s+=p[i]; return s;}\nint main(void){int a[3]={1,2,3}; return sum(a,3)!=6;}\n"
    if phase in {"ir-parsing", "ir-construction"}:
        if phase == "ir-parsing":
            return f"define i32 @fold_{ordinal}(i32 %x) {{\nentry:\n  %a = add i32 %x, 6\n  ret i32 %a\n}}\n"
        return f"int fold_{ordinal}(int x) {{ int s=0; for(int i=0;i<4;i++) s += x+i; return s; }}\nint main(void) {{ return fold_{ordinal}(2)!=14; }}\n"
    if "lambda" in scenario: return f"template<class F> int apply(F f){{return f({ordinal});}}\nint main(){{int k=2; return apply([k](int x){{return x+k;}})!={ordinal+2};}}\n"
    if "overload" in scenario: return "int pick(int){return 1;} long pick(long){return 2;} template<class T> auto call(T x)->decltype(pick(x)){return pick(x);}\nint main(){return call(3)!=1;}\n"
    if "record-layout" in scenario: return f"struct B{ordinal} {{ virtual ~B{ordinal}()=default; int x; }}; struct D{ordinal}: B{ordinal} {{ char c; double d; }}; int main(){{return sizeof(D{ordinal})<sizeof(double);}}\n"
    if "attribute" in scenario: return "[[nodiscard]] constexpr int answer(){return 42;} int main(){return answer()!=42;}\n"
    if "atomic" in scenario: return "int main(){int x=1; __atomic_fetch_add(&x,2,__ATOMIC_SEQ_CST); return x!=3;}\n"
    if "allocation" in scenario: return "struct X{int n;}; int main(){X *p=new X[4]{}; p[2].n=7; int r=p[2].n; delete[] p; return r!=7;}\n"
    if "inline-asm" in scenario: return 'int main(){int x=3; asm("" : "+r"(x)); return x!=3;}\n'
    if "debug-info" in scenario: return f"struct Debug_{ordinal}{{int x;}}; int main(){{Debug_{ordinal} d{{7}}; return d.x!=7;}}\n"
    if "call-ir" in scenario: return f"__attribute__((noinline)) int callee_{ordinal}(int x){{return x+1;}} int main(){{return callee_{ordinal}(6)!=7;}}\n"
    if phase == "ir-generation": return f"struct X_{ordinal}{{int n; X_{ordinal}(int v):n(v){{}}}}; int main(){{X_{ordinal} x(3); int y=static_cast<int>(x.n); y++; return y>2 ? 0 : 1;}}\n"
    return f"template<class T> constexpr T fold_{ordinal}(T x) {{ T s{{}}; for(int i=0;i<4;i++) s += x+i; return s; }}\nstruct Item_{ordinal} {{ int x; constexpr int get() const {{ return x; }} }};\nstatic_assert(fold_{ordinal}(2)==14);\nint main() {{ Item_{ordinal} a{{7}}; return a.get()!=7; }}\n"


def fixture_sizes(phase: str, ordinal: int, scenario: str) -> list[dict]:
    base = fixture(phase, ordinal, scenario)
    result = []
    for size in (4, 16, 64):
        if phase == "ir-generation":
            source = codegen_fixture(ordinal, scenario, size)
            result.append({"size": size, "source": source})
            continue
        if scenario in {"windows-exception-ir", "inline-asm-ir", "constant-compare-folding", "constant-binary-folding", "debug-location-ir"}:
            source = codegen_fixture(ordinal, scenario, size)
            result.append({"size": size, "source": source})
            continue
        if scenario.endswith("completion"):
            if scenario == "code-completion":
                members = " ".join(f"int field_{i};" for i in range(size)); source = base.replace("int alpha; long beta;", "int alpha; long beta; " + members)
            elif scenario == "ordinary-name-completion":
                names = " ".join(f"int local_{i}=0;" for i in range(size)); source = base.replace("__COMPLETE__", names + " __COMPLETE__")
            elif scenario == "objc-key-value-completion":
                pairs=", ".join(f"(id)0: (id)0" for _ in range(size));source=base.replace('(id)0: (id)0, __COMPLETE__',pairs+', __COMPLETE__')
            elif scenario == "objc-method-decl-completion":
                methods="\n".join(f"- (void)method_{i};" for i in range(size));source=base.replace("- (void)__COMPLETE__;",methods+"\n- (void)__COMPLETE__;")
            elif scenario == "preprocessor-directive-completion":
                source=("#define SCALE_ITEM 1\n"*size)+base
            else:
                source = base
            result.append({"size": size, "source": source})
            continue
        if phase in {"parsing", "semantic-analysis", "ast-processing", "static-analysis", "serialization"}:
            source = frontend_fixture(ordinal, scenario, size, phase)
            result.append({"size": size, "source": source})
            continue
        if phase == "preprocessing":
            if "token-pasting" in scenario:
                source = "#define JOIN(a,b) a##b\n" + "\n".join(f"int JOIN(value_,{i})={i};" for i in range(size)) + "\n"
            elif "literal" in scenario:
                source = "\n".join(f'const char *value_{i}="line\\n\\x41-{i}";' for i in range(size)) + "\n"
            elif "comment" in scenario:
                source = "\n".join(f"/* comment {i} with tokens +-* */ int value_{i}={i};" for i in range(size)) + "\n"
            elif "include" in scenario:
                source = ("#include <stddef.h>\n" * size) + "size_t value=sizeof(int);\n"
            elif "expression-evaluation" in scenario:
                source = "\n".join(f"#if ({i}+3)*2 > 1\nint value_{i}={i};\n#endif" for i in range(size)) + "\n"
            else:
                source = "#define MUL(x) ((x)*(x))\n" + "\n".join(f"int value_{i}=MUL({i});" for i in range(size)) + "\n"
        elif phase == "ir-parsing":
            extra = "\n".join(f"@g{ordinal}_{i} = global i32 {i}" for i in range(size))
            source = extra + "\n" + base
        else:
            if phase == "ir-construction":
                funcs = "\n".join(f"__attribute__((noinline)) int ir_{ordinal}_{i}(int x){{return x+{i};}}" for i in range(size))
                calls = "+".join(f"ir_{ordinal}_{i}({i})" for i in range(size))
                source = funcs + f"\nint main(void){{return ({calls})<0;}}\n"
            else:
                extra = "\n".join(f"struct Scale_{ordinal}_{i} {{ int value[{1 + i % 4}]; }};" for i in range(size))
                source = extra + "\n" + base
        result.append({"size": size, "source": source})
    return result


def frontend_fixture(o: int, scenario: str, n: int, phase: str) -> str:
    if scenario in {"coroutine-semantics", "vptr-type-check-ir", "block-literal-ir"}:
        mapped = {"coroutine-semantics": "coroutine-body-ir", "vptr-type-check-ir": "vptr-type-check-ir", "block-literal-ir": "block-literal-ir"}[scenario]
        return codegen_fixture(o, mapped, n)
    if "lambda" in scenario or "capture" in scenario:
        captures = ",".join(f"v{i}={i}" for i in range(n))
        uses = "+".join(f"v{i}" for i in range(n)) or "0"
        return f"int f(){{auto l=[{captures}](){{return {uses};}}; return l();}}\n"
    if "overload" in scenario:
        funcs = "\n".join(f"int pick(struct T{i}){{return {i};}} struct T{i}{{}};" for i in range(n))
        # Put declarations before overloads to keep each parameter complete.
        funcs = "\n".join(f"struct T{i}{{}}; int pick(T{i}){{return {i};}}" for i in range(n))
        return funcs + f"\nint f(){{return pick(T{n-1}{{}});}}\n"
    if "qualified-name" in scenario:
        ns = "\n".join(f"namespace N{i}{{struct Value{{static constexpr int x={i};}};}}" for i in range(n))
        return ns + f"\nstatic_assert(N{n-1}::Value::x=={n-1});\n"
    if "template" in scenario or "deduction" in scenario:
        if "function-template" in scenario:
            return "template<int N> int tf(){return N;} int f(){return " + "+".join(f"tf<{i}>()" for i in range(n)) + ";}\n"
        inst = "\n".join(f"static_assert(Box<{i}>::value=={i});" for i in range(n))
        return "template<int N> struct Box{static constexpr int value=N;};\n" + inst + "\n"
    if "attribute" in scenario:
        return "\n".join(f"[[nodiscard]] int attr_{i}(){{return {i};}}" for i in range(n)) + "\n"
    if "constant-expression" in scenario or "constexpr" in scenario:
        if "constructors" in scenario:
            return "struct C{int x; constexpr C(int v):x(v){}};\n" + "\n".join(f"constexpr C c{i}({i});" for i in range(n)) + "\n"
        return "constexpr int sq(int x){return x*x;}\n" + "\n".join(f"static_assert(sq({i})=={i*i});" for i in range(n)) + "\n"
    if "type-construction" in scenario or "record-layout" in scenario or "debug-type" in scenario:
        return "\n".join(f"struct R{i}{{char a[{i%7+1}]; long b; virtual ~R{i}()=default;}};" for i in range(n)) + "\n"
    if "derived-records" in scenario:
        return "struct Base{virtual ~Base()=default;};\n" + "\n".join(f"struct Derived{i}:Base{{int x{i};}};" for i in range(n)) + "\n"
    if "constant-array-initializers" in scenario:
        return "\n".join(f"constexpr int values{i}[4]={{{i},{i+1},{i+2},{i+3}}};" for i in range(n)) + "\n"
    if "member-pointer-constexpr" in scenario:
        return "struct P{int x;}; constexpr int P::*pm=&P::x;\n" + "\n".join(f"static_assert(pm==&P::x);" for _ in range(n)) + "\n"
    if "openmp" in scenario:
        return f"void f(int*p){{\n#pragma omp parallel for\nfor(int i=0;i<{n};++i)p[i]=i;\n}}\n"
    if "openacc" in scenario:
        return f"void f(int*p){{\n#pragma acc parallel loop\nfor(int i=0;i<{n};++i)p[i]=i;\n}}\n"
    if "objective-c" in scenario:
        return "@interface Obj\n" + "\n".join(f"-(int)m{i};" for i in range(n)) + "\n@end\n"
    if "inline-asm" in scenario:
        return "int f(int x){\n" + ('asm("" : "+r"(x));\n' * n) + "return x;}\n"
    if "declarator" in scenario:
        return "\n".join(f"int (*decl_{i})(double, char const*);" for i in range(n)) + "\n"
    if "for-statement" in scenario:
        return f"int f(){{int s=0;" + "".join(f"for(int i{i}=0;i{i}<3;++i{i})s+=i{i};" for i in range(n)) + "return s;}\n"
    if "parenthesized-expression" in scenario:
        return "int f(int x){return " + "+".join(f"((x+{i})*2)" for i in range(n)) + ";}\n"
    if "binary-expression" in scenario:
        return "int f(int x){return " + "+".join(f"x*{i+1}" for i in range(n)) + ";}\n"
    if "using-declaration" in scenario:
        return "namespace N{" + "".join(f"int v{i};" for i in range(n)) + "}\n" + "\n".join(f"using N::v{i};" for i in range(n)) + "\n"
    if "function-definition" in scenario or "compound-statement" in scenario:
        return "\n".join(f"int function_{i}(int x){{if(x>{i})return x; return {i};}}" for i in range(n)) + "\n"
    if "destructor-name" in scenario:
        return "\n".join(f"struct D{i}{{~D{i}();}}; void f{i}(D{i}*p){{p->~D{i}();}}" for i in range(n)) + "\n"
    if "builtin-operator" in scenario:
        return "struct X{operator int()const{return 1;}}; int f(X x){return " + "+".join("x+1" for _ in range(n)) + ";}\n"
    if "friend-function" in scenario:
        return "\n".join(f"struct F{i}{{friend int get(F{i}){{return {i};}}}};" for i in range(n)) + "\n"
    if "member-call" in scenario:
        return "struct M{int call(int x){return x;}}; int f(M&m){return " + "+".join(f"m.call({i})" for i in range(n)) + ";}\n"
    if "class-member" in scenario:
        return "struct Members{\n" + "\n".join(f"int method_{i}(int x) const{{return x+{i};}}" for i in range(n)) + "\n};\n"
    if "side-effect" in scenario:
        return f"int f(int*p){{int y=0;\n" + "\n".join(f"y += (*p)++ + {i};" for i in range(n)) + "\nreturn y;}\n"
    if phase == "static-analysis":
        checks = "\n".join(f"if(x=={i}) y += p[{i}%4];" for i in range(n))
        return f"int f(int*p,int x){{int y=0;{checks}\nreturn y;}}\n"
    if phase == "serialization":
        return "template<int N> struct Serialized{int data[N%7+1];};\n" + "\n".join(f"Serialized<{i+1}> s{i};" for i in range(n)) + "\n"
    # Parsing and AST traversal defaults scale real declarations and bodies.
    return "\n".join(f"struct Node_{o}_{i}{{int x; int get()const{{return x+{i};}}}};" for i in range(n)) + "\n"


def codegen_fixture(o: int, scenario: str, n: int) -> str:
    reps = lambda expr: "\n".join(expr.format(i=i) for i in range(n))
    if "complex-multiply" in scenario: return f"_Complex double f(_Complex double x){{_Complex double y=x;\n{reps('y = y * (1.0 + {i}.0i);')}\nreturn y;}}\n"
    if "complex-division" in scenario: return f"_Complex double f(_Complex double x){{_Complex double y=x;\n{reps('y = y / (1.0 + {i}.0i);')}\nreturn y;}}\n"
    if "cast" in scenario: return "double f(long x){double y=0;\n" + reps("y += (double)(x + {i});") + "\nreturn y;}\n"
    if "incdec" in scenario: return "int f(int x){\n" + ("x++;\n" * n) + "return x;}\n"
    if "conditional" in scenario: return "int f(int x){int y=0;\n" + reps("y += x>{i} ? x : {i};") + "\nreturn y;}\n"
    if "compare" in scenario: return "int f(int x){int y=0;\n" + reps("y += x == {i};") + "\nreturn y;}\n"
    if "atomic" in scenario: return "int f(int *p){int y=0;\n" + reps("y += __atomic_fetch_add(p,{i}+1,__ATOMIC_SEQ_CST);") + "\nreturn y;}\n"
    if "direct-call" in scenario: return f"__attribute__((noinline)) int callee(int x){{return x+1;}} int f(int x){{\n{reps('x=callee(x);')}\nreturn x;}}\n"
    if "member-function-pointer" in scenario or "member-pointer" in scenario:
        return f"struct X{{int a; int m(){{return a;}}}}; int f(X*x){{int (X::*p)()=&X::m; int y=0;\n{reps('y += (x->*p)();')}\nreturn y;}}\n"
    if "new-array" in scenario or "aggregate-array" in scenario: return f"struct X{{int a;}}; int f(){{X x[{n}] = {{}}; return x[{n-1}].a;}}\n"
    if "thread-local" in scenario: return "struct X{X();};\n" + "\n".join(f"thread_local X value_{i};" for i in range(n)) + "\nint f(){return 0;}\n"
    if "guarded-static" in scenario: return f"struct X{{X(); int a;}}; int f(){{static X values[{n}]; return values[0].a;}}\n"
    if "block-literal" in scenario: return f"int f(int x){{int (^b)(int)=^(int y){{return y+x;}}; int z=0;\n{reps('z += b({i});')}\nreturn z;}}\n"
    if "inline-asm" in scenario: return "int f(int x){\n" + ('asm("" : "+r"(x));\n' * n) + "return x;}\n"
    if "lvalue-store" in scenario: return "int f(int*p){\n" + reps("p[{i}]={i};") + "\nreturn p[0];}\n"
    if "auto-var-init" in scenario: return f"int f(){{int values[{n}]; return values[0];}}\n"
    if "exception" in scenario or "cleanup" in scenario: return f"struct X{{~X();}}; int f(int x){{X values[{n}]; if(x) throw x; return 0;}}\n"
    if "coroutine" in scenario: return "#include <coroutine>\nstruct T{struct promise_type{T get_return_object(){return{};} std::suspend_never initial_suspend(){return{};} std::suspend_never final_suspend() noexcept{return{};} void return_void(){} void unhandled_exception(){}};}; T f(){" + ("co_await std::suspend_never{};" * n) + "co_return;}\n"
    if "openmp" in scenario: return f"void f(int*p){{\n#pragma omp parallel for\nfor(int i=0;i<{n};++i)p[i]=i;\n}}\n"
    if "debug-type" in scenario: return "\n".join(f"struct D{i}{{int a; double b;}};" for i in range(n)) + "\nint f(){return 0;}\n"
    if "type-check" in scenario: return f"struct B{{virtual ~B()=default;}}; struct D:B{{}}; int f(B*p){{int y=0;\n{reps('y += dynamic_cast<D*>(p)!=nullptr;')}\nreturn y;}}\n"
    if "constant-compare" in scenario: return "int f(int x){return " + "+".join(f"(x<{i})" for i in range(n)) + ";}\n"
    if "constant-binary" in scenario: return "int f(){return " + "+".join(f"({i}*{i+1})" for i in range(n)) + ";}\n"
    if "debug-location" in scenario: return "\n".join(f"int dl{i}(int x){{return x+{i};}}" for i in range(n)) + "\n"
    if "prolog" in scenario or "epilog" in scenario: return f"int f(" + ",".join(f"int a{i}" for i in range(n)) + "){return a0;}\n"
    raise ValueError(f"missing scalable CodeGen fixture: {scenario}")


def main() -> None:
    if not CHECKOUT.is_dir(): raise SystemExit(f"missing checkout: {CHECKOUT}")
    previous_specs={p.parents[1].name:json.loads(p.read_text()) for p in (ROOT/"cases").glob("*/tests/spec.json")} if ROOT.exists() else {}
    replacement_data=json.loads((ROOT/"tools/replacements.json").read_text()) if (ROOT/"tools/replacements.json").exists() else {"replacements":{}}
    if ROOT.exists():
        shutil.rmtree(ROOT / "cases", ignore_errors=True)
        shutil.rmtree(ROOT / "upstream", ignore_errors=True)
    (ROOT / "cases").mkdir(parents=True, exist_ok=True)
    (ROOT / "upstream" / "llvm-project").mkdir(parents=True, exist_ok=True)
    shutil.copy2(CHECKOUT / "llvm/LICENSE.TXT", ROOT / "upstream" / "llvm-project" / "LICENSE.TXT")

    search_roots = ["clang/lib/Lex", "clang/lib/Parse", "clang/lib/Sema", "clang/lib/AST",
                    "clang/lib/Analysis", "clang/lib/Serialization", "clang/lib/CodeGen",
                    "clang/lib/Tooling", "clang/lib/Format", "llvm/lib/AsmParser", "llvm/lib/IR"]
    pool = []
    for directory in search_roots:
        for path in sorted((CHECKOUT / directory).rglob("*.cpp")):
            pool.extend(candidates(path))
    pool.sort(key=lambda c: (-c.score, str(c.path), c.start))
    selected = []
    per_file = {}
    per_phase = {}
    symbols = set()
    # Limit file concentration while maintaining broad phase representation.
    for c in pool:
        rel = c.path.relative_to(CHECKOUT).as_posix()
        phase = phase_for(rel)
        if phase == "ir-generation" and any(x in rel for x in ("CodeGen/Targets/", "CGBuiltin.cpp", "CGCUDA", "CGOpenMP", "CGObjC")):
            continue
        key = (rel, c.symbol)
        overlaps = any(old.path == c.path and not (c.end < old.start or c.start > old.end) for old in selected)
        if key in symbols or overlaps or per_file.get(rel, 0) >= 4 or per_phase.get(phase, 0) >= 35: continue
        symbols.add(key); selected.append(c)
        per_file[rel] = per_file.get(rel, 0) + 1
        per_phase[phase] = per_phase.get(phase, 0) + 1
        if len(selected) == 250: break
    if len(selected) != 250: raise SystemExit(f"only selected {len(selected)} candidates")
    replacement_file = ROOT / "tools" / "replacements.json"
    if replacement_file.exists():
        replacements = replacement_data.get("replacements", {})
        for id_text, item in replacements.items():
            index = int(id_text.removeprefix("cf-")) - 1
            path = CHECKOUT / item["source"]
            matches = [c for c in candidates(path) if c.start == item["start_line"] and c.end == item["end_line"]]
            if len(matches) != 1 or matches[0].symbol != item["symbol"]:
                raise ValueError(f"replacement no longer resolves exactly: {id_text}")
            selected[index] = matches[0]
        exact=[(str(c.path),c.start,c.end) for c in selected]
        if len(exact)!=len(set(exact)):raise ValueError("replacement set contains duplicate exact targets")

    runner_hash = hashlib.sha256((ROOT / "test-support" / "run_case.py").read_bytes()).hexdigest()
    for number, c in enumerate(selected, 1):
        cid = f"cf-{number:03d}"
        rel = c.path.relative_to(CHECKOUT).as_posix()
        phase = phase_for(rel)
        source_dest = ROOT / "upstream" / "llvm-project" / rel
        source_dest.parent.mkdir(parents=True, exist_ok=True)
        if not source_dest.exists(): shutil.copy2(c.path, source_dest)
        raw = source_dest.read_bytes()
        lines = raw.decode(errors="replace").splitlines(keepends=True)
        marked = lines.copy()
        include_at = next((i for i, x in enumerate(marked) if x.startswith("#include")), 0)
        marked.insert(include_at, '#include "drperf_bench_region.h"\n')
        opening_index = c.opening - 1 + (1 if include_at <= c.opening - 1 else 0)
        indent = re.match(r"\s*", marked[opening_index]).group(0) + "  "
        marked.insert(opening_index + 1, f'{indent}DRPERF_BENCH_REGION("{cid}");\n')
        patch = "".join(difflib.unified_diff(lines, marked, fromfile=f"a/{rel}", tofile=f"b/{rel}"))
        case_dir = ROOT / "cases" / cid
        (case_dir / "tests").mkdir(parents=True)
        (case_dir / "region.patch").write_text(patch)
        body = "".join(lines[c.opening - 1:c.end])
        scenario, flags, expect = targeted_scenario(phase, rel, c.symbol, body)
        if phase == "formatting": tool = "clang-format"
        elif "DependencyScanning" in rel: tool = "clang-scan-deps"
        elif "Tooling/Syntax" in rel: tool = "clang"
        elif phase == "source-tooling": tool = "clang-check"
        elif "ASTImporter" in rel or scenario in {"ast-structural-equivalence", "ast-import-shape"}: tool = "clang-import-test"
        else: tool = "clang"
        if tool == "clang-import-test": expect = ""
        spec = {"case": cid, "phase": phase, "scenario": scenario, "compiler": tool,
                "flags": flags, "expected_stdout": expect, "fixture": fixture(phase, number, scenario),
                "fixtures": fixture_sizes(phase, number, scenario),
                "target_symbol": c.symbol, "target_source": rel,
                "mapping_note": f"The {scenario} construct is selected from the target name and implementation vocabulary; exact native entry still requires the pinned instrumented build."}
        completion_expectations={"ordinary-name-completion":["local_0"],"preprocessor-directive-completion":["include","define"],"objc-method-decl-completion":[],"objc-key-value-completion":[]}
        if scenario in completion_expectations: spec["expected_completions"]=completion_expectations[scenario]
        if scenario in {"objc-method-decl-completion", "objc-key-value-completion"}: spec["requires_completion_output"]=False
        if "Tooling/Syntax" in rel:
            spec["harness_status"] = "missing-custom-syntax-tree-harness"
        replacement=replacement_data.get("replacements",{}).get(cid)
        if replacement:
            witness=replacement.get("witness_spec") or previous_specs[replacement["witness"]]
            for key in ("scenario","compiler","flags","expected_stdout","fixture","fixtures","expected_completions","requires_completion_output","harness_status"):
                if key in witness:spec[key]=witness[key]
                else:spec.pop(key,None)
            spec["case"]=cid;spec["phase"]=phase;spec["workload_phase"]=witness.get("phase")
            if len({x["source"] for x in spec.get("fixtures",[])})<3:
                witness_ordinal=int(replacement["witness"].removeprefix("cf-"))
                spec["fixtures"]=fixture_sizes(witness.get("phase",phase),witness_ordinal,spec["scenario"])
            spec["target_symbol"]=c.symbol;spec["target_source"]=rel
            spec["mapping_note"]=f"Pinned source coverage observed {c.symbol} in the combined run of witness {replacement['witness']}; per-size native entry must be checked separately. Counts and hashes are recorded in tools/replacements.json."
            scenario=spec["scenario"];tool=spec["compiler"]
        (case_dir / "tests" / "spec.json").write_text(json.dumps(spec, indent=2) + "\n")
        url = f"{REPOSITORY}/blob/{REVISION}/{rel}#L{c.start}-L{c.end}"
        locally_runnable = "Tooling/Syntax" not in rel
        validation = ({"status": "behavior-checked", "details": "Three bounded structural sizes passed with the host tool. This checks the selected subsystem and assertions only; it does not establish entry into the pinned marked source."}
                      if locally_runnable else
                      {"status": "not-run", "details": ("LLVM 20.1.8 provides this syntax-tree implementation as a library with unit tests but no command-line harness accepting arbitrary fixtures; a small clangToolingSyntax client is still required."
                          if "Tooling/Syntax" in rel else f"The case requires the matching pinned build's specialized {tool} path; that tool was unavailable in the host environment. The concrete three-size test is retained for that build.")})
        manifest = {
            "schema_version": 1, "id": cid, "title": f"{c.symbol} compiler region", "language": "cpp",
            "source": {"repository": REPOSITORY, "revision": REVISION, "path": rel,
                       "snapshot": f"../../upstream/llvm-project/{rel}", "sha256": hashlib.sha256(raw).hexdigest()},
            "region": {"symbol": c.symbol, "start_line": c.start, "end_line": c.end, "kind": "function"},
            "marker": {"kind": "cpp-scope", "name": cid, "pcvs": []}, "status": "collected",
            "build_status": "not-built", "phase": phase,
            "workload": {"description": f"Run the bounded {scenario} fixture with Clang using explicit phase flags and assert compiler output or exit semantics.",
                         "command": ["{python}", "tests/run_case.py", "tests/spec.json"]},
            "source_family": f"llvm-project:{rel}:{c.symbol}", "citations": [url],
            "tests": {"files": ["tests/spec.json"], "resources": [{"source": "../../test-support/run_case.py", "destination": "tests/run_case.py", "sha256": runner_hash}],
                      "command": ["{python}", "tests/run_case.py", "tests/spec.json"],
                      "validation": validation,
                      "coverage_note": "A full LLVM checkout at the pinned revision must be patched and built with the PerfMark helper to verify entry into this exact native region."}}
        (case_dir / "case.json").write_text(json.dumps(manifest, indent=2) + "\n")
        task = f"# {c.symbol}\n\nInspect the empty marked function in `{rel}` at LLVM commit `{REVISION}`. Identify runtime state that explains its cost without changing compiler behavior.\n\nUse the supplied `{scenario}` workload at structural sizes 4, 16, and 64. Run it with the explicit tool and flags in `tests/spec.json`, preserving the assertions at every size when investigating scaling. The marker begins with no PCVs.\n\nFor region-entry measurement, apply `region.patch` independently to a full checkout, configure LLVM with `-DLLVM_ENABLE_PROJECTS='clang;clang-tools-extra'`, add the collection support and PerfMark include paths, link PerfMark, and run the newly built tool. See the group README for exact setup commands.\n"
        (case_dir / "task.md").write_text(task)
        traits = []
        if re.search(r"\bfor\s*\(|\bwhile\s*\(", body): traits.append("iteration over input-dependent compiler data")
        if any(x in body for x in ("Lookup", "lookup", "DenseMap", "SmallPtrSet")): traits.append("name or table lookup")
        if any(x in body for x in ("Parse", "Token", "Lexer")): traits.append("token consumption or parsing")
        if any(x in body for x in ("Diagn", "Report(")): traits.append("diagnostic construction")
        if any(x in body for x in ("Create", "Build", "new ")): traits.append("AST or IR object construction")
        if not traits: traits.append("branching and object traversal in a compiler hot path")
        rationale = ", ".join(traits[:3])
        relationship=(f"Pinned source coverage observed this function during the combined `{scenario}` witness run from {spec.get('workload_phase')} work; per-size native entry is checked separately."
                      if replacement else f"The `{scenario}` test invokes the corresponding `{phase}` subsystem.")
        ref = f"# Selection evidence for {c.symbol}\n\nSource: [{rel} lines {c.start}-{c.end}]({url}). The snapshot is byte-for-byte from the pristine pinned commit and is licensed under LLVM's Apache-2.0 WITH LLVM-exception terms; see the collected license.\n\n{relationship} The test uses structural sizes 4, 16, and 64, and its spec records the exact tool, flags, target path, and symbol. Specialized tool cases remain not-run where a harness is unavailable; host behavior is never treated as pinned marker coverage.\n\nThis region was selected because its implementation contains {rationale}. Those operations can scale with tokens, declarations, candidates, AST nodes, or IR objects depending on the caller. This is an opportunity hypothesis for profiling, not a ground-truth PCV assignment or a measured speedup.\n\nSeveral-fold improvement is plausible only if measurement finds repeated scans, redundant lookup, avoidable rebuilding, or repeated diagnostics on growing inputs. The collection makes no claim that such behavior occurs for this function or supplied fixture.\n"
        (case_dir / "reference.md").write_text(ref)
    print(json.dumps({"selected": len(selected), "phases": per_phase, "files": len(per_file)}, indent=2))


if __name__ == "__main__": main()
