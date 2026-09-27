from datetime import datetime, timezone
from b3_agent.historical_operations import HistoricalOperationsService
from b3_agent.schemas.transaction import Transaction

def _tx(i,day,action,qty,price):
    return Transaction(i,datetime(2026,9,day,15,tzinfo=timezone.utc),action,"STOCK","PETR4",qty,price,"BTG",f"btg:{i}")

def test_uc07_reconstructs_closed_and_open_operations_and_outcomes():
    rows=(_tx("T1",1,"BUY",100,30),_tx("T2",10,"SELL",100,32),_tx("T3",20,"BUY",50,34))
    snapshot=HistoricalOperationsService().build(rows)
    assert len(snapshot.operations)==2
    assert len(snapshot.closed_operations)==1
    assert len(snapshot.open_operations)==1
    assert len(snapshot.outcomes)==1
    assert snapshot.outcomes[0].realized_pnl == 200
    assert snapshot.closed_operations[0].source_transaction_ids == ("T1","T2")
    assert snapshot.open_operations[0].source_transaction_ids == ("T3",)
