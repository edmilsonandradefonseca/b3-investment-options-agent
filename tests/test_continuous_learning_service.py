from datetime import datetime, timedelta, timezone
from b3_agent.continuous_learning import ContinuousLearningService
from b3_agent.experience.model import ExperienceEngine
from b3_agent.schemas.feature_snapshot import FeatureSnapshot
from b3_agent.schemas.market_regime import MarketRegime, RegimeDimension, RegimeDimensionName
from b3_agent.schemas.operation import Operation, OperationDirection, OperationStatus
from b3_agent.schemas.outcome import Outcome, OutcomeStatus

BASE=datetime(2026,1,1,15,tzinfo=timezone.utc)
def _exp(i,win=True):
    opened=BASE+timedelta(days=i*10); closed=opened+timedelta(days=5); opid=f"OP-{i}"; fsid=f"FS-{i}"
    op=Operation(opid,"LONG_STOCK","B3-PETR4",opened,OperationStatus.CLOSED,OperationDirection.LONG,100,closed_at=closed)
    fs=FeatureSnapshot(fsid,"B3-PETR4",opened,(),operation_id=opid)
    regime=MarketRegime(f"REG-{i}",opened,(RegimeDimension(RegimeDimensionName.TREND,"BULL"),),"regime-v1",fsid)
    out=Outcome(f"OUT-{i}",opid,closed,OutcomeStatus.FINAL,realized_pnl=100 if win else -100,realized_return=.02 if win else -.02)
    return ExperienceEngine().assemble(operation=op,entry_snapshot=fs,market_regime=regime,outcome=out)

def test_uc08_builds_personal_learning_without_market_generalization():
    snapshot=ContinuousLearningService().build((_exp(1),_exp(2,False),_exp(3)),as_of=BASE+timedelta(days=100))
    assert snapshot.experience_count==3
    assert len(snapshot.updates)==1
    learning=snapshot.updates[0].learning
    assert learning.sample_size==3
    assert learning.status.value=="VALIDATING"
    assert learning.learning_scope.value=="PERSONAL_EXPERIENCE"
    assert "must not be generalized" in learning.selection_bias_warning
    assert len(learning.evidence_links)==3
