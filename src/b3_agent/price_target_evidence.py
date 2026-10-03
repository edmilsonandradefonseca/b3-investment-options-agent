"""Read institution targets only from explicit, qualified stored metadata."""
from datetime import date, timedelta
from urllib.parse import urlparse
from b3_agent.stock_purchase import _number, _timestamp

HOSTS={"BTG":("btgpactual.com",),"XP":("xpi.com.br",),"SAFRA":("safra.com.br",),"ITAU":("itau.com.br","itaucorretora.com.br")}


def qualify_targets(ticker, hits, cutoff):
    rows, excluded, seen = [], [], set()
    for hit in hits:
        meta = hit.metadata
        extra = meta.get("extra") or {}
        if not isinstance(extra, dict):
            excluded.append("MISSING_STRUCTURED_TARGET"); continue
        target = extra.get("price_target") or {}
        if not isinstance(target, dict):
            excluded.append("MISSING_STRUCTURED_TARGET"); continue
        institution = str(target.get("institution", "")).upper()
        price = _number(target.get("price_brl"))
        published, available = _timestamp(meta.get("published_at")), _timestamp(meta.get("retrieved_at"))
        source = meta.get("source") or ""
        url = urlparse(source)
        try:
            horizon = date.fromisoformat(str(target.get("horizon_date")))
        except ValueError:
            horizon = None
        valid_to = _timestamp(meta.get("valid_to"))
        valid_from = _timestamp(meta.get("valid_from"))
        if (meta.get("topic") != "price_target" or ticker not in meta.get("ticker_refs", [])
                or meta.get("source_quality") not in {"official", "primary"}
                or target.get("ticker") != ticker or price is None or price <= 0
                or target.get("currency") != "BRL" or institution not in HOSTS
                or url.scheme != "https" or url.username or url.password
                or not any(url.hostname == host or (url.hostname or "").endswith("."+host) for host in HOSTS.get(institution, ()))
                or not published or not available or published > cutoff or available > cutoff
                or cutoff-published > timedelta(days=180) or not horizon or horizon <= cutoff.date()
                or (meta.get("valid_to") is not None and not valid_to)
                or (meta.get("valid_from") is not None and not valid_from)
                or (valid_to and valid_to < cutoff) or (valid_from and valid_from > cutoff)
                or not meta.get("document_id")):
            excluded.append("UNQUALIFIED_TARGET_PROVENANCE_OR_TIME"); continue
        key = (institution, meta["document_id"], horizon, price)
        if key in seen: continue
        seen.add(key)
        rows.append({"institution":institution,"price_brl":price,"horizon_date":horizon,
            "published_at":published,"available_at":available,"source_url":source,"document_id":meta["document_id"]})
    # Conflicting amounts from one institution/report/horizon cannot form consensus.
    conflicts = {(r["institution"], r["document_id"], r["horizon_date"]) for r in rows if len({other["price_brl"] for other in rows if (other["institution"],other["document_id"],other["horizon_date"]) == (r["institution"],r["document_id"],r["horizon_date"])}) > 1}
    rows = [r for r in rows if (r["institution"],r["document_id"],r["horizon_date"]) not in conflicts]
    if conflicts: excluded.append("CONFLICTING_REPORT_TARGETS")
    return {"policy_version":"stored-institution-targets-v1","status":"QUALIFIED_OBSERVATIONS" if rows else "UNKNOWN_NO_ADMISSIBLE_TARGETS","rows":rows,"exclusion_reasons":excluded,"expected_return":None,"consensus":None,
        "limitations":["Broker targets are opinions with distinct report dates/horizons, not return probabilities or expected return.","Only explicitly structured primary institutional metadata is admitted; prose and semantic relevance cannot invent a target.","No aggregate consensus is inferred across differing horizons or successive reports."]}


class StoredPriceTargetService:
    def __init__(self, factory=None):
        self.factory=factory

    def build(self, ticker, cutoff):
        close=None
        try:
            from b3_agent.intelligence.stored_research import _vector_source
            from b3_agent.knowledge.vector_store import MetadataFilter
            source, close = (self.factory or _vector_source)()
            hits=source.retrieve_results(f"{ticker} preço alvo relatório BTG XP Safra Itaú",top_k=20,
                metadata_filter=MetadataFilter(ticker=ticker,topic="price_target",published_before=cutoff))
            return qualify_targets(ticker,hits,cutoff)
        except Exception as exc:
            return {**qualify_targets(ticker,[],cutoff),"status":"STORE_UNAVAILABLE","error_type":type(exc).__name__}
        finally:
            if close:
                try:
                    close()
                except Exception:
                    pass
