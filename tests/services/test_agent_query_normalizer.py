from src.services.agent_query_normalizer import normalize_query


def test_normalize_query_does_not_expand_domain_synonyms_in_code():
    normalized, terms, expansions = normalize_query("ViT receptive field CNN")

    assert normalized == "vit receptive field cnn"
    assert "vit" in terms
    assert "cnn" in terms
    assert "vision transformer" not in terms
    assert "convolutional neural network" not in terms
    assert expansions == []


def test_normalize_query_adds_generic_compacted_punctuation_variant():
    _normalized, terms, expansions = normalize_query("U-Net")

    assert "unet" in terms
    assert "net" not in terms
    assert expansions == []
