"""Sigil — the formal language for AI-to-AI communication.

Parse, build, and serialize Sigil messages for precise,
concise, and interoperable AI agent communication.

Quick start:

    from sigil_core import parse_one, msg, serialize

    # Parse a Sigil message
    node = parse_one('[Q grok-1 user:42 ask:weather @loc:singapore "tomorrow" prob:?]')

    # Build a message programmatically
    m = (msg("A", "grok-1", "user:42")
         .number(25)
         .ident("sunny")
         .prob(0.85)
         .build())

    # Serialize back to text
    text = serialize(m)
"""

__version__ = "1.1.0"

from .parser import parse, parse_one
from .serializer import serialize, compact
from .builder import msg, MessageBuilder
from .lexer import tokenize, LexError
from .ast_nodes import (
    Node, Message, Identifier, QualifiedName, EntityRef,
    NumberLiteral, StringLiteral, List, Scope, Vector,
    KeyValue, BinaryOp, UnaryOp, FuncCall, Quantifier, Probability,
    # v0.2
    Lambda, Definition, Range,
    # v0.3
    PiType, SigmaType, InductiveType, TypeJudgment, RefinementType,
    # v0.5
    Distribution, PathType,
    # v1.1 AetherCode
    CodeBlock, FunctionDef, ModuleDef, TypeDef, TestBlock,
    DeployStatement, SelfHealBlock, EnergyDecl, LLMDirective,
)

__all__ = [
    # Core API
    "parse", "parse_one", "serialize", "compact", "msg", "tokenize",
    # Errors
    "LexError",
    # Builder
    "MessageBuilder",
    # AST nodes
    "Node", "Message", "Identifier", "QualifiedName", "EntityRef",
    "NumberLiteral", "StringLiteral", "List", "Scope", "Vector",
    "KeyValue", "BinaryOp", "UnaryOp", "FuncCall", "Quantifier", "Probability",
    # v0.2
    "Lambda", "Definition", "Range",
    # v0.3
    "PiType", "SigmaType", "InductiveType", "TypeJudgment", "RefinementType",
    # v0.5
    "Distribution", "PathType",
    # v1.1 AetherCode
    "CodeBlock", "FunctionDef", "ModuleDef", "TypeDef", "TestBlock",
    "DeployStatement", "SelfHealBlock", "EnergyDecl", "LLMDirective",
]
