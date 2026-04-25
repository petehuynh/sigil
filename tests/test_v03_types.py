"""Tests for Sigil v0.3 — type theory, category theory."""

from __future__ import annotations

import pytest

from sigil_core import (
    parse_one, serialize, msg, tokenize,
    Message, Identifier, NumberLiteral, BinaryOp,
    PiType, SigmaType, RefinementType, TypeJudgment, InductiveType, FuncCall,
)
from sigil_core.tokens import TokenType


# ===================================================================
# Lexer — new tokens
# ===================================================================

class TestV03Lexer:
    def test_long_arrow(self):
        tokens = tokenize("A \u27f6 B")
        assert tokens[1].type == TokenType.LONG_ARROW

    def test_double_arrow(self):
        tokens = tokenize("A \u21d2 B")
        assert tokens[1].type == TokenType.DOUBLE_ARROW

    def test_adjoint(self):
        tokens = tokenize("F \u22a3 G")
        assert tokens[1].type == TokenType.ADJOINT

    def test_iso(self):
        tokens = tokenize("A \u2245 B")
        assert tokens[1].type == TokenType.ISO

    def test_compose(self):
        tokens = tokenize("f \u2218 g")
        assert tokens[1].type == TokenType.COMPOSE

    def test_pi_unicode(self):
        tokens = tokenize("\u03a0")
        assert tokens[0].type == TokenType.PI_TYPE

    def test_sigma_unicode(self):
        tokens = tokenize("\u03a3")
        assert tokens[0].type == TokenType.SIGMA_TYPE

    def test_equiv_type(self):
        tokens = tokenize("A \u2243 B")
        assert tokens[1].type == TokenType.EQUIV_TYPE

    def test_pi_keyword(self):
        tokens = tokenize("Pi")
        assert tokens[0].type == TokenType.PI_TYPE

    def test_sigma_keyword(self):
        tokens = tokenize("Sigma")
        assert tokens[0].type == TokenType.SIGMA_TYPE


# ===================================================================
# Parser — Pi / Sigma types
# ===================================================================

class TestV03PiSigma:
    def test_pi_type_unicode(self):
        node = parse_one("[K bot \u03a0(x:Nat) Vec(x)]")
        pi = node.content[0]
        assert isinstance(pi, PiType)
        assert pi.var == "x"
        assert isinstance(pi.domain, Identifier)
        assert pi.domain.name == "Nat"
        assert isinstance(pi.codomain, FuncCall)
        assert pi.codomain.name == "Vec"

    def test_pi_type_keyword(self):
        node = parse_one("[K bot Pi(x:A) B]")
        pi = node.content[0]
        assert isinstance(pi, PiType)
        assert pi.var == "x"
        assert isinstance(pi.domain, Identifier)
        assert pi.domain.name == "A"
        assert isinstance(pi.codomain, Identifier)
        assert pi.codomain.name == "B"

    def test_sigma_type_unicode(self):
        node = parse_one("[K bot \u03a3(x:A) B(x)]")
        sig = node.content[0]
        assert isinstance(sig, SigmaType)
        assert sig.var == "x"
        assert isinstance(sig.domain, Identifier)
        assert sig.domain.name == "A"
        assert isinstance(sig.body, FuncCall)

    def test_sigma_type_keyword(self):
        node = parse_one("[K bot Sigma(n:Nat) Vec(n)]")
        sig = node.content[0]
        assert isinstance(sig, SigmaType)
        assert sig.var == "n"


# ===================================================================
# Parser — refinement types
# ===================================================================

class TestV03Refinement:
    def test_refinement_type(self):
        node = parse_one("[K bot {x:Nat | x > 0}]")
        ref = node.content[0]
        assert isinstance(ref, RefinementType)
        assert ref.var == "x"
        assert isinstance(ref.base_type, Identifier)
        assert ref.base_type.name == "Nat"
        assert isinstance(ref.predicate, BinaryOp)
        assert ref.predicate.op == ">"

    def test_scope_without_pipe_is_scope(self):
        """Normal scope {a b} should not be parsed as refinement."""
        node = parse_one("[A bot {x y}]")
        from sigil_core import Scope
        scope = node.content[0]
        assert isinstance(scope, Scope)

    def test_refinement_with_function_predicate(self):
        node = parse_one("[K bot {x:Int | positive(x)}]")
        ref = node.content[0]
        assert isinstance(ref, RefinementType)
        assert isinstance(ref.predicate, FuncCall)
        assert ref.predicate.name == "positive"


# ===================================================================
# Parser — category / composition operators
# ===================================================================

class TestV03CategoryOps:
    def test_compose(self):
        node = parse_one("[A bot f \u2218 g]")
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "\u2218"

    def test_iso(self):
        node = parse_one("[A bot A \u2245 B]")
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "\u2245"

    def test_adjoint(self):
        node = parse_one("[A bot F \u22a3 G]")
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "\u22a3"

    def test_long_arrow(self):
        node = parse_one("[C bot A \u27f6 B]")
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "\u27f6"

    def test_double_arrow(self):
        node = parse_one("[C bot A \u21d2 B]")
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "\u21d2"

    def test_equiv_type_op(self):
        node = parse_one("[A bot A \u2243 B]")
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "\u2243"

    def test_compose_higher_than_add(self):
        """f \u2218 g + h → (f \u2218 g) + h because compose is level 11, add is level 8."""
        node = parse_one("[A bot f \u2218 g + h]")
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "+"
        assert isinstance(expr.left, BinaryOp)
        assert expr.left.op == "\u2218"


# ===================================================================
# Serializer roundtrips
# ===================================================================

class TestV03Serializer:
    def test_pi_type_roundtrip(self):
        pi = PiType(var="x", domain=Identifier(name="Nat"), codomain=FuncCall(name="Vec", args=[Identifier(name="x")]))
        s = serialize(pi)
        assert s == "\u03a0(x:Nat) Vec(x)"

    def test_sigma_type_roundtrip(self):
        sig = SigmaType(var="x", domain=Identifier(name="A"), body=Identifier(name="B"))
        s = serialize(sig)
        assert s == "\u03a3(x:A) B"

    def test_refinement_roundtrip(self):
        ref = RefinementType(
            var="x",
            base_type=Identifier(name="Nat"),
            predicate=BinaryOp(left=Identifier(name="x"), op=">", right=NumberLiteral(value=0)),
        )
        s = serialize(ref)
        assert s == "{x:Nat | x > 0}"

    def test_type_judgment_roundtrip(self):
        tj = TypeJudgment(
            context=Identifier(name="\u0393"),
            term=Identifier(name="t"),
            type_=Identifier(name="T"),
        )
        s = serialize(tj)
        assert s == "\u0393 \u22a2 t : T"

    def test_inductive_roundtrip(self):
        ind = InductiveType(
            name="Bool",
            params=[],
            constructors=[Identifier(name="true"), Identifier(name="false")],
        )
        s = serialize(ind)
        assert s == "Inductive Bool := true | false"


# ===================================================================
# Builder methods
# ===================================================================

class TestV03Builder:
    def test_pi_type(self):
        m = (msg("K", "bot")
             .pi_type("x", Identifier(name="Nat"), FuncCall(name="Vec", args=[Identifier(name="x")]))
             .build())
        assert isinstance(m.content[0], PiType)

    def test_sigma_type(self):
        m = (msg("K", "bot")
             .sigma_type("n", Identifier(name="Nat"), FuncCall(name="Vec", args=[Identifier(name="n")]))
             .build())
        assert isinstance(m.content[0], SigmaType)

    def test_judgment(self):
        m = (msg("K", "bot")
             .judgment(Identifier(name="\u0393"), Identifier(name="t"), Identifier(name="T"))
             .build())
        assert isinstance(m.content[0], TypeJudgment)

    def test_refinement(self):
        m = (msg("K", "bot")
             .refinement("x", Identifier(name="Int"), BinaryOp(
                 left=Identifier(name="x"), op=">", right=NumberLiteral(value=0)))
             .build())
        assert isinstance(m.content[0], RefinementType)
