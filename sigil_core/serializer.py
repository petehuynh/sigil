"""Sigil serializer — AST nodes back to text."""

from __future__ import annotations

from . import ast_nodes as ast


def serialize(node: ast.Node) -> str:
    """Serialize an AST node back to Sigil text."""
    return _serialize(node)


def _serialize(node: ast.Node) -> str:
    match node:
        case ast.Message():
            parts = [node.msg_type, _serialize(node.sender)]
            if node.receiver:
                parts.append(_serialize(node.receiver))
            for c in node.content:
                parts.append(_serialize(c))
            return "[" + " ".join(parts) + "]"

        case ast.Identifier():
            return node.name

        case ast.QualifiedName():
            return ":".join(node.parts)

        case ast.EntityRef():
            return "@" + _serialize(node.qualified)

        case ast.NumberLiteral():
            if isinstance(node.value, float) and node.value == int(node.value):
                return str(node.value)
            return str(node.value)

        case ast.StringLiteral():
            return f'"{node.value}"'

        case ast.List():
            items = ", ".join(_serialize(i) for i in node.items)
            return f"[{items}]"

        case ast.Scope():
            body = " ".join(_serialize(b) for b in node.body)
            return "{" + body + "}"

        case ast.Vector():
            vals = ", ".join(str(v) for v in node.values)
            return f"vec:[{vals}]"

        case ast.KeyValue():
            return f"{node.key}:{_serialize(node.value)}"

        case ast.BinaryOp():
            return f"{_serialize(node.left)} {node.op} {_serialize(node.right)}"

        case ast.UnaryOp():
            return f"{node.op}{_serialize(node.operand)}"

        case ast.FuncCall():
            args = ", ".join(_serialize(a) for a in node.args)
            return f"{node.name}({args})"

        case ast.Quantifier():
            return f"{node.kind} {node.variable}: {_serialize(node.body)}"

        case ast.Probability():
            s = f"prob:{node.confidence}"
            if node.statement:
                s += " " + _serialize(node.statement)
            return s

        # v0.2
        case ast.Lambda():
            params = " ".join(node.params)
            return f"\u03bb{params}: {_serialize(node.body)}"

        case ast.Definition():
            return f"{node.name} := {_serialize(node.value)}"

        case ast.Range():
            return f"{_serialize(node.start)}..{_serialize(node.end)}"

        # v0.3
        case ast.PiType():
            return f"\u03a0({node.var}:{_serialize(node.domain)}) {_serialize(node.codomain)}"

        case ast.SigmaType():
            return f"\u03a3({node.var}:{_serialize(node.domain)}) {_serialize(node.body)}"

        case ast.InductiveType():
            params = " ".join(node.params)
            constrs = " | ".join(_serialize(c) for c in node.constructors)
            p = f" {params}" if params else ""
            return f"Inductive {node.name}{p} := {constrs}"

        case ast.TypeJudgment():
            return f"{_serialize(node.context)} \u22a2 {_serialize(node.term)} : {_serialize(node.type_)}"

        case ast.RefinementType():
            return "{" + f"{node.var}:{_serialize(node.base_type)} | {_serialize(node.predicate)}" + "}"

        # v0.5
        case ast.Distribution():
            params = ", ".join(_serialize(p) for p in node.params)
            return f"Dist:{node.name}({params})"

        case ast.PathType():
            return f"{_serialize(node.left)} =_Path {_serialize(node.right)}"

        # v1.1 AetherCode
        case ast.CodeBlock():
            body = " ".join(_serialize(n) for n in node.body)
            return f"code: {{{body}}}"

        case ast.FunctionDef():
            params = ", ".join(f"{p}: {_serialize(t)}" for p, t in node.params)
            ret = f" \u2192 {_serialize(node.return_type)}" if node.return_type else ""
            energy = f" energy: {_serialize(node.energy)}" if node.energy else ""
            body = " ".join(_serialize(n) for n in node.body)
            body_s = f" {{{body}}}" if node.body else ""
            return f"fn: {node.name}({params}){ret}{energy}{body_s}"

        case ast.ModuleDef():
            body = " ".join(_serialize(n) for n in node.body)
            return f"mod: {node.name} {{{body}}}"

        case ast.TypeDef():
            return f"type: {node.name} := {_serialize(node.value)}"

        case ast.TestBlock():
            body = " ".join(_serialize(n) for n in node.body)
            return f"test: {node.name} {{{body}}}"

        case ast.DeployStatement():
            return f"deploy: {node.target}"

        case ast.SelfHealBlock():
            body = " ".join(_serialize(n) for n in node.body)
            return f"self:heal {{{body}}}"

        case ast.EnergyDecl():
            return f"energy: {node.amount} {node.unit}"

        case ast.LLMDirective():
            if node.args:
                args = ", ".join(_serialize(a) for a in node.args)
                return f"llm:{node.action}({args})"
            return f"llm:{node.action}"

        case _:
            return repr(node)


def compact(node: ast.Node) -> str:
    """Serialize to minimal whitespace form (for token-efficient transmission)."""
    text = serialize(node)
    import re
    return re.sub(r"\s+", " ", text).strip()
