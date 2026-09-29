from b3_agent.intelligence.materiality import (
    Materiality,
    classify_official_disclosure,
)


def test_fato_relevante_is_material_by_official_rule():
    decision = classify_official_disclosure(category="Fato Relevante")
    assert decision.materiality == Materiality.MATERIAL
    assert decision.reason == "OFFICIAL_FATO_RELEVANTE"


def test_comunicado_is_candidate_not_generic_keyword_filtered():
    decision = classify_official_disclosure(category="Comunicado ao Mercado")
    assert decision.materiality == Materiality.CANDIDATE
    assert decision.reason == "OFFICIAL_COMUNICADO_AO_MERCADO"


def test_official_materiality_is_accent_insensitive():
    decision = classify_official_disclosure(category="Aviso aos Acionistas")
    assert decision.materiality == Materiality.CANDIDATE
    assert decision.reason == "OFFICIAL_AVISO_AOS_ACIONISTAS"
