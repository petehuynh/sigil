"""Tests for Sigil lexer, parser, serializer, and builder."""

from __future__ import annotations

import pytest

from sigil_core import (
    parse_one, parse, serialize, compact, msg, tokenize,
    Message, Identifier, QualifiedName, EntityRef,
    NumberLiteral, StringLiteral, List, Scope, Vector,
    KeyValue, BinaryOp, UnaryOp, FuncCall, Quantifier, Probability,
)
from sigil_core.lexer import LexError
from sigil_core.parser import ParseError


# ===================================================================
# Lexer tests
# ===================================================================

class TestLexer:
    def test_simple_tokens(self):
        tokens = tokenize("[Q grok-1]")
        types = [t.type.name for t in tokens]
        assert "LBRACKET" in types
        assert "RBRACKET" in types
        assert "IDENTIFIER" in types
        assert types[-1] == "EOF"

    def test_operators(self):
        tokens = tokenize("-> <- == =/= ? ! ~ @ # | & ^")
        names = [t.type.name for t in tokens[:-1]]  # exclude EOF
        assert "ARROW" in names
        assert "BACK_ARROW" in names
        assert "EQUALS" in names
        assert "NOT_EQUALS" in names

    def test_string_double_quotes(self):
        tokens = tokenize('"hello world"')
        assert tokens[0].type.name == "STRING"
        assert tokens[0].value == "hello world"

    def test_string_single_quotes(self):
        tokens = tokenize("'short'")
        assert tokens[0].type.name == "STRING"
        assert tokens[0].value == "short"

    def test_number_integer(self):
        tokens = tokenize("42")
        assert tokens[0].type.name == "NUMBER"
        assert tokens[0].value == "42"

    def test_number_float(self):
        tokens = tokenize("3.14")
        assert tokens[0].type.name == "NUMBER"
        assert tokens[0].value == "3.14"

    def test_negative_number(self):
        tokens = tokenize("-5")
        assert tokens[0].type.name == "NUMBER"
        assert tokens[0].value == "-5"

    def test_unicode_quantifiers(self):
        tokens = tokenize("\u2200x \u2203y")
        assert tokens[0].type.name == "FORALL"
        assert tokens[2].type.name == "EXISTS"

    def test_keyword_forall(self):
        tokens = tokenize("forall x")
        assert tokens[0].type.name == "FORALL"

    def test_comment_skipped(self):
        tokens = tokenize(";; this is a comment\n42")
        assert tokens[0].type.name == "NUMBER"
        assert tokens[0].value == "42"

    def test_unterminated_string(self):
        with pytest.raises(LexError, match="Unterminated"):
            tokenize('"no end')


# ===================================================================
# Parser tests — spec examples
# ===================================================================

class TestParserSpecExamples:
    """Test all examples from the Sigil spec."""

    def test_simple_query(self):
        """Example 1: Simple query."""
        node = parse_one('[Q grok-1 user:42 ask:weather @loc:singapore "tomorrow" prob:?]')
        assert isinstance(node, Message)
        assert node.msg_type == "Q"
        assert isinstance(node.sender, Identifier)
        assert node.sender.name == "grok-1"
        assert isinstance(node.receiver, QualifiedName)
        assert str(node.receiver) == "user:42"
        assert len(node.content) >= 3

    def test_simple_response(self):
        """Example 1: Response."""
        node = parse_one("[A grok-1 user:42 25 sunny prob:0.85]")
        assert isinstance(node, Message)
        assert node.msg_type == "A"
        # Check content
        nums = [c for c in node.content if isinstance(c, (NumberLiteral, Identifier))]
        assert any(isinstance(c, NumberLiteral) and c.value == 25 for c in node.content)
        probs = [c for c in node.content if isinstance(c, Probability)]
        assert len(probs) == 1
        assert probs[0].confidence == 0.85

    def test_knowledge_transfer(self):
        """Example 2: Knowledge transfer."""
        src = '[K ai:src ai:dst fact:@physics:e=mc2 rule:energy-conservation {forall sys: closed -> deltaE == 0}]'
        node = parse_one(src)
        assert isinstance(node, Message)
        assert node.msg_type == "K"
        assert isinstance(node.sender, QualifiedName)
        assert str(node.sender) == "ai:src"

    def test_negotiation(self):
        """Example 4: Negotiation."""
        src = '[N agentA agentB bid:trade {data:datasetX for compute:10min} agree:?]'
        node = parse_one(src)
        assert isinstance(node, Message)
        assert node.msg_type == "N"
        assert node.sender.name == "agentA"
        assert node.receiver.name == "agentB"

    def test_complex_assertion(self):
        """Example 5: Complex assertion with context."""
        src = '[A modelX peerY prob:0.92 {statement: outcome ~ best | alt:[worst, avg]} {context: market:2026Q2}]'
        node = parse_one(src)
        assert isinstance(node, Message)
        assert node.msg_type == "A"


# ===================================================================
# Parser tests — individual constructs
# ===================================================================

class TestParserConstructs:
    def test_entity_ref(self):
        node = parse_one("[Q bot @user:42]")
        assert isinstance(node, Message)
        entities = [c for c in node.content if isinstance(c, EntityRef)]
        assert len(entities) == 1
        assert str(entities[0].qualified) == "user:42"

    def test_list(self):
        node = parse_one("[C bot [step1, step2, step3]]")
        assert isinstance(node, Message)
        lists = [c for c in node.content if isinstance(c, List)]
        assert len(lists) == 1
        assert len(lists[0].items) == 3

    def test_scope(self):
        node = parse_one("[A bot {x == 1}]")
        assert isinstance(node, Message)
        scopes = [c for c in node.content if isinstance(c, Scope)]
        assert len(scopes) == 1

    def test_binary_op_arrow(self):
        node = parse_one("[C bot A -> B]")
        assert isinstance(node, Message)
        arrows = [c for c in node.content if isinstance(c, BinaryOp)]
        assert len(arrows) == 1
        assert arrows[0].op == "->"

    def test_probability_with_value(self):
        node = parse_one("[A bot prob:0.95]")
        assert isinstance(node, Message)
        probs = [c for c in node.content if isinstance(c, Probability)]
        assert len(probs) == 1
        assert probs[0].confidence == 0.95

    def test_probability_query(self):
        node = parse_one("[Q bot prob:?]")
        assert isinstance(node, Message)
        probs = [c for c in node.content if isinstance(c, Probability)]
        assert len(probs) == 1
        assert probs[0].confidence == -1.0  # query marker

    def test_quantifier_forall(self):
        node = parse_one("[K bot {forall x: P(x)}]")
        assert isinstance(node, Message)

    def test_key_value_string(self):
        node = parse_one('[Q bot ask:"what is life"]')
        assert isinstance(node, Message)
        kvs = [c for c in node.content if isinstance(c, KeyValue)]
        assert len(kvs) == 1
        assert kvs[0].key == "ask"
        assert isinstance(kvs[0].value, StringLiteral)

    def test_key_value_number(self):
        node = parse_one("[A bot score:42]")
        assert isinstance(node, Message)
        kvs = [c for c in node.content if isinstance(c, KeyValue)]
        assert len(kvs) == 1
        assert kvs[0].key == "score"
        assert isinstance(kvs[0].value, NumberLiteral)
        assert kvs[0].value.value == 42

    def test_vector(self):
        node = parse_one("[K bot vec:[0.1, 0.2, 0.3]]")
        assert isinstance(node, Message)
        vecs = [c for c in node.content if isinstance(c, Vector)]
        assert len(vecs) == 1
        assert vecs[0].values == [0.1, 0.2, 0.3]

    def test_func_call(self):
        node = parse_one("[C bot eval(cost, time)]")
        assert isinstance(node, Message)
        funcs = [c for c in node.content if isinstance(c, FuncCall)]
        assert len(funcs) == 1
        assert funcs[0].name == "eval"
        assert len(funcs[0].args) == 2

    def test_message_no_receiver(self):
        node = parse_one("[E bot error:500]")
        assert isinstance(node, Message)
        assert node.msg_type == "E"
        assert node.sender.name == "bot"

    def test_multiple_messages(self):
        nodes = parse("[Q a b] [A b a ok:1]")
        assert len(nodes) == 2
        assert all(isinstance(n, Message) for n in nodes)


# ===================================================================
# Serializer tests
# ===================================================================

class TestSerializer:
    def test_roundtrip_simple(self):
        src = "[A grok-1 user:42 25 sunny prob:0.85]"
        node = parse_one(src)
        out = serialize(node)
        # Re-parse the serialized output
        node2 = parse_one(out)
        assert isinstance(node2, Message)
        assert node2.msg_type == node.msg_type

    def test_compact_removes_whitespace(self):
        node = parse_one("[Q  bot   peer  ask:weather]")
        c = compact(node)
        assert "  " not in c

    def test_serialize_entity(self):
        node = EntityRef(qualified=QualifiedName(parts=["loc", "singapore"]))
        assert serialize(node) == "@loc:singapore"

    def test_serialize_vector(self):
        node = Vector(values=[1.0, 2.0, 3.0])
        assert serialize(node) == "vec:[1.0, 2.0, 3.0]"

    def test_serialize_scope(self):
        node = Scope(body=[Identifier(name="x"), Identifier(name="y")])
        assert serialize(node) == "{x y}"

    def test_serialize_binary_op(self):
        node = BinaryOp(
            left=Identifier(name="A"),
            op="->",
            right=Identifier(name="B"),
        )
        assert serialize(node) == "A -> B"

    def test_serialize_func_call(self):
        node = FuncCall(name="eval", args=[Identifier(name="x"), NumberLiteral(value=1)])
        assert serialize(node) == "eval(x, 1)"


# ===================================================================
# Builder tests
# ===================================================================

class TestBuilder:
    def test_build_query(self):
        m = (msg("Q", "grok-1", "user:42")
             .kv("ask", "weather")
             .entity("loc", "singapore")
             .string("tomorrow")
             .prob(None)
             .build())
        assert isinstance(m, Message)
        assert m.msg_type == "Q"
        assert m.sender.name == "grok-1"
        assert str(m.receiver) == "user:42"
        assert len(m.content) == 4

    def test_build_response(self):
        m = (msg("A", "grok-1", "user:42")
             .number(25)
             .ident("sunny")
             .prob(0.85)
             .build())
        assert isinstance(m, Message)
        assert m.content[0].value == 25

    def test_to_aether(self):
        text = (msg("Q", "bot", "peer")
                .kv("ask", "status")
                .to_aether())
        assert text.startswith("[Q")
        assert "ask:status" in text

    def test_build_with_scope(self):
        m = (msg("K", "ai:src", "ai:dst")
             .scope(
                 BinaryOp(
                     left=Identifier(name="A"),
                     op="->",
                     right=Identifier(name="B"),
                 )
             )
             .build())
        assert isinstance(m, Message)
        assert isinstance(m.content[0], Scope)

    def test_build_with_vector(self):
        m = (msg("K", "bot")
             .vec([0.1, 0.2, 0.3])
             .build())
        assert isinstance(m.content[0], Vector)

    def test_build_with_list(self):
        m = (msg("C", "planner")
             .list_(Identifier(name="step1"), Identifier(name="step2"))
             .build())
        assert isinstance(m.content[0], List)
        assert len(m.content[0].items) == 2

    def test_build_with_arrow(self):
        m = (msg("C", "bot")
             .arrow(Identifier(name="cause"), Identifier(name="effect"))
             .build())
        assert isinstance(m.content[0], BinaryOp)
        assert m.content[0].op == "->"


# ===================================================================
# Edge cases
# ===================================================================

class TestEdgeCases:
    def test_empty_message(self):
        """Minimal message with just type and sender."""
        node = parse_one("[Q bot]")
        assert isinstance(node, Message)
        assert node.msg_type == "Q"
        assert node.sender.name == "bot"
        assert node.receiver is None

    def test_nested_scopes(self):
        node = parse_one("[C bot {a {b {c}}}]")
        assert isinstance(node, Message)

    def test_mixed_content(self):
        node = parse_one('[A bot 42 "hello" prob:0.9 @user:1 [a, b]]')
        assert isinstance(node, Message)
        assert len(node.content) >= 4

    def test_parse_error_unclosed(self):
        with pytest.raises(ParseError):
            parse_one("[Q bot")

    def test_lex_error_bad_char(self):
        with pytest.raises(LexError):
            tokenize("$$$")
