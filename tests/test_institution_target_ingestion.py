from datetime import datetime,timezone
import pytest
from b3_agent.institution_target_ingestion import xp_report_evidence
URL='https://conteudos.xpi.com.br/acoes/relatorios/fixture/'
NOW=datetime(2026,10,3,tzinfo=timezone.utc)

def page(text='ITUB4 preço-alvo para R$50/ação ao final de 2027.',title='Itaú (ITUB4)',date='2026-08-06T23:18:02+00:00'):
    return f'<meta property="article:modified_time" content="{date}"><h1>{title}</h1><div class="article-content"><p>{text}</p></div><p>BBDC4 preço-alvo para R$999/ação ao final de 2027.</p>'

def test_extracts_only_explicit_single_equity_primary_report_and_dates_version():
    result=xp_report_evidence(URL,page(),NOW)
    assert result.metadata.extra['price_target']['price_brl']==50
    assert result.metadata.extra['price_target']['horizon_date']=='2027-12-31'
    assert result.metadata.published_at.hour==23
    assert result.metadata.extra['source_content_sha256']
    assert '999' not in result.content

@pytest.mark.parametrize('html',[page(text='ITUB4 preço-alvo R$50'),page(title='ITUB4 BBDC4'),page(date='2026-11-01T00:00:00+00:00'),page(date='2026-08-01'),page(text='BBDC4 preço-alvo para R$50/ação ao final de 2027.'),page(text='ITUB4 preço-alvo para R$50/ação ao final de 2027. ITUB4 preço-alvo para R$51/ação ao final de 2027.')])
def test_incomplete_foreign_conflicting_future_and_naive_report_rejected(html):
    with pytest.raises(ValueError): xp_report_evidence(URL,html,NOW)

def test_spoof_and_aggregate_page_rejected():
    for url in ['https://conteudos.xpi.com.br.evil.example/acoes/relatorios/fixture/','https://conteudos.xpi.com.br/acoes/itub4/']:
        with pytest.raises(ValueError): xp_report_evidence(url,page(),NOW)
