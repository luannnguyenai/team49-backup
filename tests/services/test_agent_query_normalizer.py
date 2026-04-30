from src.services.agent_query_normalizer import normalize_query


def test_normalize_query_expands_domain_synonyms():
    normalized, terms, expansions = normalize_query("ViT receptive field CNN")

    assert normalized == "vit receptive field cnn"
    assert "vision transformer" in terms
    assert "rf" in terms
    assert "convolutional neural network" in terms
    assert {expansion.from_term for expansion in expansions} >= {"vit", "cnn"}
