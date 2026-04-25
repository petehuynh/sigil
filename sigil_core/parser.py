"""Sigil recursive-descent parser.

Grammar (simplified):

    program       := message* EOF
    message       := '[' msg_type expr expr expr* ']'
    expr          := binary_expr
    binary_expr   := unary_expr (OP unary_expr)*    [precedence climbing]
    unary_expr    := ('?' | '!' | '¬' | '-' | math_prefix) atom | atom
    atom          := NUMBER | STRING | entity_ref | qualified_or_kv
                   | list | scope | func_call | quantifier | vec
                   | lambda | pi_type | sigma_type | TOP | BOTTOM
    entity_ref    := '@' qualified_name
    qualified_or_kv := IDENT (':' (atom | '?'))?
    list          := '[' (expr (',' | expr)*)? ']'
    scope         := '{' expr* '}'  |  '{' IDENT ':' type '|' expr '}'
    func_call     := IDENT '(' (expr (',' expr)*)? ')'
    quantifier    := (FORALL | EXISTS) IDENT ':' expr
    vec           := 'vec' ':' '[' (NUMBER (',' NUMBER)*)? ']'
    lambda        := LAMBDA IDENT+ ':' expr
    pi_type       := PI_TYPE '(' IDENT ':' expr ')' expr
    sigma_type    := SIGMA_TYPE '(' IDENT ':' expr ')' expr
"""

from __future__ import annotations

from .tokens import Token, TokenType
from .lexer import tokenize
from . import ast_nodes as ast


MSG_TYPES = {"Q", "A", "C", "N", "K", "E", "P", "inf", "upd"}

# v1.1 AetherCode keywords — these should not be consumed as receiver names
_V11_KEYWORDS = frozenset({"fn", "mod", "code", "type", "test", "deploy", "self", "energy", "llm"})

# ---------------------------------------------------------------------------
# Precedence table  (level, associativity)
# Higher number = tighter binding
# ---------------------------------------------------------------------------
PRECEDENCE: dict[TokenType, tuple[int, str]] = {
    # Level 1 — message flow / morphisms
    TokenType.ARROW:        (1, "left"),
    TokenType.BACK_ARROW:   (1, "left"),
    TokenType.LONG_ARROW:   (1, "left"),
    TokenType.DOUBLE_ARROW: (1, "left"),
    # Level 2 — biconditional
    TokenType.IFF:          (2, "left"),
    # Level 3 — implies (right-assoc)
    TokenType.IMPLIES:      (3, "right"),
    # Level 4 — logical OR
    TokenType.OR_SYM:       (4, "left"),
    TokenType.PIPE:         (4, "left"),
    TokenType.XOR:          (4, "left"),
    # Level 5 — logical AND
    TokenType.AND_SYM:      (5, "left"),
    TokenType.AMP:          (5, "left"),
    # Level 6 — comparison / relation
    TokenType.EQUALS:       (6, "left"),
    TokenType.NOT_EQUALS:   (6, "left"),
    TokenType.TILDE:        (6, "left"),
    TokenType.LT:           (6, "left"),
    TokenType.GT:           (6, "left"),
    TokenType.LTE:          (6, "left"),
    TokenType.GTE:          (6, "left"),
    TokenType.APPROX:       (6, "left"),
    TokenType.EQUIV:        (6, "left"),
    TokenType.NOT_EQUIV:    (6, "left"),
    TokenType.ELEMENT_OF:   (6, "left"),
    TokenType.SUBSET:       (6, "left"),
    TokenType.PROPER_SUBSET:(6, "left"),
    TokenType.MUCH_LESS:    (6, "left"),
    TokenType.MUCH_GREATER: (6, "left"),
    TokenType.ISO:          (6, "left"),
    TokenType.EQUIV_TYPE:   (6, "left"),
    TokenType.PROPORTIONAL: (6, "left"),
    # Level 7 — proves / adjoint
    TokenType.PROVES:       (7, "left"),
    TokenType.ADJOINT:      (7, "left"),
    # Level 8 — additive
    TokenType.PLUS:         (8, "left"),
    TokenType.MINUS:        (8, "left"),
    # Level 9 — multiplicative
    TokenType.STAR:         (9, "left"),
    TokenType.SLASH:        (9, "left"),
    TokenType.PERCENT:      (9, "left"),
    # Level 10 — power (right-assoc)
    TokenType.CARET:        (10, "right"),
    TokenType.DOUBLE_STAR:  (10, "right"),
    # Level 11 — composition
    TokenType.COMPOSE:      (11, "left"),
}

# Math prefix operators
_MATH_PREFIX = frozenset({
    TokenType.SUM, TokenType.PRODUCT_SYM, TokenType.INTEGRAL,
    TokenType.PARTIAL, TokenType.NABLA, TokenType.DELTA,
})


class ParseError(Exception):
    def __init__(self, msg: str, token: Token | None = None):
        loc = f" at {token.line}:{token.col}" if token else ""
        super().__init__(f"Parse error{loc}: {msg}")
        self.token = token


class Parser:
    """Recursive-descent parser for Sigil."""

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _at(self, *types: TokenType) -> bool:
        return self._peek().type in types

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _expect(self, tt: TokenType, msg: str = "") -> Token:
        tok = self._advance()
        if tok.type != tt:
            raise ParseError(msg or f"Expected {tt.name}, got {tok.type.name} ({tok.value!r})", tok)
        return tok

    def _match(self, *types: TokenType) -> Token | None:
        if self._peek().type in types:
            return self._advance()
        return None

    # ------------------------------------------------------------------
    # top-level
    # ------------------------------------------------------------------

    def parse(self) -> list[ast.Node]:
        """Parse full program — returns list of top-level nodes (usually Messages)."""
        nodes: list[ast.Node] = []
        while not self._at(TokenType.EOF):
            if self._at(TokenType.LBRACKET):
                nodes.append(self._parse_message_or_list())
            else:
                nodes.append(self._parse_expr())
        return nodes

    def parse_one(self) -> ast.Node:
        """Parse a single message/expression."""
        if self._at(TokenType.LBRACKET):
            return self._parse_message_or_list()
        return self._parse_expr()

    # ------------------------------------------------------------------
    # message vs list disambiguation
    # ------------------------------------------------------------------

    def _parse_message_or_list(self) -> ast.Node:
        """After seeing '[', decide if this is a Message or a List."""
        saved = self.pos
        self._advance()  # consume '['
        tok = self._peek()

        # If next token is an identifier that matches a MSG_TYPE, it's a message
        if tok.type == TokenType.IDENTIFIER and tok.value in MSG_TYPES:
            return self._parse_message_body()

        # Otherwise it's a list
        self.pos = saved
        return self._parse_list()

    # ------------------------------------------------------------------
    # message
    # ------------------------------------------------------------------

    def _parse_message_body(self) -> ast.Message:
        """Parse message body after '[' has been consumed and MSG-TYPE confirmed."""
        msg_type_tok = self._advance()
        msg_type = msg_type_tok.value

        # sender (required)
        sender = self._parse_name()

        # receiver (optional — another name before content)
        receiver: ast.QualifiedName | ast.Identifier | None = None
        if not self._at(TokenType.RBRACKET, TokenType.EOF):
            saved = self.pos
            candidate = self._try_parse_name()
            if candidate is not None:
                is_receiver = True
                if isinstance(candidate, ast.Identifier):
                    # Plain IDENT followed by COLON → key:value content
                    # Plain IDENT followed by LPAREN → function call
                    # Plain IDENT followed by WALRUS → definition
                    # Plain IDENT followed by operator → binary expression
                    if self._at(TokenType.COLON, TokenType.LPAREN, TokenType.WALRUS) or self._peek().type in PRECEDENCE:
                        is_receiver = False
                if is_receiver and isinstance(candidate, ast.QualifiedName):
                    # v1.1 keywords (fn:, mod:, etc.) are content, not receivers
                    if candidate.parts[0] in _V11_KEYWORDS:
                        is_receiver = False
                    elif self._at(TokenType.RBRACKET, TokenType.EOF):
                        is_receiver = False
                    elif self._at(TokenType.LPAREN):
                        # QualifiedName followed by ( → function call pattern (e.g., Dist:Normal(...))
                        is_receiver = False
                if is_receiver:
                    receiver = candidate
                else:
                    self.pos = saved

        # content expressions until ']'
        content: list[ast.Node] = []
        while not self._at(TokenType.RBRACKET, TokenType.EOF):
            content.append(self._parse_expr())

        self._expect(TokenType.RBRACKET, "Expected ']' to close message")
        return ast.Message(msg_type=msg_type, sender=sender, receiver=receiver, content=content)

    def _parse_name(self) -> ast.QualifiedName | ast.Identifier:
        """Parse a name: IDENT or IDENT:IDENT(:IDENT)*."""
        tok = self._expect(TokenType.IDENTIFIER, "Expected identifier for name")
        parts = [tok.value]
        while self._at(TokenType.COLON):
            saved = self.pos
            self._advance()  # consume ':'
            if self._at(TokenType.IDENTIFIER, TokenType.NUMBER):
                nxt = self._advance()
                parts.append(nxt.value)
            elif self._at(TokenType.QUESTION):
                self.pos = saved
                break
            else:
                self.pos = saved
                break
        if len(parts) == 1:
            return ast.Identifier(name=parts[0])
        return ast.QualifiedName(parts=parts)

    def _try_parse_name(self) -> ast.QualifiedName | ast.Identifier | None:
        """Try to parse a name; return None and rollback on failure."""
        if not self._at(TokenType.IDENTIFIER):
            return None
        saved = self.pos
        try:
            return self._parse_name()
        except ParseError:
            self.pos = saved
            return None

    # ------------------------------------------------------------------
    # expressions
    # ------------------------------------------------------------------

    def _parse_expr(self) -> ast.Node:
        return self._parse_binary()

    def _parse_binary(self, min_prec: int = 0) -> ast.Node:
        """Precedence-climbing binary expression parser."""
        left = self._parse_unary()

        while True:
            entry = PRECEDENCE.get(self._peek().type)
            if entry is None:
                break
            prec, assoc = entry
            if prec < min_prec:
                break
            op_tok = self._advance()
            next_min = prec + 1 if assoc == "left" else prec
            right = self._parse_binary(next_min)
            left = ast.BinaryOp(left=left, op=op_tok.value, right=right)

        # Check for postfix .. (range)
        left = self._parse_postfix(left)

        return left

    def _parse_postfix(self, left: ast.Node) -> ast.Node:
        """Handle postfix operators like .. (range)."""
        if self._at(TokenType.DOTDOT):
            self._advance()
            right = self._parse_unary()
            return ast.Range(start=left, end=right)
        return left

    def _parse_unary(self) -> ast.Node:
        # ? unary
        if self._at(TokenType.QUESTION):
            op = self._advance()
            operand = self._parse_atom()
            return ast.UnaryOp(op=op.value, operand=operand)
        # ! unary
        if self._at(TokenType.BANG):
            op = self._advance()
            operand = self._parse_atom()
            return ast.UnaryOp(op=op.value, operand=operand)
        # NOT_SYM (¬) unary
        if self._at(TokenType.NOT_SYM):
            op = self._advance()
            operand = self._parse_unary()
            return ast.UnaryOp(op=op.value, operand=operand)
        # Unary minus
        if self._at(TokenType.MINUS):
            op = self._advance()
            operand = self._parse_unary()
            return ast.UnaryOp(op=op.value, operand=operand)
        # Math prefix operators (∑ ∏ ∫ ∂ ∇ Δ)
        if self._peek().type in _MATH_PREFIX:
            op = self._advance()
            operand = self._parse_unary()
            return ast.UnaryOp(op=op.value, operand=operand)

        return self._parse_atom()

    def _parse_atom(self) -> ast.Node:
        tok = self._peek()

        # Number
        if tok.type == TokenType.NUMBER:
            self._advance()
            val = float(tok.value) if "." in tok.value else int(tok.value)
            return ast.NumberLiteral(value=val)

        # String
        if tok.type == TokenType.STRING:
            self._advance()
            return ast.StringLiteral(value=tok.value)

        # Entity reference: @name
        if tok.type == TokenType.AT:
            self._advance()
            name = self._parse_name()
            if isinstance(name, ast.Identifier):
                name = ast.QualifiedName(parts=[name.name])
            return ast.EntityRef(qualified=name)

        # List or nested message: [...]
        if tok.type == TokenType.LBRACKET:
            return self._parse_message_or_list()

        # Scope or refinement type: {...}
        if tok.type == TokenType.LBRACE:
            return self._parse_scope()

        # Quantifier: forall/exists
        if tok.type in (TokenType.FORALL, TokenType.EXISTS):
            return self._parse_quantifier()

        # Lambda: λ or \
        if tok.type == TokenType.LAMBDA:
            return self._parse_lambda()

        # Pi type: Π(x:A) B
        if tok.type == TokenType.PI_TYPE:
            return self._parse_pi_type()

        # Sigma type: Σ(x:A) B
        if tok.type == TokenType.SIGMA_TYPE:
            return self._parse_sigma_type()

        # Constants: ⊤ ⊥
        if tok.type == TokenType.TOP:
            self._advance()
            return ast.Identifier(name="\u22a4")

        if tok.type == TokenType.BOTTOM:
            self._advance()
            return ast.Identifier(name="\u22a5")

        # Identifier — could be: plain ident, qualified name, key:value,
        # func call, vec:[], prob:N, Dist:Name(...), name := expr
        if tok.type == TokenType.IDENTIFIER:
            return self._parse_ident_expr()

        # Standalone operators used as markers (e.g., trailing ?)
        if tok.type == TokenType.QUESTION:
            self._advance()
            return ast.Identifier(name="?")

        # Parenthesized expression
        if tok.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_expr()
            self._expect(TokenType.RPAREN, "Expected ')' to close parenthesized expression")
            return expr

        raise ParseError(f"Unexpected token: {tok.type.name} ({tok.value!r})", tok)

    def _parse_ident_expr(self) -> ast.Node:
        """Parse expression starting with an identifier."""
        tok = self._advance()
        name = tok.value

        # func call: name(...)
        if self._at(TokenType.LPAREN):
            return self._parse_func_call(name)

        # := definition: name := expr
        if self._at(TokenType.WALRUS):
            self._advance()
            value = self._parse_expr()
            return ast.Definition(name=name, value=value)

        # qualified name or key:value
        if self._at(TokenType.COLON):
            saved = self.pos
            self._advance()  # consume ':'

            # vec:[...]
            if name == "vec" and self._at(TokenType.LBRACKET):
                return self._parse_vector()

            # prob:N or prob:?
            if name == "prob":
                if self._at(TokenType.NUMBER):
                    num_tok = self._advance()
                    conf = float(num_tok.value)
                    stmt = None
                    if self._at(TokenType.LBRACE):
                        stmt = self._parse_scope()
                    return ast.Probability(confidence=conf, statement=stmt)
                if self._at(TokenType.QUESTION):
                    self._advance()
                    return ast.Probability(confidence=-1.0, statement=None)

            # Dist:Name(...) — Distribution
            if name == "Dist" and self._at(TokenType.IDENTIFIER):
                dist_name_tok = self._advance()
                dist_name = dist_name_tok.value
                params: list[ast.Node] = []
                if self._at(TokenType.LPAREN):
                    self._advance()
                    while not self._at(TokenType.RPAREN, TokenType.EOF):
                        params.append(self._parse_expr())
                        self._match(TokenType.COMMA)
                    self._expect(TokenType.RPAREN, "Expected ')' to close distribution params")
                return ast.Distribution(name=dist_name, params=params)

            # v1.1 AetherCode constructs

            # code: { ... }
            if name == "code" and self._at(TokenType.LBRACE):
                return self._parse_code_block()

            # fn: name(params) → type energy:N { body }
            if name == "fn" and self._at(TokenType.IDENTIFIER):
                return self._parse_function_def()

            # mod: name { ... }
            if name == "mod" and self._at(TokenType.IDENTIFIER):
                return self._parse_module_def()

            # type: name := typeExpr — requires lookahead to confirm :=
            if name == "type" and self._at(TokenType.IDENTIFIER):
                saved_td = self.pos
                self._advance()  # tentatively consume name
                if self._at(TokenType.WALRUS):
                    self.pos = saved_td  # rollback, let _parse_type_def() consume
                    return self._parse_type_def()
                self.pos = saved_td  # not a type def, fall through

            # test: name { ... }
            if name == "test" and self._at(TokenType.IDENTIFIER):
                return self._parse_test_block()

            # deploy: target
            if name == "deploy" and self._at(TokenType.IDENTIFIER):
                return self._parse_deploy_stmt()

            # self:heal { ... }
            if name == "self" and self._at(TokenType.IDENTIFIER) and self._peek().value == "heal":
                self._advance()  # consume 'heal'
                return self._parse_self_heal()

            # energy: number unit
            if name == "energy" and self._at(TokenType.NUMBER):
                return self._parse_energy_decl()

            # llm:gen, llm:refine, llm:verify
            if name == "llm" and self._at(TokenType.IDENTIFIER):
                action_tok = self._advance()
                return self._parse_llm_directive(action_tok.value)

            # key:? — query marker
            if self._at(TokenType.QUESTION):
                self._advance()
                return ast.KeyValue(key=name, value=ast.Identifier(name="?"))

            # key:value — parse the value as another atom/expr
            if not self._at(TokenType.RBRACKET, TokenType.RBRACE, TokenType.RPAREN, TokenType.EOF):
                # Could be qualified name (key:ident:ident...) or key:value
                if self._at(TokenType.IDENTIFIER):
                    # Check if this is qualified name (multi-part) or key:value
                    val_tok = self._advance()
                    parts = [name, val_tok.value]
                    # Continue collecting colon-separated parts
                    while self._at(TokenType.COLON):
                        s2 = self.pos
                        self._advance()
                        if self._at(TokenType.IDENTIFIER, TokenType.NUMBER):
                            nxt = self._advance()
                            parts.append(nxt.value)
                        else:
                            self.pos = s2
                            break

                    # If the qualified name is followed by content that looks
                    # like a value, treat first as key and rest as value
                    if len(parts) == 2 and self._at(
                        TokenType.STRING, TokenType.LBRACKET, TokenType.LBRACE,
                        TokenType.LPAREN, TokenType.AT,
                    ):
                        return ast.KeyValue(
                            key=name,
                            value=ast.Identifier(name=parts[1]),
                        )

                    return ast.QualifiedName(parts=parts)

                if self._at(TokenType.NUMBER):
                    num_tok = self._advance()
                    val = float(num_tok.value) if "." in num_tok.value else int(num_tok.value)
                    return ast.KeyValue(key=name, value=ast.NumberLiteral(value=val))

                if self._at(TokenType.STRING):
                    str_tok = self._advance()
                    return ast.KeyValue(key=name, value=ast.StringLiteral(value=str_tok.value))

                if self._at(TokenType.LBRACKET):
                    val = self._parse_message_or_list()
                    return ast.KeyValue(key=name, value=val)

                if self._at(TokenType.LBRACE):
                    val = self._parse_scope()
                    return ast.KeyValue(key=name, value=val)

                if self._at(TokenType.AT):
                    val = self._parse_atom()
                    return ast.KeyValue(key=name, value=val)

            # Bare colon at end or before closing bracket — roll back
            self.pos = saved
            return ast.Identifier(name=name)

        return ast.Identifier(name=name)

    # ------------------------------------------------------------------
    # v1.1 AetherCode parse methods
    # ------------------------------------------------------------------

    def _parse_code_block(self) -> ast.CodeBlock:
        """Parse code: { ... } — colon already consumed."""
        self._expect(TokenType.LBRACE)
        body: list[ast.Node] = []
        while not self._at(TokenType.RBRACE, TokenType.EOF):
            body.append(self._parse_expr())
        self._expect(TokenType.RBRACE)
        return ast.CodeBlock(body=body)

    def _parse_function_def(self) -> ast.FunctionDef:
        """Parse fn: name(params) → type energy:N { body } — colon already consumed."""
        name_tok = self._expect(TokenType.IDENTIFIER, "Expected function name")
        self._expect(TokenType.LPAREN, "Expected '(' after function name")
        params: list[tuple[str, ast.Node]] = []
        while not self._at(TokenType.RPAREN, TokenType.EOF):
            p_name = self._expect(TokenType.IDENTIFIER, "Expected parameter name").value
            self._expect(TokenType.COLON, "Expected ':' after parameter name")
            p_type = self._parse_atom()
            params.append((p_name, p_type))
            self._match(TokenType.COMMA)
        self._expect(TokenType.RPAREN, "Expected ')' to close parameters")
        return_type: ast.Node | None = None
        if self._at(TokenType.IMPLIES) or self._at(TokenType.ARROW):
            self._advance()
            return_type = self._parse_atom()
        energy: ast.EnergyDecl | None = None
        if self._at(TokenType.IDENTIFIER) and self._peek().value == "energy":
            saved = self.pos
            self._advance()  # consume 'energy'
            if self._at(TokenType.COLON):
                self._advance()  # consume ':'
                energy = self._parse_energy_decl_inner()
            else:
                self.pos = saved
        body: list[ast.Node] = []
        if self._at(TokenType.LBRACE):
            self._advance()
            while not self._at(TokenType.RBRACE, TokenType.EOF):
                body.append(self._parse_expr())
            self._expect(TokenType.RBRACE)
        return ast.FunctionDef(name=name_tok.value, params=params,
                               return_type=return_type, energy=energy, body=body)

    def _parse_module_def(self) -> ast.ModuleDef:
        """Parse mod: name { ... } — colon already consumed."""
        name_tok = self._expect(TokenType.IDENTIFIER, "Expected module name")
        self._expect(TokenType.LBRACE, "Expected '{' after module name")
        body: list[ast.Node] = []
        while not self._at(TokenType.RBRACE, TokenType.EOF):
            body.append(self._parse_expr())
        self._expect(TokenType.RBRACE)
        return ast.ModuleDef(name=name_tok.value, body=body)

    def _parse_type_def(self) -> ast.TypeDef:
        """Parse type: name := typeExpr — colon already consumed."""
        name_tok = self._expect(TokenType.IDENTIFIER, "Expected type name")
        self._expect(TokenType.WALRUS, "Expected ':=' after type name")
        value = self._parse_expr()
        return ast.TypeDef(name=name_tok.value, value=value)

    def _parse_test_block(self) -> ast.TestBlock:
        """Parse test: name { ... } — colon already consumed."""
        name_tok = self._expect(TokenType.IDENTIFIER, "Expected test name")
        self._expect(TokenType.LBRACE, "Expected '{' after test name")
        body: list[ast.Node] = []
        while not self._at(TokenType.RBRACE, TokenType.EOF):
            body.append(self._parse_expr())
        self._expect(TokenType.RBRACE)
        return ast.TestBlock(name=name_tok.value, body=body)

    def _parse_deploy_stmt(self) -> ast.DeployStatement:
        """Parse deploy: target — colon already consumed."""
        target_tok = self._expect(TokenType.IDENTIFIER, "Expected deploy target")
        return ast.DeployStatement(target=target_tok.value)

    def _parse_self_heal(self) -> ast.SelfHealBlock:
        """Parse self:heal { ... } — 'self', ':', 'heal' already consumed."""
        self._expect(TokenType.LBRACE, "Expected '{' after self:heal")
        body: list[ast.Node] = []
        while not self._at(TokenType.RBRACE, TokenType.EOF):
            body.append(self._parse_expr())
        self._expect(TokenType.RBRACE)
        return ast.SelfHealBlock(body=body)

    def _parse_energy_decl(self) -> ast.EnergyDecl:
        """Parse energy: number unit — colon already consumed."""
        return self._parse_energy_decl_inner()

    def _parse_energy_decl_inner(self) -> ast.EnergyDecl:
        """Inner energy parser: number followed by optional unit identifier."""
        num_tok = self._expect(TokenType.NUMBER, "Expected energy amount")
        amount = float(num_tok.value)
        unit = "A"
        if self._at(TokenType.IDENTIFIER):
            unit = self._advance().value
        return ast.EnergyDecl(amount=amount, unit=unit)

    def _parse_llm_directive(self, action: str) -> ast.LLMDirective:
        """Parse llm:action(args) — 'llm', ':', and action already consumed."""
        args: list[ast.Node] = []
        if self._at(TokenType.LPAREN):
            self._advance()
            while not self._at(TokenType.RPAREN, TokenType.EOF):
                args.append(self._parse_expr())
                self._match(TokenType.COMMA)
            self._expect(TokenType.RPAREN, "Expected ')' to close LLM directive args")
        return ast.LLMDirective(action=action, args=args)

    # ------------------------------------------------------------------
    # v0.2+ parse methods
    # ------------------------------------------------------------------

    def _parse_lambda(self) -> ast.Lambda:
        """Parse lambda expression: λx y: body or \\x y: body."""
        self._advance()  # consume LAMBDA token
        params: list[str] = []
        while self._at(TokenType.IDENTIFIER):
            params.append(self._advance().value)
        self._expect(TokenType.COLON, "Expected ':' after lambda parameters")
        body = self._parse_expr()
        return ast.Lambda(params=params, body=body)

    def _parse_pi_type(self) -> ast.PiType:
        """Parse Pi type: Π(x:A) B or Pi(x:A) B."""
        self._advance()  # consume PI_TYPE token
        self._expect(TokenType.LPAREN, "Expected '(' after Π/Pi")
        var_tok = self._expect(TokenType.IDENTIFIER, "Expected variable in Pi type")
        self._expect(TokenType.COLON, "Expected ':' in Pi type binding")
        domain = self._parse_expr()
        self._expect(TokenType.RPAREN, "Expected ')' after Pi type domain")
        codomain = self._parse_expr()
        return ast.PiType(var=var_tok.value, domain=domain, codomain=codomain)

    def _parse_sigma_type(self) -> ast.SigmaType:
        """Parse Sigma type: Σ(x:A) B or Sigma(x:A) B."""
        self._advance()  # consume SIGMA_TYPE token
        self._expect(TokenType.LPAREN, "Expected '(' after Σ/Sigma")
        var_tok = self._expect(TokenType.IDENTIFIER, "Expected variable in Sigma type")
        self._expect(TokenType.COLON, "Expected ':' in Sigma type binding")
        domain = self._parse_expr()
        self._expect(TokenType.RPAREN, "Expected ')' after Sigma type domain")
        body = self._parse_expr()
        return ast.SigmaType(var=var_tok.value, domain=domain, body=body)

    def _parse_func_call(self, name: str) -> ast.FuncCall:
        self._expect(TokenType.LPAREN)
        args: list[ast.Node] = []
        while not self._at(TokenType.RPAREN, TokenType.EOF):
            args.append(self._parse_expr())
            self._match(TokenType.COMMA)
        self._expect(TokenType.RPAREN, "Expected ')' to close function call")
        return ast.FuncCall(name=name, args=args)

    def _parse_list(self) -> ast.List:
        self._expect(TokenType.LBRACKET)
        items: list[ast.Node] = []
        while not self._at(TokenType.RBRACKET, TokenType.EOF):
            items.append(self._parse_expr())
            self._match(TokenType.COMMA)
        self._expect(TokenType.RBRACKET, "Expected ']' to close list")
        return ast.List(items=items)

    def _parse_scope(self) -> ast.Scope | ast.RefinementType:
        """Parse {content} or {x:A | P(x)} refinement type."""
        self._expect(TokenType.LBRACE)

        # Try to detect refinement type: {ident : type | predicate}
        if self._at(TokenType.IDENTIFIER):
            saved = self.pos
            var_tok = self._advance()
            if self._at(TokenType.COLON):
                self._advance()
                # Parse the base type — stop at PIPE or RBRACE
                # Use min_prec=5 to avoid consuming | (PIPE, level 4) as binary op
                base_parts: list[ast.Node] = []
                while not self._at(TokenType.PIPE, TokenType.RBRACE, TokenType.EOF):
                    base_parts.append(self._parse_binary(min_prec=5))
                if self._at(TokenType.PIPE):
                    self._advance()  # consume |
                    # It's a refinement type
                    base = base_parts[0] if len(base_parts) == 1 else ast.Scope(body=base_parts)
                    pred = self._parse_expr()
                    self._expect(TokenType.RBRACE, "Expected '}' to close refinement type")
                    return ast.RefinementType(var=var_tok.value, base_type=base, predicate=pred)
                # Not a refinement — rollback and parse as normal scope
                self.pos = saved
            else:
                self.pos = saved

        body: list[ast.Node] = []
        while not self._at(TokenType.RBRACE, TokenType.EOF):
            body.append(self._parse_expr())
        self._expect(TokenType.RBRACE, "Expected '}' to close scope")
        return ast.Scope(body=body)

    def _parse_vector(self) -> ast.Vector:
        """Parse vec:[n1, n2, ...] — '[' already peeked."""
        self._expect(TokenType.LBRACKET)
        values: list[float] = []
        while not self._at(TokenType.RBRACKET, TokenType.EOF):
            tok = self._expect(TokenType.NUMBER, "Expected number in vector")
            values.append(float(tok.value))
            self._match(TokenType.COMMA)
        self._expect(TokenType.RBRACKET, "Expected ']' to close vector")
        return ast.Vector(values=values)

    def _parse_quantifier(self) -> ast.Quantifier:
        kind_tok = self._advance()  # forall / exists
        var_tok = self._expect(TokenType.IDENTIFIER, "Expected variable after quantifier")
        self._expect(TokenType.COLON, "Expected ':' after quantifier variable")
        body = self._parse_expr()
        return ast.Quantifier(kind=kind_tok.value, variable=var_tok.value, body=body)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse(source: str) -> list[ast.Node]:
    """Parse Sigil source text into a list of AST nodes."""
    tokens = tokenize(source)
    return Parser(tokens).parse()


def parse_one(source: str) -> ast.Node:
    """Parse a single Sigil message/expression."""
    tokens = tokenize(source)
    return Parser(tokens).parse_one()
