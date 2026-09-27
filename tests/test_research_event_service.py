from datetime import date, datetime, timedelta, timezone
from b3_agent.research_events import ResearchEventService
from b3_agent.schemas.news import NewsEvidence
BASE=datetime(2026,9,27,12,tzinfo=timezone.utc)
def _news(i,available): return NewsEvidence(instrument_id="B3-PETR4",ticker="PETR4",observation_timestamp=available,available_timestamp=available,source="provider",ingested_at=available,headline=f"News {i}",source_name="Provider",published_date=date(2026,9,27),event_type="CORPORATE",summary="evidence",source_record_id=i)
def test_uc10_excludes_future_information_point_in_time():
 result=ResearchEventService().build((_news("NOW",BASE-timedelta(hours=1)),_news("FUTURE",BASE+timedelta(hours=1))),as_of=BASE)
 assert [e.event_id for e in result.events]==["NOW"]
 assert result.excluded_future_count==1
 assert result.events[0].event_type=="CORPORATE"
 assert result.source_refs==("NOW",)
