from datetime import datetime, timedelta, timezone
from b3_agent.historical_similarity import HistoricalSimilarityService
from b3_agent.experience.model import ExperienceEngine
from b3_agent.schemas.feature_snapshot import FeatureSnapshot, FeatureValue, FeatureDomain
from b3_agent.schemas.market_regime import MarketRegime, RegimeDimension, RegimeDimensionName
from b3_agent.schemas.operation import Operation, OperationDirection, OperationStatus
from b3_agent.schemas.outcome import Outcome, OutcomeStatus
BASE=datetime(2026,9,1,15,tzinfo=timezone.utc)
def _snap(i,day,close): return FeatureSnapshot(i,"B3-PETR4",BASE+timedelta(days=day),(FeatureValue("close",close,FeatureDomain.MARKET,BASE+timedelta(days=day)),),operation_id="OP-"+i)
def _reg(i,s): return MarketRegime(i,s.as_of,(RegimeDimension(RegimeDimensionName.TREND,"BULL"),),"regime-v1",s.snapshot_id,confidence=.8)
def _exp(i,day,close):
 s=_snap(f"FS-{i}",day,close); r=_reg(f"REG-{i}",s); op=Operation(f"OP-FS-{i}","LONG_STOCK","B3-PETR4",s.as_of,OperationStatus.CLOSED,OperationDirection.LONG,100,closed_at=s.as_of+timedelta(days=2)); out=Outcome(f"OUT-{i}",op.operation_id,op.closed_at,OutcomeStatus.FINAL,realized_pnl=100,realized_return=.02); return ExperienceEngine().assemble(operation=op,entry_snapshot=s,market_regime=r,outcome=out)
def test_uc09_returns_ranked_history_and_trace_without_vector_dependency():
 current=_snap("CURRENT",20,40); regime=_reg("REG-CURRENT",current)
 result=HistoricalSimilarityService().build(current_snapshot=current,current_regime=regime,as_of=BASE+timedelta(days=30),experiences=(_exp(1,10,39),_exp(2,12,20)),top_k=2)
 assert result.retrieval.matches[0].feature_similarity_score > result.retrieval.matches[1].feature_similarity_score
 assert result.retrieval.trace is not None
 assert result.retrieval.trace.retrieval_mode == "structured-only"
 assert result.assessment.historical_similarity is not None
