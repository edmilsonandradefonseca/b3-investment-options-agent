from datetime import datetime, timezone
import sqlite3
from types import SimpleNamespace

from b3_agent.intelligence.personal_history import PersonalHistoryService

NOW = datetime(2026, 10, 1, tzinfo=timezone.utc)


def ledger(tmp_path):
    path = tmp_path / 'options.sqlite3'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE option_transactions (transaction_id TEXT, option_ticker TEXT, broker TEXT, quantity REAL, average_cost REAL, total_cost REAL, as_of TEXT, source_ref TEXT, source_type TEXT, source_id TEXT)')
    return path


def append(path, ident, symbol, qty, price, day):
    with sqlite3.connect(path) as conn:
        conn.execute('INSERT INTO option_transactions VALUES (?,?,?,?,?,?,?,?,?,?)', (ident,symbol,'BTG',qty,price,qty*price,day,'BTG:NotaCorretagem:'+ident,'BROKERAGE_NOTE',ident))


def test_real_single_row_shape_does_not_invent_outcome(tmp_path):
    path = ledger(tmp_path)
    append(path,'one','GGBRE221W2',2500,.68,'2026-05-04')
    before = path.read_bytes()
    result = PersonalHistoryService(tmp_path).build()
    assert result['execution_count'] == 1
    assert result['cash_flow_observed'] == -1700
    assert result['assignment_frequency'] is None
    assert result['learning_sample_size'] == 0
    assert result['net_flat_sequence_count'] == 0
    assert result['executions'][0]['execution_timestamp'] is None
    assert result['coverage'] == 'UNKNOWN'
    assert path.read_bytes() == before
    assert not (tmp_path/'source_manifest.sqlite3').exists()


def test_reuses_raw_reads_and_invalidates_on_append(tmp_path):
    path = ledger(tmp_path)
    append(path,'s','PETRA100',-100,2,'2026-01-02')
    service = PersonalHistoryService(tmp_path)
    first = service.build()
    second = service.build()
    assert second['telemetry']['cache'] == 'HIT'
    assert first['fingerprint'] == second['fingerprint']
    append(path,'b','PETRA100',100,1,'2026-01-10')
    third = service.build()
    assert third['fingerprint'] != first['fingerprint']
    assert third['execution_count'] == 2
    sequence = third['net_flat_sequences'][0]
    assert sequence['gross_execution_cash_flow'] == 100
    assert sequence['economic_outcome_status'] == 'UNKNOWN'
    assert not sequence['eligible_for_learning']
    assert set(sequence['source_transaction_ids']) == {'s','b'}


def test_underlying_prefix_is_unverified_not_petr4_coverage(tmp_path):
    path = ledger(tmp_path)
    append(path,'s','PETRA100',-100,2,'2026-01-02')
    service = PersonalHistoryService(tmp_path)
    result = service.build(ticker='PETR4')
    assert result['executions'][0]['identity_match'] == 'UNVERIFIED_OPTION_ROOT'
    assert service.build(ticker='VALE3')['execution_count'] == 0


def test_strict_pit_rejects_absent_or_future_availability(tmp_path):
    path = ledger(tmp_path)
    append(path,'s','PETRA100',-100,2,'2026-01-02')
    service = PersonalHistoryService(tmp_path)
    assert service.build(as_of=NOW)['execution_count'] == 0
    with sqlite3.connect(tmp_path/'source_manifest.sqlite3') as conn:
        conn.execute('CREATE TABLE source_manifest (source_id TEXT, source_type TEXT, imported_at TEXT)')
        conn.execute("INSERT INTO source_manifest VALUES ('s','BROKERAGE_NOTE','2026-10-02T00:00:00+00:00')")
    assert service.build(as_of=NOW)['execution_count'] == 0
    later = service.build(as_of=datetime(2026,10,3,tzinfo=timezone.utc))
    assert later['execution_count'] == 1
    assert later['mode'] == 'STRICT_KNOWN_AT_TIME'


def test_same_day_direction_ambiguity_does_not_fabricate_cycles(tmp_path):
    path = ledger(tmp_path)
    append(path,'s','PETRA100',-100,2,'2026-01-02')
    append(path,'b','PETRA100',100,1,'2026-01-02')
    result = PersonalHistoryService(tmp_path).build()
    assert result['net_flat_sequence_count'] == 0
    assert result['excluded']['INTRADAY_ORDER_UNKNOWN'] == 2


def test_brokers_not_netted_together(tmp_path):
    path = ledger(tmp_path)
    append(path,'s','PETRA100',-100,2,'2026-01-02')
    append(path,'b','PETRA100',100,1,'2026-01-10')
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE option_transactions SET broker='OTHER' WHERE transaction_id='b'")
    assert PersonalHistoryService(tmp_path).build()['net_flat_sequence_count'] == 0


def test_missing_database_read_does_not_create_directories(tmp_path):
    missing = tmp_path/'missing'
    result = PersonalHistoryService(missing).build()
    assert not missing.exists()
    assert result['assignment_frequency'] is None
    assert result['sources']['option_transactions']['status'] == 'MISSING'


def test_stock_history_and_cross_ledger_option_overlap(tmp_path):
    path = ledger(tmp_path)
    append(path,'s','PETRA100',-100,2,'2026-01-02')
    with sqlite3.connect(tmp_path/'b3_agent.db') as conn:
        conn.execute('CREATE TABLE transactions (transaction_id TEXT, executed_at TEXT, action TEXT, instrument_type TEXT, ticker TEXT, quantity REAL, price REAL, broker TEXT, source_ref TEXT)')
        conn.executemany('INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?)', [
            ('dup','2026-01-02T15:00:00+00:00','SELL','OPTION','PETRA100',100,2,'BTG','manual'),
            ('stock','2026-01-02T15:00:00+00:00','BUY','STOCK','PETR4',20,30,'BTG','manual'),
        ])
    result = PersonalHistoryService(tmp_path).build()
    assert result['execution_count'] == 2
    assert result['excluded']['POSSIBLE_CROSS_LEDGER_DUPLICATE'] == 1
    stock = PersonalHistoryService(tmp_path).build(ticker='PETR4')
    assert any(r['instrument_type'] == 'STOCK' for r in stock['executions'])


def test_since_filter_keeps_earlier_legs_for_sequence(tmp_path):
    path = ledger(tmp_path)
    append(path,'s','RENTP100',-100,2,'2026-01-02')
    append(path,'b','RENTP100',100,1,'2026-02-10')
    result = PersonalHistoryService(tmp_path).build(since='2026-02-01')
    assert result['execution_count'] == 1
    assert result['cash_flow_observed'] == -100
    assert result['net_flat_sequences'][0]['gross_execution_cash_flow'] == 100


def test_history_endpoint_does_not_configure_models(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from b3_agent import server
    monkeypatch.setattr(server,'settings',SimpleNamespace(data_dir=tmp_path))
    monkeypatch.setattr(server,'_configure_runtime',lambda: (_ for _ in ()).throw(AssertionError('LLM called')))
    response = TestClient(server.app).get('/history/context?ticker=PETR4')
    assert response.status_code == 200
    assert response.json()['assignment_frequency'] is None
    assert not list(tmp_path.iterdir())


def test_workflow_reads_sqlite_before_reasoning_and_keeps_risk_gate(tmp_path):
    import json
    from b3_agent.agents.reasoning import InvestmentReasoningAgent
    from b3_agent.agents.risk_validator import RiskValidator
    from b3_agent.orchestration.workflow import build_workflow
    from b3_agent.llm.reuse import ReusingLLMClient
    class Model:
        def __init__(self): self.inputs=[]
        def complete_json(self, **kwargs):
            self.inputs.append(json.loads(kwargs['input_text']))
            return dict(action='WAIT',subject_id='PETR4',thesis='Insufficient history',rationale='Unknown outcomes',evidence_refs=[],risks=['Unknown'],opportunity_cost='Unknown',capital_impact='Unknown',confidence='LOW',invalidation_conditions=['New evidence'])
    class UnexpectedSpecialist:
        def analyze(self, context): raise AssertionError('specialist should be omitted')
    path=ledger(tmp_path)
    append(path,'s','PETRA100',-100,2,'2026-01-02')
    model=Model()
    workflow=build_workflow(reasoning_agent=InvestmentReasoningAgent(ReusingLLMClient(model)),risk_validator=RiskValidator(),personal_history_service=PersonalHistoryService(tmp_path),single_synthesis=True,market_agent=UnexpectedSpecialist(),portfolio_agent=UnexpectedSpecialist(),options_agent=UnexpectedSpecialist())
    result=workflow.invoke({'user_question':'Compare PUT and CALL','ticker':'PETR4','workspace_intelligence':True})
    assert len(model.inputs)==1
    history=model.inputs[0]['deterministic_context']['personal_history']
    assert history['execution_count']==1
    assert history['assignment_frequency'] is None
    decisions=model.inputs[0]['deterministic_context']['decision_history']
    assert decisions['candidates'][0]['subject_id']=='PETR4'
    assert decisions['subjects']['PETR4']['execution_count']==0
    assert decisions['subjects']['PETR4']['match_policy']=='EXACT_SYMBOL'
    assert result['decision_history']==decisions
    assert 'risk_validation' in result
    assert result['stage_telemetry']['reason']['cache']=='MISS'
    assert 'personal_history' in result['stage_telemetry']


def test_workspace_deterministic_mode_never_calls_senior(monkeypatch):
    from datetime import datetime, timezone
    from b3_agent import server
    from b3_agent.orchestration.contracts import OrchestratorRequest, OrchestratorResponse
    class Context:
        source_refs=('sqlite:history',)
        def as_context(self): return {'deterministic_context': {'personal_history': {'coverage':'UNKNOWN'}, 'decision_history': {'ranking_effect':'NONE'}}}
    class Service:
        def build(self,**kwargs):
            assert not kwargs['include_joao']
            assert not kwargs['include_joao_perspective']
            return Context()
    monkeypatch.setattr(server,'WorkspaceIntelligenceContextService',Service)
    monkeypatch.setattr(server,'_configure_runtime',lambda: (_ for _ in ()).throw(AssertionError('senior invoked')))
    response=server._workspace_intelligence_response(OrchestratorRequest('Analyze','PETR4',{'workspace':'Strategy Lab','analysis_mode':'deterministic'}),deterministic_response=OrchestratorResponse('COMPLETED',result={'canonical_metric': 7}))
    assert response.result['canonical_metric']==7
    assert response.result['telemetry']['llm_calls']==0
    assert response.result['personal_history']['coverage']=='UNKNOWN'
    assert response.result['decision_history']['ranking_effect']=='NONE'


def test_partial_repurchase_observation_never_finalizes_outcome(tmp_path, monkeypatch):
    from b3_agent.experience.outcome_engine import OutcomeEngine
    monkeypatch.setattr(OutcomeEngine, 'finalize', lambda *a, **k: (_ for _ in ()).throw(AssertionError('OutcomeEngine called')))
    path = ledger(tmp_path)
    append(path, 'sell', 'RENTP100', -100, 2, '2026-01-02')
    append(path, 'partial', 'RENTP100', 40, 1, '2026-02-10')
    result = PersonalHistoryService(tmp_path).build(since='2026-02-01')
    sequence = result['observed_sequences'][0]
    assert sequence['observed_quantity_delta'] == -60
    assert sequence['partial_reduction_count'] == 1
    assert sequence['gross_execution_cash_flow'] == 160
    assert result['cash_flow_observed'] == -40
    assert sequence['status'] == 'OBSERVED_OUTSTANDING_DELTA'
    assert sequence['current_position_quantity'] is None
    assert sequence['realized_pnl'] is None
    assert sequence['assigned'] is None
    assert not sequence['eligible_for_learning']
    assert sequence['movements'][-1]['movement'] == 'OBSERVED_PARTIAL_REDUCTION'
    assert result['historical_admission']['unknown_outcome_count'] == 1
    assert result['historical_admission']['ranking_effect'] == 'NONE'
    append(path, 'flat', 'RENTP100', 60, 1.5, '2026-03-01')
    closed = PersonalHistoryService(tmp_path).build()['observed_sequences'][0]
    assert closed['status'] == 'OBSERVED_NET_FLAT_SEQUENCE'
    assert closed['gross_execution_cash_flow'] == 70
    assert closed['economic_outcome_status'] == 'UNKNOWN'
    assert closed['movements'][-1]['movement'] == 'OBSERVED_NET_FLAT'
    assert closed['roll_chain_result'] is None


def test_ambiguous_crossing_group_has_no_partially_admitted_sequence(tmp_path):
    path = ledger(tmp_path)
    append(path, 'sell', 'RENTP100', -100, 2, '2026-01-02')
    append(path, 'cross', 'RENTP100', 140, 1, '2026-02-10')
    result = PersonalHistoryService(tmp_path).build()
    assert result['observed_sequence_count'] == 0
    assert result['historical_admission']['eligible_outcome_count'] == 0
    assert result['excluded']['RECONSTRUCTION_AMBIGUOUS'] == 2


def test_observed_stock_movements_preserve_source_units(tmp_path):
    with sqlite3.connect(tmp_path / 'b3_agent.db') as conn:
        conn.execute('CREATE TABLE transactions (transaction_id TEXT, executed_at TEXT, action TEXT, instrument_type TEXT, ticker TEXT, quantity REAL, price REAL, broker TEXT, source_ref TEXT)')
        conn.executemany('INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?)', [
            ('buy','2026-01-02T15:00:00+00:00','BUY','STOCK','PETR4',20,30,'BTG','manual:buy'),
            ('reduce','2026-02-02T15:00:00+00:00','SELL','STOCK','PETR4',5,35,'BTG','manual:reduce'),
        ])
    result = PersonalHistoryService(tmp_path).build(ticker='PETR4')
    sequence = result['observed_sequences'][0]
    assert sequence['observed_quantity_delta'] == 15
    assert sequence['gross_execution_cash_flow'] == -425
    assert sequence['instrument_type'] == 'STOCK'
    assert sequence['partial_reduction_count'] == 1
    assert sequence['source_refs'] == ('manual:buy', 'manual:reduce')


def test_sequence_detail_is_bounded_but_totals_include_earlier_rows(tmp_path):
    path = ledger(tmp_path)
    for i in range(25):
        append(path, str(i), 'RENTP100', -1, 2, f'2026-01-{i+1:02d}')
    result = PersonalHistoryService(tmp_path).build()
    sequence = result['observed_sequences'][0]
    assert len(sequence['movements']) == len(sequence['source_transaction_ids']) == 20
    assert sequence['movement_details_omitted'] == sequence['source_transaction_details_omitted'] == 5
    assert sequence['observed_quantity_delta'] == -25
    assert sequence['gross_execution_cash_flow'] == 50
    assert sequence['movements'][0]['observed_delta_before'] == -5


def test_observed_projection_keeps_strict_availability_cutoff(tmp_path):
    path = ledger(tmp_path)
    append(path, 'sell', 'RENTP100', -100, 2, '2026-01-02')
    append(path, 'buy', 'RENTP100', 100, 1, '2026-02-10')
    with sqlite3.connect(tmp_path / 'source_manifest.sqlite3') as conn:
        conn.execute('CREATE TABLE source_manifest (source_id TEXT, source_type TEXT, imported_at TEXT)')
        conn.executemany('INSERT INTO source_manifest VALUES (?,?,?)', [
            ('sell','BROKERAGE_NOTE','2026-01-03T00:00:00+00:00'),
            ('buy','BROKERAGE_NOTE','2026-10-02T00:00:00+00:00'),
        ])
    result = PersonalHistoryService(tmp_path).build(as_of=NOW)
    assert result['observed_sequences'][0]['observed_quantity_delta'] == -100
    assert result['net_flat_sequence_count'] == 0
    assert result['excluded']['AVAILABILITY_NOT_PROVEN_AT_AS_OF'] == 1
