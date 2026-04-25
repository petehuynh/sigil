"""Sigil fluent builder — construct messages programmatically.

Usage:
    from sigil_core import msg

    m = (msg("Q", "grok-1", "user:42")
         .kv("ask", "weather")
         .entity("loc", "singapore")
         .string("tomorrow")
         .prob(None)  # query confidence
         .build())
"""

from __future__ import annotations

from . import ast_nodes as ast
from .serializer import serialize


class MessageBuilder:
    """Fluent builder for Sigil messages."""

    def __init__(self, msg_type: str, sender: str, receiver: str | None = None):
        self._msg_type = msg_type
        self._sender = _parse_name(sender)
        self._receiver = _parse_name(receiver) if receiver else None
        self._content: list[ast.Node] = []

    def kv(self, key: str, value: str | int | float | ast.Node) -> MessageBuilder:
        """Add a key:value pair."""
        if isinstance(value, ast.Node):
            val_node = value
        elif isinstance(value, (int, float)):
            val_node = ast.NumberLiteral(value=value)
        else:
            val_node = ast.Identifier(name=str(value))
        self._content.append(ast.KeyValue(key=key, value=val_node))
        return self

    def string(self, s: str) -> MessageBuilder:
        """Add a string literal."""
        self._content.append(ast.StringLiteral(value=s))
        return self

    def number(self, n: int | float) -> MessageBuilder:
        """Add a number literal."""
        self._content.append(ast.NumberLiteral(value=n))
        return self

    def entity(self, *parts: str) -> MessageBuilder:
        """Add an @entity reference (e.g., entity("loc", "singapore") -> @loc:singapore)."""
        self._content.append(ast.EntityRef(qualified=ast.QualifiedName(parts=list(parts))))
        return self

    def ident(self, name: str) -> MessageBuilder:
        """Add a plain identifier."""
        self._content.append(ast.Identifier(name=name))
        return self

    def prob(self, confidence: float | None = None) -> MessageBuilder:
        """Add a probability qualifier. None = query (prob:?)."""
        if confidence is None:
            self._content.append(ast.Probability(confidence=-1.0))
        else:
            self._content.append(ast.Probability(confidence=confidence))
        return self

    def scope(self, *nodes: ast.Node) -> MessageBuilder:
        """Add a scoped block {...}."""
        self._content.append(ast.Scope(body=list(nodes)))
        return self

    def list_(self, *items: ast.Node) -> MessageBuilder:
        """Add a list [...]."""
        self._content.append(ast.List(items=list(items)))
        return self

    def vec(self, values: list[float]) -> MessageBuilder:
        """Add a vector vec:[...]."""
        self._content.append(ast.Vector(values=values))
        return self

    def node(self, n: ast.Node) -> MessageBuilder:
        """Add an arbitrary AST node."""
        self._content.append(n)
        return self

    def arrow(self, left: ast.Node, right: ast.Node) -> MessageBuilder:
        """Add a left -> right binary op."""
        self._content.append(ast.BinaryOp(left=left, op="->", right=right))
        return self

    # v0.2 builder methods

    def binop(self, left: ast.Node, op: str, right: ast.Node) -> MessageBuilder:
        """Add a binary operation."""
        self._content.append(ast.BinaryOp(left=left, op=op, right=right))
        return self

    def implies(self, left: ast.Node, right: ast.Node) -> MessageBuilder:
        """Add left -> right implication."""
        self._content.append(ast.BinaryOp(left=left, op="\u2192", right=right))
        return self

    def iff(self, left: ast.Node, right: ast.Node) -> MessageBuilder:
        """Add left <-> right biconditional."""
        self._content.append(ast.BinaryOp(left=left, op="\u2194", right=right))
        return self

    def lam(self, params: list[str], body: ast.Node) -> MessageBuilder:
        """Add a lambda expression."""
        self._content.append(ast.Lambda(params=params, body=body))
        return self

    def define(self, name: str, value: ast.Node) -> MessageBuilder:
        """Add a definition (name := value)."""
        self._content.append(ast.Definition(name=name, value=value))
        return self

    def range_(self, start: ast.Node, end: ast.Node) -> MessageBuilder:
        """Add a range (start..end)."""
        self._content.append(ast.Range(start=start, end=end))
        return self

    # v0.3 builder methods

    def pi_type(self, var: str, domain: ast.Node, codomain: ast.Node) -> MessageBuilder:
        """Add a Pi type: Pi(var:domain) codomain."""
        self._content.append(ast.PiType(var=var, domain=domain, codomain=codomain))
        return self

    def sigma_type(self, var: str, domain: ast.Node, body: ast.Node) -> MessageBuilder:
        """Add a Sigma type: Sigma(var:domain) body."""
        self._content.append(ast.SigmaType(var=var, domain=domain, body=body))
        return self

    def judgment(self, ctx: ast.Node, term: ast.Node, type_: ast.Node) -> MessageBuilder:
        """Add a type judgment: ctx |- term : type."""
        self._content.append(ast.TypeJudgment(context=ctx, term=term, type_=type_))
        return self

    def refinement(self, var: str, base: ast.Node, pred: ast.Node) -> MessageBuilder:
        """Add a refinement type: {var:base | pred}."""
        self._content.append(ast.RefinementType(var=var, base_type=base, predicate=pred))
        return self

    # v0.5 builder methods

    def dist(self, name: str, params: list[ast.Node]) -> MessageBuilder:
        """Add a distribution: Dist:name(params)."""
        self._content.append(ast.Distribution(name=name, params=params))
        return self

    def path_type(self, left: ast.Node, right: ast.Node) -> MessageBuilder:
        """Add a path type: left =_Path right."""
        self._content.append(ast.PathType(left=left, right=right))
        return self

    # v1.1 builder methods

    def code_block(self, body: list[ast.Node]) -> MessageBuilder:
        """Add a code block: code: { body }."""
        self._content.append(ast.CodeBlock(body=body))
        return self

    def function_def(self, name: str, params: list[tuple[str, ast.Node]],
                     return_type: ast.Node | None = None,
                     energy: ast.EnergyDecl | None = None,
                     body: list[ast.Node] | None = None) -> MessageBuilder:
        """Add a function definition: fn: name(params) → type { body }."""
        self._content.append(ast.FunctionDef(
            name=name, params=params, return_type=return_type,
            energy=energy, body=body or []))
        return self

    def module_def(self, name: str, body: list[ast.Node]) -> MessageBuilder:
        """Add a module definition: mod: name { body }."""
        self._content.append(ast.ModuleDef(name=name, body=body))
        return self

    def type_def(self, name: str, value: ast.Node) -> MessageBuilder:
        """Add a type definition: type: name := value."""
        self._content.append(ast.TypeDef(name=name, value=value))
        return self

    def test_block(self, name: str, body: list[ast.Node]) -> MessageBuilder:
        """Add a test block: test: name { body }."""
        self._content.append(ast.TestBlock(name=name, body=body))
        return self

    def deploy(self, target: str) -> MessageBuilder:
        """Add a deploy statement: deploy: target."""
        self._content.append(ast.DeployStatement(target=target))
        return self

    def self_heal(self, body: list[ast.Node]) -> MessageBuilder:
        """Add a self:heal block."""
        self._content.append(ast.SelfHealBlock(body=body))
        return self

    def energy(self, amount: float, unit: str = "A") -> MessageBuilder:
        """Add an energy declaration: energy: amount unit."""
        self._content.append(ast.EnergyDecl(amount=amount, unit=unit))
        return self

    def llm(self, action: str, args: list[ast.Node] | None = None) -> MessageBuilder:
        """Add an LLM directive: llm:action(args)."""
        self._content.append(ast.LLMDirective(action=action, args=args or []))
        return self

    def build(self) -> ast.Message:
        """Build the Message AST node."""
        return ast.Message(
            msg_type=self._msg_type,
            sender=self._sender,
            receiver=self._receiver,
            content=list(self._content),
        )

    def to_aether(self) -> str:
        """Build and serialize to Sigil text."""
        return serialize(self.build())


def _parse_name(name: str) -> ast.QualifiedName | ast.Identifier:
    """Parse a colon-separated name string into a node."""
    parts = name.split(":")
    if len(parts) == 1:
        return ast.Identifier(name=parts[0])
    return ast.QualifiedName(parts=parts)


def msg(msg_type: str, sender: str, receiver: str | None = None) -> MessageBuilder:
    """Start building an Sigil message.

    Args:
        msg_type: Message type code (Q, A, C, N, K, E, P, inf, upd)
        sender: Sender ID (e.g., "grok-1" or "ai:src")
        receiver: Optional receiver ID
    """
    return MessageBuilder(msg_type, sender, receiver)
