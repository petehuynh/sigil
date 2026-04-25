"""Tests for Sigil v0.2 — math/logic operators, lambda, definition, range."""

from __future__ import annotations

import pytest

from sigil_core import (
    parse_one, serialize, msg, tokenize,
    Message, Identifier, NumberLiteral, BinaryOp, UnaryOp,
    Lambda, Definition, Range,
)
from sigil_core.tokens import TokenType
from sigil_core.lexer import LexError


# ===================================================================
# Lexer — new tokens
# ===================================================================

class TestV02Lexer:
    def test_plus(self):
        tokens = tokenize("1 + 2")
        assert tokens[1].type == TokenType.PLUS

    def test_minus_binary(self):
        tokens = tokenize("3 - 1")
        assert tokens[1].type == TokenType.MINUS

    def test_star(self):
        tokens = tokenize("2 * 3")
        assert tokens[1].type == TokenType.STAR

    def test_slash(self):
        tokens = tokenize("6 / 2")
        assert tokens[1].type == TokenType.SLASH

    def test_percent(self):
        tokens = tokenize("7 % 3")
        assert tokens[1].type == TokenType.PERCENT

    def test_double_star(self):
        tokens = tokenize("2 ** 3")
        assert tokens[1].type == TokenType.DOUBLE_STAR

    def test_lt(self):
        tokens = tokenize("a < b")
        assert tokens[1].type == TokenType.LT

    def test_gt(self):
        tokens = tokenize("a > b")
        assert tokens[1].type == TokenType.GT

    def test_lte(self):
        tokens = tokenize("a <= b")
        assert tokens[1].type == TokenType.LTE

    def test_gte(self):
        tokens = tokenize("a >= b")
        assert tokens[1].type == TokenType.GTE

    def test_walrus(self):
        tokens = tokenize("x := 5")
        assert tokens[1].type == TokenType.WALRUS

    def test_dotdot(self):
        tokens = tokenize("1..10")
        assert tokens[1].type == TokenType.DOTDOT

    def test_backslash_lambda(self):
        tokens = tokenize("\\x: x")
        assert tokens[0].type == TokenType.LAMBDA

    def test_unicode_lambda(self):
        tokens = tokenize("\u03bbx: x")
        assert tokens[0].type == TokenType.LAMBDA

    def test_unicode_and(self):
        tokens = tokenize("A \u2227 B")
        assert tokens[1].type == TokenType.AND_SYM

    def test_unicode_or(self):
        tokens = tokenize("A \u2228 B")
        assert tokens[1].type == TokenType.OR_SYM

    def test_unicode_not(self):
        tokens = tokenize("\u00acA")
        assert tokens[0].type == TokenType.NOT_SYM

    def test_unicode_implies(self):
        tokens = tokenize("A \u2192 B")
        assert tokens[1].type == TokenType.IMPLIES

    def test_unicode_iff(self):
        tokens = tokenize("A \u2194 B")
        assert tokens[1].type == TokenType.IFF

    def test_unicode_proves(self):
        tokens = tokenize("G \u22a2 t")
        assert tokens[1].type == TokenType.PROVES

    def test_unicode_equiv(self):
        tokens = tokenize("a \u2261 b")
        assert tokens[1].type == TokenType.EQUIV

    def test_unicode_element_of(self):
        tokens = tokenize("x \u2208 S")
        assert tokens[1].type == TokenType.ELEMENT_OF

    def test_unicode_top_bottom(self):
        tokens = tokenize("\u22a4 \u22a5")
        assert tokens[0].type == TokenType.TOP
        assert tokens[1].type == TokenType.BOTTOM

    def test_unicode_sum_product(self):
        tokens = tokenize("\u2211 \u220f")
        assert tokens[0].type == TokenType.SUM
        assert tokens[1].type == TokenType.PRODUCT_SYM

    def test_dotdot_vs_decimal(self):
        """1..10 should tokenize as NUMBER(1) DOTDOT NUMBER(10), not float 1.0."""
        tokens = tokenize("1..10")
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == "1"
        assert tokens[1].type == TokenType.DOTDOT
        assert tokens[2].type == TokenType.NUMBER
        assert tokens[2].value == "10"

    def test_negative_vs_subtraction(self):
        """After an expression-ending token, - is MINUS; otherwise it's negative."""
        # Binary subtraction
        tokens = tokenize("5 - 3")
        assert tokens[1].type == TokenType.MINUS
        # Negative number at start
        tokens = tokenize("-5")
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == "-5"

    def test_walrus_vs_colon(self):
        """:= is WALRUS, : alone is COLON."""
        tokens = tokenize("x := 5")
        assert tokens[1].type == TokenType.WALRUS
        tokens2 = tokenize("x : 5")
        assert tokens2[1].type == TokenType.COLON


# ===================================================================
# Parser — precedence
# ===================================================================

class TestV02Precedence:
    def test_add_mul_precedence(self):
        """1 + 2 * 3 → 1 + (2 * 3)."""
        node = parse_one("[A bot 1 + 2 * 3]")
        assert isinstance(node, Message)
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "+"
        assert isinstance(expr.left, NumberLiteral)
        assert expr.left.value == 1
        assert isinstance(expr.right, BinaryOp)
        assert expr.right.op == "*"

    def test_power_right_assoc(self):
        """2 ^ 3 ^ 4 → 2 ^ (3 ^ 4)."""
        node = parse_one("[A bot 2 ^ 3 ^ 4]")
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "^"
        assert isinstance(expr.left, NumberLiteral)
        assert expr.left.value == 2
        assert isinstance(expr.right, BinaryOp)
        assert expr.right.op == "^"

    def test_logic_or_and_precedence(self):
        """A | B & C → A | (B & C)."""
        node = parse_one("[A bot A | B & C]")
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "|"
        assert isinstance(expr.right, BinaryOp)
        assert expr.right.op == "&"

    def test_implies_right_assoc(self):
        """A \u2192 B \u2192 C → A \u2192 (B \u2192 C)."""
        node = parse_one("[A bot A \u2192 B \u2192 C]")
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "\u2192"
        assert isinstance(expr.right, BinaryOp)
        assert expr.right.op == "\u2192"

    def test_comparison_flat(self):
        """a == b is left-associative but single comparison is fine."""
        node = parse_one("[A bot a == b]")
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "=="

    def test_double_star_power(self):
        """2 ** 3 is power."""
        node = parse_one("[A bot 2 ** 3]")
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "**"

    def test_parens_override_precedence(self):
        """(1 + 2) * 3 — parentheses override."""
        node = parse_one("[A bot (1 + 2) * 3]")
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "*"
        assert isinstance(expr.left, BinaryOp)
        assert expr.left.op == "+"

    def test_mixed_add_sub(self):
        """1 + 2 - 3 → (1 + 2) - 3."""
        node = parse_one("[A bot 1 + 2 - 3]")
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "-"
        assert isinstance(expr.left, BinaryOp)
        assert expr.left.op == "+"


# ===================================================================
# Parser — constructs
# ===================================================================

class TestV02Constructs:
    def test_lambda_single_param(self):
        node = parse_one("[A bot \u03bbx: x]")
        lam = node.content[0]
        assert isinstance(lam, Lambda)
        assert lam.params == ["x"]
        assert isinstance(lam.body, Identifier)

    def test_lambda_multi_param(self):
        node = parse_one("[A bot \u03bbx y: x]")
        lam = node.content[0]
        assert isinstance(lam, Lambda)
        assert lam.params == ["x", "y"]

    def test_lambda_backslash(self):
        node = parse_one("[A bot \\x y: x]")
        lam = node.content[0]
        assert isinstance(lam, Lambda)
        assert lam.params == ["x", "y"]

    def test_definition(self):
        node = parse_one("[K bot x := 42]")
        defn = node.content[0]
        assert isinstance(defn, Definition)
        assert defn.name == "x"
        assert isinstance(defn.value, NumberLiteral)
        assert defn.value.value == 42

    def test_range(self):
        node = parse_one("[A bot 1..10]")
        r = node.content[0]
        assert isinstance(r, Range)
        assert isinstance(r.start, NumberLiteral)
        assert r.start.value == 1
        assert isinstance(r.end, NumberLiteral)
        assert r.end.value == 10

    def test_element_of(self):
        node = parse_one("[A bot x \u2208 S]")
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "\u2208"

    def test_proves(self):
        node = parse_one("[K bot G \u22a2 t]")
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "\u22a2"

    def test_equiv(self):
        node = parse_one("[A bot a \u2261 b]")
        expr = node.content[0]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "\u2261"

    def test_not_unary(self):
        node = parse_one("[A bot \u00acA]")
        expr = node.content[0]
        assert isinstance(expr, UnaryOp)
        assert expr.op == "\u00ac"

    def test_unary_minus_expr(self):
        """Negative number in parens — lexer produces negative literal."""
        node = parse_one("[A bot (-5)]")
        expr = node.content[0]
        assert isinstance(expr, NumberLiteral)
        assert expr.value == -5

    def test_top_bottom(self):
        node = parse_one("[A bot \u22a4 \u22a5]")
        assert isinstance(node.content[0], Identifier)
        assert node.content[0].name == "\u22a4"
        assert isinstance(node.content[1], Identifier)
        assert node.content[1].name == "\u22a5"

    def test_sum_prefix(self):
        node = parse_one("[A bot \u2211x]")
        expr = node.content[0]
        assert isinstance(expr, UnaryOp)
        assert expr.op == "\u2211"

    def test_product_prefix(self):
        node = parse_one("[A bot \u220fx]")
        expr = node.content[0]
        assert isinstance(expr, UnaryOp)
        assert expr.op == "\u220f"


# ===================================================================
# Serializer roundtrips
# ===================================================================

class TestV02Serializer:
    def test_lambda_roundtrip(self):
        lam = Lambda(params=["x", "y"], body=Identifier(name="x"))
        s = serialize(lam)
        assert s == "\u03bbx y: x"

    def test_definition_roundtrip(self):
        d = Definition(name="x", value=NumberLiteral(value=42))
        s = serialize(d)
        assert s == "x := 42"

    def test_range_roundtrip(self):
        r = Range(start=NumberLiteral(value=1), end=NumberLiteral(value=10))
        s = serialize(r)
        assert s == "1..10"

    def test_binary_plus_serialize(self):
        b = BinaryOp(left=NumberLiteral(value=1), op="+", right=NumberLiteral(value=2))
        s = serialize(b)
        assert s == "1 + 2"


# ===================================================================
# Builder methods
# ===================================================================

class TestV02Builder:
    def test_binop(self):
        m = (msg("A", "bot")
             .binop(NumberLiteral(value=1), "+", NumberLiteral(value=2))
             .build())
        assert isinstance(m.content[0], BinaryOp)
        assert m.content[0].op == "+"

    def test_implies(self):
        m = (msg("A", "bot")
             .implies(Identifier(name="A"), Identifier(name="B"))
             .build())
        assert isinstance(m.content[0], BinaryOp)
        assert m.content[0].op == "\u2192"

    def test_iff(self):
        m = (msg("A", "bot")
             .iff(Identifier(name="A"), Identifier(name="B"))
             .build())
        assert isinstance(m.content[0], BinaryOp)
        assert m.content[0].op == "\u2194"

    def test_lam(self):
        m = (msg("A", "bot")
             .lam(["x"], Identifier(name="x"))
             .build())
        assert isinstance(m.content[0], Lambda)

    def test_define(self):
        m = (msg("K", "bot")
             .define("pi", NumberLiteral(value=3.14))
             .build())
        assert isinstance(m.content[0], Definition)

    def test_range(self):
        m = (msg("A", "bot")
             .range_(NumberLiteral(value=1), NumberLiteral(value=100))
             .build())
        assert isinstance(m.content[0], Range)
