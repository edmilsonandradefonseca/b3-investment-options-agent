from datetime import date, datetime, timedelta, timezone

import pytest

from b3_agent.orchestration.contracts import OrchestratorRequest
from b3_agent.routing.lab_option_management import compare_management, management_intent
from b3_agent.schemas.option import OptionContract, OptionQuote
from b3_agent.schemas.position import PortfolioContext, Position

AS_OF = datetime(2026, 10, 6, 14, tzinfo=timezone.utc)
OLD = OptionContract('PETRK376', 'PETR4', 'PETR4', 'PETRK376', 'CALL', 37.6,
                     date(2026, 11, 20), contract_multiplier=100)
NEW = OptionContract('PETRK400', 'PETR4', 'PETR4', 'PETRK400', 'CALL', 40,
                     date(2026, 12, 18), contract_multiplier=100)


def quote(contract, *, bid=1.5, ask=1.7, when=AS_OF):
    return OptionQuote(instrument_id=contract.option_id, ticker='PETR4',
                       observation_timestamp=when, available_timestamp=when,
                       source='oplab', ingested_at=when, source_record_id=f'OPLAB:{contract.option_id}',
                       option_id=contract.option_id, bid=bid, ask=ask, last=bid,
                       mid=(bid+ask)/2 if bid and ask else None, volume=10, open_interest=100)


def fixtures(quantity=-20, cash_known=False):
    position = Position('btg:option:PETRK376', 'PETRK376', 'OPTION', quantity,
                        strike=37.6, expiration_date=date(2026, 11, 20), option_type='CALL',
                        underlying_ticker='PETR4', source_ref='BTG:row:5')
    stock = Position('btg:stock:PETR4', 'PETR4', 'STOCK', 4500, source_ref='BTG:row:2')
    portfolio = PortfolioContext(date(2026, 10, 6), (stock, position), cash=1000 if cash_known else 0,
                                 cash_is_known=cash_known)
    return position, portfolio


def build(*, qty=5, trade_cost=25, old_quote=None, new_quote=None, new=NEW, position=None, portfolio=None):
    if position is None or portfolio is None:
        position, portfolio = fixtures()
    return compare_management(position=position, quantity_units=qty, old_contract=OLD,
                              old_quote=old_quote or quote(OLD, bid=1.8, ask=2.2),
                              new_contract=new, new_quote=new_quote or quote(NEW, bid=1.5, ask=1.7),
                              portfolio=portfolio, portfolio_revision='current-sha', as_of=AS_OF,
                              transaction_costs_brl=trade_cost)


def test_short_roll_uses_ask_to_close_bid_to_open_and_never_calls_flow_profit():
    result = build()
    keep, close, roll = result['alternatives']
    assert [x['alternative_id'] for x in result['alternatives']] == ['KEEP', 'CLOSE', 'ROLL']
    assert close['legs'][0]['price_field'] == 'ask'
    assert close['incremental_gross_cash_flow_brl'] == -1100
    assert roll['legs'][1]['price_field'] == 'bid'
    assert roll['incremental_gross_cash_flow_brl'] == -350
    assert roll['incremental_net_cash_flow_brl'] == -375
    assert roll['accumulated_realized_pnl_brl'] is None
    assert 'não é lucro' in roll['reason']
    assert keep['incremental_gross_cash_flow_brl'] == 0
    assert result['comparison']['ranking'] == 'NOT_APPLIED'
    assert result['portfolio_after_close']['cash_after_brl'] is None
    assert result['portfolio_after_close']['positions'][0]['quantity'] == 4500
    assert result['portfolio_after_close']['positions'][1]['quantity'] == -15
    assert result['portfolio_after_roll']['positions'][-1]['quantity'] == -5


def test_long_roll_sells_old_at_bid_and_buys_new_at_ask():
    position, portfolio = fixtures(quantity=20)
    result = build(position=position, portfolio=portfolio, trade_cost=0)
    close, roll = result['alternatives'][1:]
    assert close['legs'][0]['price_field'] == 'bid'
    assert close['incremental_gross_cash_flow_brl'] == 900
    assert roll['legs'][1]['price_field'] == 'ask'
    assert roll['incremental_gross_cash_flow_brl'] == 50
    assert roll['incremental_net_cash_flow_brl'] == 50
    assert result['portfolio_after_roll']['positions'][-1]['quantity'] == 5


def test_missing_executable_ask_preserves_unknown_gross_and_net():
    result = build(old_quote=quote(OLD, bid=1.8, ask=None), trade_cost=None)
    close, roll = result['alternatives'][1:]
    assert close['incremental_gross_cash_flow_brl'] is None
    assert close['incremental_net_cash_flow_brl'] is None
    assert roll['incremental_gross_cash_flow_brl'] is None
    assert roll['status'] == 'EXECUTABLE_PRICE_UNKNOWN'


@pytest.mark.parametrize('kwargs', [
    {'qty': 21}, {'qty': 0}, {'qty': 1.5}, {'qty': True},
    {'new': OptionContract('PETRK400', 'PETR4', 'PETR4', 'PETRK400', 'CALL', 40, date(2026, 11, 20), contract_multiplier=100)},
])
def test_invalid_size_or_destination_rejected(kwargs):
    with pytest.raises(ValueError):
        build(**kwargs)


def test_identity_quote_age_and_market_integrity_are_enforced():
    with pytest.raises(ValueError, match='does not match'):
        build(old_quote=quote(OLD, bid=1.8, ask=2.2).__class__(
            instrument_id='PETRK376', ticker='VALE3', observation_timestamp=AS_OF,
            available_timestamp=AS_OF, source='oplab', ingested_at=AS_OF,
            option_id='PETRK376', bid=1.8, ask=2.2, last=2, mid=2, volume=1,
            open_interest=1))
    with pytest.raises(ValueError, match='seven-day'):
        build(old_quote=quote(OLD, when=AS_OF-timedelta(days=8)))
    with pytest.raises(ValueError, match='crossed'):
        build(old_quote=quote(OLD, bid=2.3, ask=2.2))


@pytest.mark.parametrize('destination', ['PETRK400', 'PETRY400'])
def test_continuation_can_select_a_displayed_destination_without_repeating_command(destination):
    selected = {'status': 'POSITION_AND_QUANTITY_IDENTIFIED', 'option_id': 'PETRK376',
                'selected_quantity_units': 5}
    response = {'lab_position_selection': selected,
                'lab_roll_candidates': [{'option_id': destination}]}
    context = {'workspace': 'Strategy Lab', 'lab_request_kind': 'follow_up',
               'lab_conversation': [{'question': 'Compare manter, encerrar e rolar.', 'response': response}]}
    intent = management_intent(OrchestratorRequest(destination, context=context))
    assert intent == {'option_id': 'PETRK376', 'quantity_units': 5,
                      'destination_option_id': destination, 'action': 'COMPARE_KEEP_CLOSE_ROLL'}


def test_never_promotes_position_management_without_previously_identified_position():
    context = {'workspace': 'Strategy Lab', 'lab_request_kind': 'follow_up',
               'lab_conversation': [{'question': 'Quero rolar PETRK376.', 'response': {}}]}
    assert management_intent(OrchestratorRequest('PETRK400', context=context)) is None
