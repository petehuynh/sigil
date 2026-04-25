"""Sigil token types and Token class."""

from __future__ import annotations

from enum import Enum, auto
from dataclasses import dataclass


class TokenType(Enum):
    # Delimiters
    LBRACKET = auto()    # [
    RBRACKET = auto()    # ]
    LBRACE = auto()      # {
    RBRACE = auto()      # }
    LPAREN = auto()      # (
    RPAREN = auto()      # )

    # Operators (v0.1)
    ARROW = auto()       # ->
    BACK_ARROW = auto()  # <-
    EQUALS = auto()      # ==
    NOT_EQUALS = auto()  # =/=
    QUESTION = auto()    # ?
    BANG = auto()        # !
    TILDE = auto()       # ~
    AT = auto()          # @
    HASH = auto()        # #
    PIPE = auto()        # |
    AMP = auto()         # &
    CARET = auto()       # ^
    COLON = auto()       # :
    COMMA = auto()       # ,

    # Quantifiers / logic (v0.1)
    FORALL = auto()      # forall / ∀
    EXISTS = auto()      # exists / ∃

    # v0.2 Math operators
    PLUS = auto()        # +
    MINUS = auto()       # -
    STAR = auto()        # *
    SLASH = auto()       # /
    PERCENT = auto()     # %
    DOUBLE_STAR = auto() # **

    # v0.2 Comparison
    LT = auto()          # <
    GT = auto()          # >
    LTE = auto()         # <=
    GTE = auto()         # >=
    APPROX = auto()      # ≈

    # v0.2 Logic symbols
    AND_SYM = auto()     # ∧
    OR_SYM = auto()      # ∨
    NOT_SYM = auto()     # ¬
    IMPLIES = auto()     # → (U+2192)
    IFF = auto()         # ↔
    XOR = auto()         # ⊕

    # v0.2 Set / proof
    PROVES = auto()      # ⊢
    EQUIV = auto()       # ≡
    NOT_EQUIV = auto()   # ≢
    ELEMENT_OF = auto()  # ∈
    SUBSET = auto()      # ⊆
    PROPER_SUBSET = auto()  # ⊂

    # v0.2 Constants
    TOP = auto()         # ⊤
    BOTTOM = auto()      # ⊥

    # v0.2 Math prefix
    SUM = auto()         # ∑
    PRODUCT_SYM = auto() # ∏
    INTEGRAL = auto()    # ∫
    PARTIAL = auto()     # ∂
    NABLA = auto()       # ∇
    DELTA = auto()       # Δ

    # v0.2 Other
    LAMBDA = auto()      # λ / \
    WALRUS = auto()      # :=
    DOTDOT = auto()      # ..
    MUCH_LESS = auto()   # ≪
    MUCH_GREATER = auto()  # ≫

    # v0.3 Category theory
    LONG_ARROW = auto()    # ⟶
    DOUBLE_ARROW = auto()  # ⇒
    ADJOINT = auto()       # ⊣
    ISO = auto()           # ≅
    COMPOSE = auto()       # ∘

    # v0.3 Type theory
    PI_TYPE = auto()       # Π
    SIGMA_TYPE = auto()    # Σ
    EQUIV_TYPE = auto()    # ≃

    # v0.5 Probabilistic / HoTT
    PROPORTIONAL = auto()  # ∝

    # Literals
    NUMBER = auto()
    STRING = auto()
    IDENTIFIER = auto()

    # End
    EOF = auto()


# Unicode character → TokenType lookup (consolidated)
UNICODE_MAP: dict[str, TokenType] = {
    "\u2200": TokenType.FORALL,         # ∀
    "\u2203": TokenType.EXISTS,         # ∃
    "\u2248": TokenType.APPROX,         # ≈
    "\u2227": TokenType.AND_SYM,        # ∧
    "\u2228": TokenType.OR_SYM,         # ∨
    "\u00ac": TokenType.NOT_SYM,        # ¬
    "\u2192": TokenType.IMPLIES,        # →
    "\u2194": TokenType.IFF,            # ↔
    "\u2295": TokenType.XOR,            # ⊕
    "\u22a2": TokenType.PROVES,         # ⊢
    "\u2261": TokenType.EQUIV,          # ≡
    "\u2262": TokenType.NOT_EQUIV,      # ≢
    "\u2208": TokenType.ELEMENT_OF,     # ∈
    "\u2286": TokenType.SUBSET,         # ⊆
    "\u2282": TokenType.PROPER_SUBSET,  # ⊂
    "\u22a4": TokenType.TOP,            # ⊤
    "\u22a5": TokenType.BOTTOM,         # ⊥
    "\u2211": TokenType.SUM,            # ∑
    "\u220f": TokenType.PRODUCT_SYM,    # ∏
    "\u222b": TokenType.INTEGRAL,       # ∫
    "\u2202": TokenType.PARTIAL,        # ∂
    "\u2207": TokenType.NABLA,          # ∇
    "\u0394": TokenType.DELTA,          # Δ
    "\u03bb": TokenType.LAMBDA,         # λ
    "\u226a": TokenType.MUCH_LESS,      # ≪
    "\u226b": TokenType.MUCH_GREATER,   # ≫
    "\u27f6": TokenType.LONG_ARROW,     # ⟶
    "\u21d2": TokenType.DOUBLE_ARROW,   # ⇒
    "\u22a3": TokenType.ADJOINT,        # ⊣
    "\u2245": TokenType.ISO,            # ≅
    "\u2218": TokenType.COMPOSE,        # ∘
    "\u03a0": TokenType.PI_TYPE,        # Π
    "\u03a3": TokenType.SIGMA_TYPE,     # Σ
    "\u2243": TokenType.EQUIV_TYPE,     # ≃
    "\u221d": TokenType.PROPORTIONAL,   # ∝
}

# Canonical display values for Unicode tokens
UNICODE_DISPLAY: dict[TokenType, str] = {
    TokenType.FORALL: "forall",
    TokenType.EXISTS: "exists",
    TokenType.APPROX: "\u2248",
    TokenType.AND_SYM: "\u2227",
    TokenType.OR_SYM: "\u2228",
    TokenType.NOT_SYM: "\u00ac",
    TokenType.IMPLIES: "\u2192",
    TokenType.IFF: "\u2194",
    TokenType.XOR: "\u2295",
    TokenType.PROVES: "\u22a2",
    TokenType.EQUIV: "\u2261",
    TokenType.NOT_EQUIV: "\u2262",
    TokenType.ELEMENT_OF: "\u2208",
    TokenType.SUBSET: "\u2286",
    TokenType.PROPER_SUBSET: "\u2282",
    TokenType.TOP: "\u22a4",
    TokenType.BOTTOM: "\u22a5",
    TokenType.SUM: "\u2211",
    TokenType.PRODUCT_SYM: "\u220f",
    TokenType.INTEGRAL: "\u222b",
    TokenType.PARTIAL: "\u2202",
    TokenType.NABLA: "\u2207",
    TokenType.DELTA: "\u0394",
    TokenType.LAMBDA: "\u03bb",
    TokenType.MUCH_LESS: "\u226a",
    TokenType.MUCH_GREATER: "\u226b",
    TokenType.LONG_ARROW: "\u27f6",
    TokenType.DOUBLE_ARROW: "\u21d2",
    TokenType.ADJOINT: "\u22a3",
    TokenType.ISO: "\u2245",
    TokenType.COMPOSE: "\u2218",
    TokenType.PI_TYPE: "\u03a0",
    TokenType.SIGMA_TYPE: "\u03a3",
    TokenType.EQUIV_TYPE: "\u2243",
    TokenType.PROPORTIONAL: "\u221d",
}


# Keywords that map to specific token types
KEYWORDS: dict[str, TokenType] = {
    "forall": TokenType.FORALL,
    "exists": TokenType.EXISTS,
    "Pi": TokenType.PI_TYPE,
    "Sigma": TokenType.SIGMA_TYPE,
}


@dataclass(frozen=True, slots=True)
class Token:
    type: TokenType
    value: str
    line: int = 0
    col: int = 0

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r})"
