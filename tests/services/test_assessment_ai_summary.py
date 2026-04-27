from src.services.assessment_service import _parse_assessment_ai_summary


def test_parse_assessment_ai_summary_accepts_json_payload():
    response = _parse_assessment_ai_summary(
        """
        {
          "summary": "Bạn đang vững phần CNN cơ bản, nhưng còn hổng ở activation.",
          "highlights": ["Bỏ qua phần đã đạt 100%", "Ôn lại phần sai 0/1"],
          "next_step": "Bắt đầu bằng phần activation trước."
        }
        """
    )

    assert response.available is True
    assert response.summary == "Bạn đang vững phần CNN cơ bản, nhưng còn hổng ở activation."
    assert response.highlights == ["Bỏ qua phần đã đạt 100%", "Ôn lại phần sai 0/1"]
    assert response.next_step == "Bắt đầu bằng phần activation trước."


def test_parse_assessment_ai_summary_returns_unavailable_without_summary():
    response = _parse_assessment_ai_summary('{"highlights": ["ok"]}')

    assert response.available is False
    assert response.summary is None
