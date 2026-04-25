"""Tests for Sigil v1.1 — AetherCode constructs.

Covers: code:, fn:, mod:, type:, test:, deploy:, self:heal, energy:, llm:
"""

import pytest
from sigil_core import parse_one, serialize
from sigil_core import ast_nodes as ast


# ---------------------------------------------------------------------------
# code: block
# ---------------------------------------------------------------------------

class TestCodeBlock:
    def test_code_block_basic(self):
        node = parse_one('[K bot code: {x}]')
        assert isinstance(node, ast.Message)
        cb = node.content[0]
        assert isinstance(cb, ast.CodeBlock)
        assert len(cb.body) == 1
        assert isinstance(cb.body[0], ast.Identifier)
        assert cb.body[0].name == "x"

    def test_code_block_with_function(self):
        node = parse_one('[K bot code: {fn: greet(name:Str) {name}}]')
        cb = node.content[0]
        assert isinstance(cb, ast.CodeBlock)
        fn = cb.body[0]
        assert isinstance(fn, ast.FunctionDef)
        assert fn.name == "greet"

    def test_code_block_roundtrip(self):
        src = '[K bot code: {x}]'
        node = parse_one(src)
        text = serialize(node)
        node2 = parse_one(text)
        assert isinstance(node2.content[0], ast.CodeBlock)


# ---------------------------------------------------------------------------
# fn: function definition
# ---------------------------------------------------------------------------

class TestFunctionDef:
    def test_fn_simple(self):
        node = parse_one('[K bot fn: add(x:Int, y:Int) {x}]')
        fn = node.content[0]
        assert isinstance(fn, ast.FunctionDef)
        assert fn.name == "add"
        assert len(fn.params) == 2
        assert fn.params[0][0] == "x"
        assert isinstance(fn.params[0][1], ast.Identifier)
        assert fn.params[0][1].name == "Int"
        assert fn.params[1][0] == "y"

    def test_fn_with_return_type(self):
        node = parse_one('[K bot fn: square(x:Int) \u2192 Int {x}]')
        fn = node.content[0]
        assert isinstance(fn, ast.FunctionDef)
        assert fn.name == "square"
        assert fn.return_type is not None
        assert isinstance(fn.return_type, ast.Identifier)
        assert fn.return_type.name == "Int"

    def test_fn_with_arrow_return_type(self):
        node = parse_one('[K bot fn: square(x:Int) -> Int {x}]')
        fn = node.content[0]
        assert isinstance(fn, ast.FunctionDef)
        assert fn.return_type is not None

    def test_fn_no_body(self):
        node = parse_one('[K bot fn: noop(x:Int) \u2192 Int]')
        fn = node.content[0]
        assert isinstance(fn, ast.FunctionDef)
        assert fn.name == "noop"
        assert fn.body == []

    def test_fn_roundtrip(self):
        node = parse_one('[K bot fn: add(x:Int, y:Int) \u2192 Int {x}]')
        text = serialize(node)
        node2 = parse_one(text)
        fn2 = node2.content[0]
        assert isinstance(fn2, ast.FunctionDef)
        assert fn2.name == "add"
        assert len(fn2.params) == 2


# ---------------------------------------------------------------------------
# mod: module definition
# ---------------------------------------------------------------------------

class TestModuleDef:
    def test_mod_basic(self):
        node = parse_one('[K bot mod: math {x}]')
        mod = node.content[0]
        assert isinstance(mod, ast.ModuleDef)
        assert mod.name == "math"
        assert len(mod.body) == 1

    def test_mod_with_function(self):
        node = parse_one('[K bot mod: math {fn: square(x:Int) \u2192 Int {x}}]')
        mod = node.content[0]
        assert isinstance(mod, ast.ModuleDef)
        fn = mod.body[0]
        assert isinstance(fn, ast.FunctionDef)
        assert fn.name == "square"

    def test_mod_roundtrip(self):
        node = parse_one('[K bot mod: utils {x}]')
        text = serialize(node)
        node2 = parse_one(text)
        mod2 = node2.content[0]
        assert isinstance(mod2, ast.ModuleDef)
        assert mod2.name == "utils"


# ---------------------------------------------------------------------------
# type: definition
# ---------------------------------------------------------------------------

class TestTypeDef:
    def test_type_basic(self):
        node = parse_one('[K bot type: Count := Int]')
        td = node.content[0]
        assert isinstance(td, ast.TypeDef)
        assert td.name == "Count"
        assert isinstance(td.value, ast.Identifier)
        assert td.value.name == "Int"

    def test_type_roundtrip(self):
        node = parse_one('[K bot type: Count := Int]')
        text = serialize(node)
        node2 = parse_one(text)
        td2 = node2.content[0]
        assert isinstance(td2, ast.TypeDef)
        assert td2.name == "Count"


# ---------------------------------------------------------------------------
# test: block
# ---------------------------------------------------------------------------

class TestTestBlock:
    def test_test_basic(self):
        node = parse_one('[K bot test: math {x}]')
        tb = node.content[0]
        assert isinstance(tb, ast.TestBlock)
        assert tb.name == "math"
        assert len(tb.body) == 1

    def test_test_with_kv(self):
        node = parse_one('[K bot test: checks {expect:1}]')
        tb = node.content[0]
        assert isinstance(tb, ast.TestBlock)
        kv = tb.body[0]
        assert isinstance(kv, ast.KeyValue)
        assert kv.key == "expect"

    def test_test_roundtrip(self):
        node = parse_one('[K bot test: suite {x}]')
        text = serialize(node)
        node2 = parse_one(text)
        tb2 = node2.content[0]
        assert isinstance(tb2, ast.TestBlock)
        assert tb2.name == "suite"


# ---------------------------------------------------------------------------
# deploy: statement
# ---------------------------------------------------------------------------

class TestDeployStatement:
    def test_deploy_basic(self):
        node = parse_one('[C bot deploy: solana]')
        ds = node.content[0]
        assert isinstance(ds, ast.DeployStatement)
        assert ds.target == "solana"

    def test_deploy_roundtrip(self):
        node = parse_one('[C bot deploy: ethereum]')
        text = serialize(node)
        node2 = parse_one(text)
        ds2 = node2.content[0]
        assert isinstance(ds2, ast.DeployStatement)
        assert ds2.target == "ethereum"


# ---------------------------------------------------------------------------
# self:heal block
# ---------------------------------------------------------------------------

class TestSelfHealBlock:
    def test_self_heal_basic(self):
        node = parse_one('[K bot self:heal {x}]')
        sh = node.content[0]
        assert isinstance(sh, ast.SelfHealBlock)
        assert len(sh.body) == 1

    def test_self_heal_with_kv(self):
        node = parse_one('[K bot self:heal {fallback:retry}]')
        sh = node.content[0]
        assert isinstance(sh, ast.SelfHealBlock)
        assert len(sh.body) == 1
        assert isinstance(sh.body[0], ast.QualifiedName)

    def test_self_heal_roundtrip(self):
        node = parse_one('[K bot self:heal {x}]')
        text = serialize(node)
        node2 = parse_one(text)
        sh2 = node2.content[0]
        assert isinstance(sh2, ast.SelfHealBlock)


# ---------------------------------------------------------------------------
# energy: declaration
# ---------------------------------------------------------------------------

class TestEnergyDecl:
    def test_energy_with_unit(self):
        node = parse_one('[K bot energy: 0.5 A]')
        ed = node.content[0]
        assert isinstance(ed, ast.EnergyDecl)
        assert ed.amount == 0.5
        assert ed.unit == "A"

    def test_energy_kwh(self):
        node = parse_one('[K bot energy: 100 kWh]')
        ed = node.content[0]
        assert isinstance(ed, ast.EnergyDecl)
        assert ed.amount == 100.0
        assert ed.unit == "kWh"

    def test_energy_roundtrip(self):
        node = parse_one('[K bot energy: 0.5 A]')
        text = serialize(node)
        node2 = parse_one(text)
        ed2 = node2.content[0]
        assert isinstance(ed2, ast.EnergyDecl)
        assert ed2.amount == 0.5
        assert ed2.unit == "A"


# ---------------------------------------------------------------------------
# llm: directive
# ---------------------------------------------------------------------------

class TestLLMDirective:
    def test_llm_gen(self):
        node = parse_one('[C bot llm:gen]')
        ld = node.content[0]
        assert isinstance(ld, ast.LLMDirective)
        assert ld.action == "gen"
        assert ld.args == []

    def test_llm_refine_with_args(self):
        node = parse_one('[C bot llm:refine(code)]')
        ld = node.content[0]
        assert isinstance(ld, ast.LLMDirective)
        assert ld.action == "refine"
        assert len(ld.args) == 1
        assert isinstance(ld.args[0], ast.Identifier)
        assert ld.args[0].name == "code"

    def test_llm_verify(self):
        node = parse_one('[C bot llm:verify]')
        ld = node.content[0]
        assert isinstance(ld, ast.LLMDirective)
        assert ld.action == "verify"

    def test_llm_roundtrip(self):
        node = parse_one('[C bot llm:gen]')
        text = serialize(node)
        node2 = parse_one(text)
        ld2 = node2.content[0]
        assert isinstance(ld2, ast.LLMDirective)
        assert ld2.action == "gen"

    def test_llm_refine_roundtrip(self):
        node = parse_one('[C bot llm:refine(code)]')
        text = serialize(node)
        node2 = parse_one(text)
        ld2 = node2.content[0]
        assert isinstance(ld2, ast.LLMDirective)
        assert ld2.action == "refine"
        assert len(ld2.args) == 1


# ---------------------------------------------------------------------------
# Builder integration
# ---------------------------------------------------------------------------

class TestBuilder:
    def test_builder_function_def(self):
        from sigil_core import msg
        m = (msg("K", "bot")
             .function_def("add",
                           [("x", ast.Identifier(name="Int")),
                            ("y", ast.Identifier(name="Int"))],
                           return_type=ast.Identifier(name="Int"))
             .build())
        fn = m.content[0]
        assert isinstance(fn, ast.FunctionDef)
        assert fn.name == "add"

    def test_builder_deploy(self):
        from sigil_core import msg
        m = msg("C", "bot").deploy("solana").build()
        assert isinstance(m.content[0], ast.DeployStatement)

    def test_builder_energy(self):
        from sigil_core import msg
        m = msg("K", "bot").energy(0.5, "A").build()
        ed = m.content[0]
        assert isinstance(ed, ast.EnergyDecl)
        assert ed.amount == 0.5

    def test_builder_llm(self):
        from sigil_core import msg
        m = msg("C", "bot").llm("gen").build()
        ld = m.content[0]
        assert isinstance(ld, ast.LLMDirective)
        assert ld.action == "gen"


# ---------------------------------------------------------------------------
# Composite / integration
# ---------------------------------------------------------------------------

class TestComposite:
    def test_fn_inside_mod(self):
        src = '[K bot mod: math {fn: square(x:Int) \u2192 Int {x}}]'
        node = parse_one(src)
        mod = node.content[0]
        assert isinstance(mod, ast.ModuleDef)
        fn = mod.body[0]
        assert isinstance(fn, ast.FunctionDef)
        assert fn.name == "square"

    def test_multiple_constructs(self):
        src = '[K bot fn: add(x:Int) {x} deploy: solana]'
        node = parse_one(src)
        assert isinstance(node.content[0], ast.FunctionDef)
        assert isinstance(node.content[1], ast.DeployStatement)

    def test_code_block_with_nested(self):
        src = '[K bot code: {fn: greet(name:Str) {name} energy: 0.5 A}]'
        node = parse_one(src)
        cb = node.content[0]
        assert isinstance(cb, ast.CodeBlock)
        assert isinstance(cb.body[0], ast.FunctionDef)
        assert isinstance(cb.body[1], ast.EnergyDecl)
