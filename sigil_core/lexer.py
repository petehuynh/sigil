"""Sigil lexer — tokenizes source text into a stream of Tokens."""

from __future__ import annotations

from .tokens import Token, TokenType, KEYWORDS, UNICODE_MAP, UNICODE_DISPLAY


class LexError(Exception):
    def __init__(self, msg: str, line: int = 0, col: int = 0):
        super().__init__(f"Lex error at {line}:{col}: {msg}")
        self.line = line
        self.col = col


# Token types that end an expression (used for minus disambiguation)
_EXPR_ENDING = frozenset({
    TokenType.NUMBER, TokenType.IDENTIFIER, TokenType.RPAREN,
    TokenType.RBRACKET, TokenType.RBRACE, TokenType.STRING,
    TokenType.TOP, TokenType.BOTTOM,
})

# Simple single-character tokens
_SIMPLE: dict[str, TokenType] = {
    "[": TokenType.LBRACKET, "]": TokenType.RBRACKET,
    "{": TokenType.LBRACE,   "}": TokenType.RBRACE,
    "(": TokenType.LPAREN,   ")": TokenType.RPAREN,
    "?": TokenType.QUESTION, "!": TokenType.BANG,
    "~": TokenType.TILDE,    "@": TokenType.AT,
    "#": TokenType.HASH,     "|": TokenType.PIPE,
    "&": TokenType.AMP,      "^": TokenType.CARET,
    ",": TokenType.COMMA,
    "+": TokenType.PLUS,     "/": TokenType.SLASH,
    "%": TokenType.PERCENT,
}


class Lexer:
    """Tokenize Sigil source text."""

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self._last_type: TokenType | None = None

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _peek(self) -> str:
        if self.pos >= len(self.source):
            return ""
        return self.source[self.pos]

    def _peek_ahead(self, n: int = 1) -> str:
        idx = self.pos + n
        if idx >= len(self.source):
            return ""
        return self.source[idx]

    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _skip_whitespace(self) -> None:
        while self.pos < len(self.source) and self.source[self.pos] in " \t\n\r":
            self._advance()

    def _skip_comment(self) -> None:
        """Skip ;; line comments."""
        if self.pos < len(self.source) - 1 and self.source[self.pos:self.pos + 2] == ";;":
            while self.pos < len(self.source) and self.source[self.pos] != "\n":
                self._advance()

    def _emit(self, tokens: list[Token], tok: Token) -> None:
        """Append token and track last type for disambiguation."""
        tokens.append(tok)
        self._last_type = tok.type

    # ------------------------------------------------------------------
    # token readers
    # ------------------------------------------------------------------

    def _read_string(self, quote: str) -> Token:
        line, col = self.line, self.col
        self._advance()  # opening quote
        chars: list[str] = []
        while self.pos < len(self.source):
            ch = self._advance()
            if ch == "\\":
                nxt = self._advance() if self.pos < len(self.source) else ""
                chars.append(nxt)
            elif ch == quote:
                return Token(TokenType.STRING, "".join(chars), line, col)
            else:
                chars.append(ch)
        raise LexError("Unterminated string", line, col)

    def _read_number(self) -> Token:
        line, col = self.line, self.col
        start = self.pos
        has_dot = False
        if self._peek() == "-":
            self._advance()
        while self.pos < len(self.source):
            ch = self._peek()
            if ch == "." and not has_dot:
                # Stop if next char is also '.' (it's a .. range operator)
                if self._peek_ahead() == ".":
                    break
                has_dot = True
                self._advance()
            elif ch.isdigit():
                self._advance()
            else:
                break
        return Token(TokenType.NUMBER, self.source[start:self.pos], line, col)

    def _read_identifier(self) -> Token:
        line, col = self.line, self.col
        start = self.pos
        while self.pos < len(self.source):
            ch = self._peek()
            if ch.isalnum() or ch in "_-":
                self._advance()
            elif ch == "=" and self._peek_ahead() not in ("=", "/"):
                # Allow '=' inside identifiers (e.g., e=mc2) but not when
                # it starts '==' or '=/=' operators.
                self._advance()
            else:
                break
        text = self.source[start:self.pos]
        tt = KEYWORDS.get(text, TokenType.IDENTIFIER)
        return Token(tt, text, line, col)

    # ------------------------------------------------------------------
    # main
    # ------------------------------------------------------------------

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while self.pos < len(self.source):
            self._skip_whitespace()
            if self.pos >= len(self.source):
                break

            ch = self._peek()
            line, col = self.line, self.col

            # comments
            if ch == ";" and self._peek_ahead() == ";":
                self._skip_comment()
                continue

            # Unicode dispatch — single lookup for all Unicode symbols
            if ch in UNICODE_MAP:
                self._advance()
                tt = UNICODE_MAP[ch]
                val = UNICODE_DISPLAY.get(tt, ch)
                self._emit(tokens, Token(tt, val, line, col))
                continue

            # single-char tokens
            if ch in _SIMPLE:
                self._advance()
                self._emit(tokens, Token(_SIMPLE[ch], ch, line, col))
                continue

            # multi-char operators — order matters

            # ** before *
            if ch == "*":
                self._advance()
                if self._peek() == "*":
                    self._advance()
                    self._emit(tokens, Token(TokenType.DOUBLE_STAR, "**", line, col))
                else:
                    self._emit(tokens, Token(TokenType.STAR, "*", line, col))
                continue

            # -> (arrow)
            if ch == "-" and self._peek_ahead() == ">":
                self._advance(); self._advance()
                self._emit(tokens, Token(TokenType.ARROW, "->", line, col))
                continue

            # - (minus vs negative number)
            if ch == "-":
                if self._last_type in _EXPR_ENDING:
                    # Binary minus
                    self._advance()
                    self._emit(tokens, Token(TokenType.MINUS, "-", line, col))
                elif self._peek_ahead().isdigit():
                    # Negative number literal
                    self._emit(tokens, self._read_number())
                else:
                    # Unary minus or standalone
                    self._advance()
                    self._emit(tokens, Token(TokenType.MINUS, "-", line, col))
                continue

            # < cascade: <- , <= , <
            if ch == "<":
                self._advance()
                if self._peek() == "-":
                    self._advance()
                    self._emit(tokens, Token(TokenType.BACK_ARROW, "<-", line, col))
                elif self._peek() == "=":
                    self._advance()
                    self._emit(tokens, Token(TokenType.LTE, "<=", line, col))
                else:
                    self._emit(tokens, Token(TokenType.LT, "<", line, col))
                continue

            # > cascade: >= , >
            if ch == ">":
                self._advance()
                if self._peek() == "=":
                    self._advance()
                    self._emit(tokens, Token(TokenType.GTE, ">=", line, col))
                else:
                    self._emit(tokens, Token(TokenType.GT, ">", line, col))
                continue

            # == and =/=
            if ch == "=" and self._peek_ahead() == "=":
                self._advance(); self._advance()
                self._emit(tokens, Token(TokenType.EQUALS, "==", line, col))
                continue
            if ch == "=" and self._peek_ahead() == "/" and self.pos + 2 < len(self.source) and self.source[self.pos + 2] == "=":
                self._advance(); self._advance(); self._advance()
                self._emit(tokens, Token(TokenType.NOT_EQUALS, "=/=", line, col))
                continue

            # : cascade: := , :
            if ch == ":":
                self._advance()
                if self._peek() == "=":
                    self._advance()
                    self._emit(tokens, Token(TokenType.WALRUS, ":=", line, col))
                else:
                    self._emit(tokens, Token(TokenType.COLON, ":", line, col))
                continue

            # .. (dotdot range) — only if two dots in a row
            if ch == "." and self._peek_ahead() == ".":
                self._advance(); self._advance()
                self._emit(tokens, Token(TokenType.DOTDOT, "..", line, col))
                continue

            # \ as lambda
            if ch == "\\":
                self._advance()
                self._emit(tokens, Token(TokenType.LAMBDA, "\u03bb", line, col))
                continue

            # strings
            if ch in ('"', "'"):
                self._emit(tokens, self._read_string(ch))
                continue

            # numbers
            if ch.isdigit():
                self._emit(tokens, self._read_number())
                continue

            # identifiers / keywords
            if ch.isalpha() or ch == "_":
                self._emit(tokens, self._read_identifier())
                continue

            raise LexError(f"Unexpected character: {ch!r}", line, col)

        tokens.append(Token(TokenType.EOF, "", self.line, self.col))
        return tokens


def tokenize(source: str) -> list[Token]:
    """Convenience function to tokenize Sigil source."""
    return Lexer(source).tokenize()
