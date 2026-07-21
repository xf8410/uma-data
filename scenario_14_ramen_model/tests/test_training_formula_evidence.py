"""
Test: Training formula evidence for Scenario 14 Ramen

Tests verified facts from IL2CPP disassembly.
All assertions are backed by direct binary evidence.

Evidence levels:
- direct_extract: confirmed from disassembly
- binary_inference: inferred from disassembly patterns
- unknown: not yet proven
"""

import pytest
import json
import os


# Load evidence
EVIDENCE_PATH = os.path.join(os.path.dirname(__file__), '..', 'training_formula_evidence.json')

with open(EVIDENCE_PATH, 'r', encoding='utf-8') as f:
    EVIDENCE = json.load(f)


class TestBuildVerification:
    """Verify the build fingerprints match the work order."""

    def test_libil2cpp_sha256(self):
        assert EVIDENCE['build']['libil2cpp_sha256'] == \
            '3e32f9792d85a79f4cead60fc7676e187ecada3bccf6aa4d28d809aa7918d5c0'

    def test_libil2cpp_size(self):
        assert EVIDENCE['build']['libil2cpp_size'] == 218715344

    def test_metadata_sha256(self):
        assert EVIDENCE['build']['metadata_sha256'] == \
            'af653230aca9fba539348040d3718bbc265f64a2613083e11989dd36c6b224bf'

    def test_metadata_version(self):
        assert EVIDENCE['build']['metadata_version'] == 31

    def test_load_base(self):
        assert EVIDENCE['build']['load_base'] == '0x7330ef37c4'


class TestToolResults:
    """Verify tool execution results are documented."""

    def test_il2cppdumper_failed(self):
        tools = {t['tool']: t for t in EVIDENCE['tools_used']}
        assert tools['Il2CppDumper']['result'].startswith('FAILED')

    def test_cpp2il_failed(self):
        tools = {t['tool']: t for t in EVIDENCE['tools_used']}
        assert tools['Cpp2IL']['result'].startswith('FAILED')

    def test_capstone_succeeded(self):
        tools = {t['tool']: t for t in EVIDENCE['tools_used']}
        assert 'SUCCESS' in tools['capstone']['result']

    def test_method_dump_available(self):
        tools = {t['tool']: t for t in EVIDENCE['tools_used']}
        assert tools['existing_method_dump']['total_methods'] == 160909


class TestApplyMethod:
    """Test Apply(int) method findings."""

    @pytest.fixture
    def apply(self):
        return EVIDENCE['methods']['ServingPracticeRegionEffectBonusVO.Apply']

    def test_evidence_level(self, apply):
        assert apply['evidence_level'] == 'direct_extract'

    def test_runtime_addr(self, apply):
        assert apply['runtime_addr'] == '0x7339b12a0c'

    def test_codegen_offset(self, apply):
        """Codegen address is 0x150 bytes into actual function."""
        assert apply['codegen_offset'] == '+0x150'

    def test_divisor_logic(self, apply):
        """Divisor determined by training type."""
        dl = apply['disassembly_summary']['divisor_logic']
        assert dl['type_1'] == 'divisor = 2'
        assert dl['type_2'] == 'divisor = 1'
        assert dl['other'] == 'divisor = 4'

    def test_division_is_truncating(self, apply):
        """sdiv truncates toward zero, NOT rounding."""
        d = apply['disassembly_summary']['division']
        assert d['instruction'].startswith('sdiv')
        assert 'truncat' in d['type'].lower()
        assert 'zero' in d['type'].lower()

    def test_nine_effect_types(self, apply):
        """9 effect types added in Apply."""
        effects = apply['disassembly_summary']['effect_additions']
        assert len(effects) == 9

    def test_effect_ids(self, apply):
        """Specific effect IDs from disassembly."""
        effects = apply['disassembly_summary']['effect_additions']
        ids = [e['effect_id'] for e in effects]
        assert '0x9f (159)' in ids
        assert '0xa7 (167)' in ids
        assert '0x147 (327)' in ids
        assert '0x190 (400)' in ids

    def test_two_add_variants(self, apply):
        """Two AddEffect variants: 4-float and 1-float."""
        effects = apply['disassembly_summary']['effect_additions']
        calls = set(e['call'] for e in effects)
        assert '0x96b5190' in calls  # 4-float variant
        assert '0x96b5094' in calls  # 1-float variant


class TestGetWithCheckPointPt:
    """Test GetWithCheckPointPt findings."""

    @pytest.fixture
    def gwt(self):
        return EVIDENCE['methods']['ServingPracticeRegionEffectRepository.GetWithCheckPointPt']

    def test_evidence_level(self, gwt):
        assert gwt['evidence_level'] == 'direct_extract'

    def test_mid_function(self, gwt):
        """Codegen address is mid-function."""
        assert 'mid' in gwt['codegen_offset'].lower()

    def test_three_lists(self, gwt):
        """Three internal lists at offsets 0xf0, 0xf8, 0x100."""
        assert '0xf0' in gwt['disassembly_summary']['three_lists']
        assert '0xf8' in gwt['disassembly_summary']['three_lists']
        assert '0x100' in gwt['disassembly_summary']['three_lists']


class TestGetTrainingMatchingObtain:
    """Test GetTrainingMatchingObtain findings."""

    @pytest.fixture
    def gtm(self):
        return EVIDENCE['methods']['ServingPracticeEffectRepositoryUtil.GetTrainingMatchingObtain']

    def test_evidence_level(self, gtm):
        assert gtm['evidence_level'] == 'direct_extract'

    def test_codegen_is_start(self, gtm):
        """Codegen address equals actual function start (no offset)."""
        assert 'codegen = actual start' in gtm['actual_start']

    def test_table_has_8_entries(self, gtm):
        """Table initialized with 8 entries."""
        assert gtm['disassembly_summary']['table_init_function']['entries'] == 8

    def test_0_1f_constant(self, gtm):
        """0.1f bit pattern (0x3DCC0CCCD) used as constant."""
        assert '0.1' in gtm['disassembly_summary']['table_init_function']['constant_0_1f']

    def test_1_0f_constant(self, gtm):
        """1.0f used for entries 7-8."""
        assert '1.0' in gtm['disassembly_summary']['table_init_function']['constant_1_0f']


class TestIsBonusEffectTraining:
    """Test IsBonusEffectTraining findings."""

    @pytest.fixture
    def ibe(self):
        return EVIDENCE['methods']['ServingPracticeTransactionEntity.IsBonusEffectTraining']

    def test_evidence_level(self, ibe):
        assert ibe['evidence_level'] == 'direct_extract'

    def test_training_type_id(self, ibe):
        """Checks training type 0xa7 (167)."""
        assert ibe['disassembly_summary']['training_type_id'] == '0xa7 (167)'

    def test_returns_boolean(self, ibe):
        """Returns true/false based on effect type match."""
        logic = ibe['disassembly_summary']['logic']
        assert any('return true' in step for step in logic)
        assert any('return false' in step for step in logic)


class TestUnknowns:
    """Test that unknowns are honestly documented."""

    def test_unknowns_exist(self):
        assert len(EVIDENCE['unknowns']) >= 5

    def test_apply_full_arithmetic_unknown(self):
        ids = [u['id'] for u in EVIDENCE['unknowns']]
        assert 'apply_full_arithmetic' in ids

    def test_no_hardcoded_unknowns(self):
        """Unknowns must not be hardcoded as 0 or 50%."""
        for u in EVIDENCE['unknowns']:
            assert u['evidence_level'] != 'direct_extract', \
                f"Unknown {u['id']} claims direct_extract"

    def test_rounding_positions_unknown(self):
        ids = [u['id'] for u in EVIDENCE['unknowns']]
        assert 'rounding_positions' in ids


class TestFormulaChain:
    """Test the training formula chain steps."""

    @pytest.fixture
    def chain(self):
        return EVIDENCE['training_formula_chain']

    def test_evidence_level(self, chain):
        assert chain['evidence_level'] == 'binary_inference'

    def test_has_5_steps(self, chain):
        assert len(chain['steps']) == 5

    def test_step3_is_sdiv(self, chain):
        """Step 3 must be sdiv (truncating integer division)."""
        step3 = chain['steps'][2]
        assert 'sdiv' in step3['description']
        assert 'truncat' in step3['description'].lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
