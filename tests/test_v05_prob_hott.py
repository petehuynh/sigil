"""Tests for Sigil v0.5 — probabilistic programming, HoTT paths."""

from __future__ import annotations

import pytest

from sigil_core import (
    parse_one, serialize, msg, tokenize,
    Message, Identifier, NumberLiteral, BinaryOp, UnaryOp,
    Distribution, PathType, Lambda, PiType, FuncCall,
    Definition, Range, RefinementType,
)
from sigil_core.tokens import TokenType


# ===================================================================
# Lexer — new tokens
# ===================================================================

class TestV05Lexer:
    def test_proportional(self):
        tokens = tokenize("x \u221d y")
        assert tokens[1].type == TokenType.PROPORTIONAL


# ===================================================================
# Parser — Distribution
# ===================================================================

class TestV05Distribution:
    def test_dist_normal(self):
        node = parse_one("[Q bot Dist:Normal(0, 1)]")
        d = node.content[0]
        assert isinstance(d, Distribution)
        assert d.name == "Normal"
        assert len(d.params) == 2
        assert isinstance(d.params[0], NumberLiteral)
        assert d.params[0].value == 0
        assert isinstance(d.params[1], NumberLiteral)
        assert d.params[1].value == 1

    def test_dist_beta(self):
        node = parse_one("[Q bot Dist:Beta(2, 5)]")
        d = node.content[0]
        assert isinstance(d, Distribution)
        assert d.name == "Beta"
        assert len(d.params) == 2

    def test_dist_bernoulli(self):
        node = parse_one("[Q bot Dist:Bernoulli(0.7)]")
        d = node.content[0]
        assert isinstance(d, Distribution)
        assert d.name == "Bernoulli"
        assert len(d.params) == 1

    def test_dist_with_variable_params(self):
        node = parse_one("[Q bot Dist:Normal(mu, sigma)]")
        d = node.content[0]
        assert isinstance(d, Distribution)
        assert isinstance(d.params[0], Identifier)
        assert d.params[0].name == "mu"

    def test_proportional_op(self):
        node = parse_one("[A bot posterior \u221d likelihood]")
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "\u221d"


# ===================================================================
# Parser — PathType (HoTT)
# ===================================================================

class TestV05PathType:
    def test_path_type_builder(self):
        """PathType constructed via builder."""
        m = (msg("K", "bot")
             .path_type(Identifier(name="x"), Identifier(name="y"))
             .build())
        pt = m.content[0]
        assert isinstance(pt, PathType)
        assert isinstance(pt.left, Identifier)
        assert pt.left.name == "x"
        assert isinstance(pt.right, Identifier)
        assert pt.right.name == "y"


# ===================================================================
# Spec examples — full expressions from v0.2-v0.5
# ===================================================================

class TestSpecExamples:
    def test_pythagoras_theorem(self):
        """c^2 == a^2 + b^2."""
        node = parse_one("[K bot c ^ 2 == a ^ 2 + b ^ 2]")
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "=="

    def test_math_expression(self):
        """1 + 2 * 3 in a message."""
        node = parse_one("[A bot 1 + 2 * 3]")
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "+"
        assert isinstance(expr.right, BinaryOp)
        assert expr.right.op == "*"

    def test_functor_assertion(self):
        """F(A \u27f6 B) == F(A) \u27f6 F(B) — functor preserves morphisms."""
        node = parse_one("[A bot F(A \u27f6 B) == F(A) \u27f6 F(B)]")
        # Top level: == at precedence 6
        # Left side: F(A ⟶ B) which is a FuncCall
        # Right side: F(A) ⟶ F(B) which involves ⟶ at precedence 1
        # Actually == (6) binds tighter than ⟶ (1), so:
        # F(A ⟶ B)  ==  F(A)  ⟶  F(B)
        # → (F(A ⟶ B) == F(A)) ⟶ F(B)
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)

    def test_probabilistic_inference(self):
        """posterior \u221d likelihood * prior."""
        node = parse_one("[A bot posterior \u221d likelihood * prior]")
        expr = node.content[0]
        # \u221d is level 6, * is level 9 (tighter)
        # So: posterior ∝ (likelihood * prior)
        assert isinstance(expr, BinaryOp)
        assert expr.op == "\u221d"
        assert isinstance(expr.right, BinaryOp)
        assert expr.right.op == "*"

    def test_pi_type_in_message(self):
        """Knowledge transfer with Pi type."""
        node = parse_one("[K bot \u03a0(x:Nat) Vec(x)]")
        pi = node.content[0]
        assert isinstance(pi, PiType)

    def test_lambda_with_body_expr(self):
        """\u03bbx: x + 1."""
        node = parse_one("[A bot \u03bbx: x + 1]")
        lam = node.content[0]
        assert isinstance(lam, Lambda)
        assert isinstance(lam.body, BinaryOp)
        assert lam.body.op == "+"

    def test_definition_with_expr(self):
        """double := \u03bbx: x * 2."""
        node = parse_one("[K bot double := \u03bbx: x * 2]")
        defn = node.content[0]
        assert isinstance(defn, Definition)
        assert defn.name == "double"
        assert isinstance(defn.value, Lambda)

    def test_element_of_set(self):
        """x \u2208 Nat."""
        node = parse_one("[A bot x \u2208 Nat]")
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "\u2208"

    def test_msg_type_inf(self):
        """New message type 'inf'."""
        node = parse_one("[inf bot result:42]")
        assert isinstance(node, Message)
        assert node.msg_type == "inf"

    def test_msg_type_upd(self):
        """New message type 'upd'."""
        node = parse_one("[upd bot status:ok]")
        assert isinstance(node, Message)
        assert node.msg_type == "upd"


# ===================================================================
# Serializer roundtrips
# ===================================================================

class TestV05Serializer:
    def test_distribution_roundtrip(self):
        d = Distribution(name="Normal", params=[NumberLiteral(value=0), NumberLiteral(value=1)])
        s = serialize(d)
        assert s == "Dist:Normal(0, 1)"

    def test_path_type_roundtrip(self):
        pt = PathType(left=Identifier(name="x"), right=Identifier(name="y"))
        s = serialize(pt)
        assert s == "x =_Path y"

    def test_complex_roundtrip(self):
        """Lambda with math body roundtrip."""
        lam = Lambda(params=["x"], body=BinaryOp(
            left=Identifier(name="x"),
            op="+",
            right=NumberLiteral(value=1),
        ))
        s = serialize(lam)
        assert s == "\u03bbx: x + 1"


# ===================================================================
# Builder methods
# ===================================================================

class TestV05Builder:
    def test_dist(self):
        m = (msg("Q", "bot")
             .dist("Normal", [NumberLiteral(value=0), NumberLiteral(value=1)])
             .build())
        assert isinstance(m.content[0], Distribution)
        assert m.content[0].name == "Normal"

    def test_path_type(self):
        m = (msg("K", "bot")
             .path_type(Identifier(name="a"), Identifier(name="b"))
             .build())
        assert isinstance(m.content[0], PathType)

    def test_full_message_serialize(self):
        """Build and serialize a complex v0.5 message."""
        text = (msg("Q", "bot")
                .dist("Normal", [NumberLiteral(value=0), NumberLiteral(value=1)])
                .to_aether())
        assert "Dist:Normal(0, 1)" in text
        assert text.startswith("[Q")


# ===================================================================
# Backward compatibility
# ===================================================================

class TestBackwardCompat:
    def test_v01_simple_query(self):
        """v0.1 message still parses correctly."""
        node = parse_one('[Q grok-1 user:42 ask:weather @loc:singapore "tomorrow" prob:?]')
        assert isinstance(node, Message)
        assert node.msg_type == "Q"

    def test_v01_binary_arrow(self):
        """v0.1 -> arrow still works."""
        node = parse_one("[C bot A -> B]")
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "->"

    def test_v01_quantifier(self):
        """v0.1 forall still works."""
        node = parse_one("[K bot {forall x: P(x)}]")
        assert isinstance(node, Message)

    def test_version_bumped(self):
        import sigil_core
        assert sigil_core.__version__ >= "0.5.0"
