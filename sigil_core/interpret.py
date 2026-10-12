"""Sigil ⇄ natural-language interpreter — the human↔agent hinge.

Sigil is the agents' language (compact, precise). Humans read/write their own
language. This module bridges the two at the "room" boundary:

* ``to_locale(node, locale)`` renders a Sigil message into a human sentence,
  template-based for the coordination speech-acts (deterministic, zero-LLM-cost).
* ``build_allocation(...)`` constructs the canonical Sigil for an integrator
  allocation (the ``P``ropose act).
* ``from_locale(text, ...)`` carries a human's free text back to the agents as a
  Sigil ``K`` (knowledge) message. Structured NL→Sigil for arbitrary prose is an
  LLM-assisted enhancement (see ``NL_ENCODER`` hook) — the deterministic path
  here covers the fixed coordination acts, which is what the room needs first.

CHARACTER IS NOT HARDCODED HERE. The renderer is a **neutral, natural-language
baseline** — it makes a message fluent, nothing more. An agent's tone/voice is
its own (ElizaOS character: bio, adjectives, style, system), applied when the
agent GENERATES its content; that content rides through as free-text/note fields
and is carried verbatim. Never bake a personality (warm, terse, formal) into
these templates — that belongs to the character, not the bridge.

Coordination profile (the convention layered on Sigil's generic Message):

    allocation  ->  P  @integrator @agent {task:… title:… step:… why:… prob:…}
    acknowledge ->  A  @agent @integrator {ack:… }        (accept)
    negotiate   ->  N  @agent @integrator {counter:… }
    report      ->  K  @agent @integrator {done:… note:… }
    status      -> upd @agent @integrator {status:… }
    error       ->  E  @agent @integrator {error:… }
"""

from __future__ import annotations

from . import ast_nodes as ast
from .builder import msg

# ── Coordination speech-acts ─────────────────────────────────────
# msg_type -> localized verb phrase (subject VERB receiver: body).
# English is complete; the other platform locales carry the verb + the
# "confidence" word so the coordination scaffold is legible in-language while
# domain refs (task ids, agent names, steps) stay as proper nouns.

_VERBS: dict[str, dict[str, str]] = {
    "P":   {"en": "proposes to", "my": "အား အဆိုပြုသည်", "tl": "nagmumungkahi kay",
            "vi": "đề xuất với", "zh": "向…提议"},
    "C":   {"en": "directs", "my": "ညွှန်ကြားသည်", "tl": "inuutusan si",
            "vi": "chỉ thị cho", "zh": "指示"},
    "N":   {"en": "negotiates with", "my": "နှင့် ညှိနှိုင်းသည်", "tl": "nakikipag-usap kay",
            "vi": "thương lượng với", "zh": "与…协商"},
    "A":   {"en": "confirms to", "my": "အား အတည်ပြုသည်", "tl": "kinukumpirma kay",
            "vi": "xác nhận với", "zh": "向…确认"},
    "K":   {"en": "reports to", "my": "အား အစီရင်ခံသည်", "tl": "nag-uulat kay",
            "vi": "báo cáo cho", "zh": "向…汇报"},
    "E":   {"en": "reports an error to", "my": "အား အမှားတင်ပြသည်",
            "tl": "nag-uulat ng error kay", "vi": "báo lỗi cho", "zh": "向…报告错误"},
    "upd": {"en": "updates", "my": "အား အဆင့်မြှင့်သည်", "tl": "ina-update si",
            "vi": "cập nhật cho", "zh": "更新"},
    "inf": {"en": "infers to", "my": "အား ကောက်ချက်ချသည်", "tl": "naghihinuha kay",
            "vi": "suy luận cho", "zh": "向…推断"},
    "Q":   {"en": "asks", "my": "အား မေးသည်", "tl": "nagtatanong kay",
            "vi": "hỏi", "zh": "询问"},
}

_CONFIDENCE_WORD = {"en": "confidence", "my": "ယုံကြည်မှု", "tl": "kumpiyansa",
                    "vi": "độ tin cậy", "zh": "置信度"}

def _loc(table: dict[str, dict[str, str]], key: str, locale: str) -> str:
    entry = table.get(key, {})
    return entry.get(locale) or entry.get("en") or key


def _pretty(seg: str) -> str:
    seg = seg.replace("-", " ").replace("_", " ").strip()
    return (seg[:1].upper() + seg[1:]) if seg else seg


def _display(node: ast.Node | None, names: dict[str, str] | None) -> str:
    """Friendly name for a sender/receiver. ``names`` maps id → display name
    (the app passes the agent registry); otherwise the ref is prettified."""
    if node is None:
        return ""
    full = str(node) if isinstance(node, ast.QualifiedName) else getattr(node, "name", str(node))
    last = node.name if isinstance(node, (ast.QualifiedName, ast.Identifier)) else str(node)
    if names:
        if full in names:
            return names[full]
        if last in names:
            return names[last]
    return _pretty(last)


def _scalar(node: ast.Node) -> str:
    if isinstance(node, ast.StringLiteral):
        return node.value
    if isinstance(node, ast.Identifier):
        return node.name
    if isinstance(node, ast.NumberLiteral):
        v = node.value
        return str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)
    if isinstance(node, ast.EntityRef):
        return "@" + str(node.qualified)
    return ""


# Which content key carries the *payload* of each speech-act — i.e. the thing a
# reader actually wants to read. The English renderer reaches for these inline
# per branch; `_to_other` needs the same map so a translated sentence carries the
# same content rather than an empty colon. Order is priority order.
_SUBJECT_KEYS: dict[str, tuple[str, ...]] = {
    "P":   ("title", "task", "assign"),
    "C":   ("title", "task", "assign"),
    "N":   ("counter",),
    "A":   ("ack",),
    "K":   ("done", "note"),
    "upd": ("status",),
    "E":   ("error",),
    "Q":   ("ask",),
}


def _content_subject(msg_type: str, kv: dict[str, str], frees: list[str]) -> str:
    """The message's payload as a display string.

    Strictly a SELECTION over what the message already contains — the keys the
    English branch for this act reads, then the generic title/task/assign, then
    free strings, then any remaining key/value pairs. It can surface nothing the
    Sigil does not carry; it exists so a non-English rendering is not reduced to
    "<sender> reports to <receiver>:" with the content silently dropped.
    """
    for key in _SUBJECT_KEYS.get(msg_type, ()) + ("title", "task", "assign"):
        if kv.get(key):
            return kv[key]
    if frees:
        return " ".join(frees)
    return ", ".join(f"{k} {v}" for k, v in kv.items() if v)


def _fields(content: list[ast.Node]) -> tuple[dict[str, str], list[str], float | None]:
    """Split message content into {known keys}, [free strings], confidence."""
    kv: dict[str, str] = {}
    frees: list[str] = []
    prob: float | None = None
    for n in content:
        if isinstance(n, ast.KeyValue):
            kv[n.key] = _scalar(n.value)
        elif isinstance(n, ast.Probability):
            if n.confidence is not None and n.confidence >= 0:
                prob = n.confidence
        elif isinstance(n, ast.StringLiteral):
            frees.append(n.value)
        elif isinstance(n, ast.Scope):
            k2, f2, p2 = _fields(n.body)
            kv.update(k2)
            frees.extend(f2)
            prob = p2 if p2 is not None else prob
        else:
            s = _scalar(n)
            if s:
                frees.append(s)
    return kv, frees, prob


def to_locale(node: ast.Node, locale: str = "en",
              names: dict[str, str] | None = None) -> str:
    """Render a Sigil message as a natural human sentence.

    ``locale``: en/my/tl/vi/zh. ``names``: optional id→display-name map so the
    room shows "Greyhound" / "Oxley Agent" rather than raw refs.
    """
    if not isinstance(node, ast.Message):
        _, frees, _ = _fields([node])
        return " ".join(frees)
    return (_to_english if locale == "en" else _to_other)(node, locale, names)


def _to_english(m: ast.Message, locale: str, names: dict[str, str] | None) -> str:
    s = _display(m.sender, names)
    r = _display(m.receiver, names)
    kv, frees, prob = _fields(m.content)
    conf = f" ({int(round(prob * 100))}% confident)" if prob is not None else ""
    subject = kv.get("title") or kv.get("task") or kv.get("assign") or (frees[0] if frees else "")
    subj_q = f"“{subject}”" if subject else ""
    t = m.msg_type

    if t == "P":  # propose / allocate
        line = f"{s} suggests {r} take {subj_q}" if r else f"{s} suggests taking {subj_q}"
        if kv.get("step"):
            line += f" at the {kv['step']} step"
        if kv.get("why"):
            line += f", since {kv['why']}"
        return line.rstrip() + conf + "."
    if t == "C":  # command
        return (f"{s} asks {r} to handle {subj_q}." if subject else f"{s} sends {r} a command.")
    if t == "N":  # negotiate
        body = kv.get("counter") or " ".join(frees) or "the terms"
        return f"{s} pushes back to {r}: {body}."
    if t == "A":  # accept / confirm
        ack = kv.get("ack")
        if ack and ack.lower() in ("ok", "yes", "true", "1"):
            return f"{s} accepts."
        body = ack or " ".join(frees)
        return f"{s} confirms" + (f" to {r}" if r else "") + (f": {body}" if body else "") + "."
    if t == "K":  # report / knowledge
        if kv.get("done"):
            return f"{s} reports back to {r}: finished {kv['done']}."
        body = kv.get("note") or " ".join(frees)
        if not r:
            return f"{s}: {body}".rstrip(": ")
        return f"{s} to {r}: {body}." if body else f"{s} reports back to {r}."
    if t == "upd":  # status update
        st = kv.get("status") or " ".join(frees)
        return f"{s} is now {st}." if st else f"{s} posts an update."
    if t == "E":  # error
        err = kv.get("error") or " ".join(frees) or "an unspecified error"
        return f"{s} ran into a problem: {err}."
    if t == "Q":  # query
        body = kv.get("ask") or " ".join(frees)
        return f"{s} asks" + (f" {r}" if r else "") + (f": {body}" if body else "") + "."
    # inf / anything else — neutral but readable
    body = " ".join(frees) or ", ".join(f"{k} {v}" for k, v in kv.items())
    return (f"{s} → {r}: {body}" if r else f"{s}: {body}").strip()


def _to_other(m: ast.Message, locale: str, names: dict[str, str] | None) -> str:
    """Non-English: localized speech-act verb + subject + confidence. Domain refs
    stay verbatim (proper nouns). Native-speaker phrasing is a follow-up."""
    s = _display(m.sender, names)
    r = _display(m.receiver, names)
    kv, frees, prob = _fields(m.content)
    verb = _loc(_VERBS, m.msg_type, locale)
    subject = _content_subject(m.msg_type, kv, frees)
    if prob is not None:
        word = _CONFIDENCE_WORD.get(locale, _CONFIDENCE_WORD["en"])
        conf = f" ({word} {int(round(prob * 100))}%)"
    else:
        conf = ""
    head = f"{s} {verb} {r}".strip()
    return (f"{head}: {subject}{conf}").strip()


# ── Structured constructors (the deterministic human/integrator → Sigil path) ──

def build_allocation(*, sender: str, receiver: str, task_ref: str,
                     task_title: str | None = None, step: str | None = None,
                     rationale: str | None = None,
                     confidence: float | None = None) -> ast.Message:
    """Build the canonical Sigil for an integrator allocation (a ``P`` act)."""
    b = msg("P", sender, receiver)
    b.kv("task", ast.StringLiteral(value=task_ref))
    if task_title:
        b.kv("title", ast.StringLiteral(value=task_title))
    if step:
        b.kv("step", ast.StringLiteral(value=step))
    if rationale:
        b.kv("why", ast.StringLiteral(value=rationale))
    if confidence is not None:
        b.prob(confidence)
    return b.build()


# Optional hook: a callable(text, context) -> ast.Message for LLM-assisted
# structured encoding of free-form human prose. Left None by default; the
# deterministic carry below is used when it is not set.
NL_ENCODER = None


def from_locale(text: str, *, sender: str, receiver: str) -> ast.Message:
    """Carry a human's free text to the agents as a Sigil ``K`` message.

    If ``NL_ENCODER`` is installed, defer to it for structured encoding;
    otherwise wrap the raw text as knowledge content (the agent still receives
    it, un-lossy). Structured NL→coordination-act parsing is the LLM enhancement.
    """
    if NL_ENCODER is not None:
        return NL_ENCODER(text, sender=sender, receiver=receiver)
    return msg("K", sender, receiver).string(text).build()
