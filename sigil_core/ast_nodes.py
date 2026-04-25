"""Sigil AST node definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Node:
    """Base class for all AST nodes."""


# ---------------------------------------------------------------------------
# Literals
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class NumberLiteral(Node):
    value: float | int


@dataclass(slots=True)
class StringLiteral(Node):
    value: str


@dataclass(slots=True)
class Identifier(Node):
    name: str


# ---------------------------------------------------------------------------
# Compound names
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class QualifiedName(Node):
    """namespace:name or multi-part like ai:src, @user:42, tool:call."""
    parts: list[str]

    @property
    def namespace(self) -> str:
        return self.parts[0] if len(self.parts) > 1 else ""

    @property
    def name(self) -> str:
        return self.parts[-1]

    def __str__(self) -> str:
        return ":".join(self.parts)


@dataclass(slots=True)
class EntityRef(Node):
    """@entity:id — reference to an entity."""
    qualified: QualifiedName


# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class List(Node):
    """[item1, item2, ...] or [item1 item2 ...]"""
    items: list[Node] = field(default_factory=list)


@dataclass(slots=True)
class Scope(Node):
    """{content ...} — a scoped block."""
    body: list[Node] = field(default_factory=list)


@dataclass(slots=True)
class Vector(Node):
    """vec:[0.1, 0.2, ...] — embedding vector."""
    values: list[float] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class KeyValue(Node):
    """key:value pair (e.g., prob:0.95, ask:weather)."""
    key: str
    value: Node


@dataclass(slots=True)
class BinaryOp(Node):
    """left op right (e.g., A -> B, x == y)."""
    left: Node
    op: str
    right: Node


@dataclass(slots=True)
class UnaryOp(Node):
    """op expr (e.g., ?, !, ¬, -, ∑)."""
    op: str
    operand: Node


@dataclass(slots=True)
class FuncCall(Node):
    """name(arg1, arg2, ...)."""
    name: str
    args: list[Node] = field(default_factory=list)


@dataclass(slots=True)
class Quantifier(Node):
    """forall x: P or exists x: P."""
    kind: str  # "forall" or "exists"
    variable: str
    body: Node


@dataclass(slots=True)
class Probability(Node):
    """prob:value {statement} — probabilistic qualifier."""
    confidence: float
    statement: Node | None = None


# ---------------------------------------------------------------------------
# v0.2 — Lambda, Definition, Range
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Lambda(Node):
    """lambda x y: body"""
    params: list[str]
    body: Node


@dataclass(slots=True)
class Definition(Node):
    """name := expr"""
    name: str
    value: Node


@dataclass(slots=True)
class Range(Node):
    """start..end"""
    start: Node
    end: Node


# ---------------------------------------------------------------------------
# v0.3 — Type theory
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PiType(Node):
    """Pi(x:A) B — dependent function type."""
    var: str
    domain: Node
    codomain: Node


@dataclass(slots=True)
class SigmaType(Node):
    """Sigma(x:A) B — dependent pair type."""
    var: str
    domain: Node
    body: Node


@dataclass(slots=True)
class InductiveType(Node):
    """Inductive name params := constructors"""
    name: str
    params: list[str]
    constructors: list[Node]


@dataclass(slots=True)
class TypeJudgment(Node):
    """context |- term : type"""
    context: Node
    term: Node
    type_: Node


@dataclass(slots=True)
class RefinementType(Node):
    """{x:A | P(x)} — refinement type"""
    var: str
    base_type: Node
    predicate: Node


# ---------------------------------------------------------------------------
# v0.5 — Probabilistic / HoTT
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Distribution(Node):
    """Dist:Normal(0, 1) — named distribution."""
    name: str
    params: list[Node]


@dataclass(slots=True)
class PathType(Node):
    """x =_Path y — HoTT path type."""
    left: Node
    right: Node


# ---------------------------------------------------------------------------
# Top-level message
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Message(Node):
    """[MSG-TYPE sender receiver? content...]

    MSG-TYPE codes:
      Q = query, A = answer/assert, C = command, N = negotiate,
      K = knowledge transfer, E = error, P = propose,
      inf = infer, upd = update
    """
    msg_type: str
    sender: QualifiedName | Identifier
    receiver: QualifiedName | Identifier | None = None
    content: list[Node] = field(default_factory=list)
    timestamp: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# v1.1 — AetherCode
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class CodeBlock(Node):
    """code: { ... } — top-level code container."""
    body: list[Node] = field(default_factory=list)


@dataclass(slots=True)
class FunctionDef(Node):
    """fn: name(params) → returnType energy:N { body }"""
    name: str
    params: list[tuple[str, Node]]
    return_type: Node | None = None
    energy: 'EnergyDecl | None' = None
    body: list[Node] = field(default_factory=list)


@dataclass(slots=True)
class ModuleDef(Node):
    """mod: name { ... }"""
    name: str
    body: list[Node] = field(default_factory=list)


@dataclass(slots=True)
class TypeDef(Node):
    """type: name := typeExpr"""
    name: str
    value: Node | None = None


@dataclass(slots=True)
class TestBlock(Node):
    """test: name { ... }"""
    name: str
    body: list[Node] = field(default_factory=list)


@dataclass(slots=True)
class DeployStatement(Node):
    """deploy: target"""
    target: str
    platform: str | None = None
    energy: 'EnergyDecl | None' = None


@dataclass(slots=True)
class SelfHealBlock(Node):
    """self:heal { ... }"""
    body: list[Node] = field(default_factory=list)


@dataclass(slots=True)
class EnergyDecl(Node):
    """energy: number unit"""
    amount: float
    unit: str = "A"


@dataclass(slots=True)
class LLMDirective(Node):
    """llm:gen, llm:refine, llm:verify"""
    action: str
    args: list[Node] = field(default_factory=list)
