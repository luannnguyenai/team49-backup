"""
test_replan_llm_quality.py
--------------------------
Test script để đánh giá chất lượng LLM extraction cho Replan.

Chạy: python test_replan_llm_quality.py
"""

import asyncio
import os
import json
from pathlib import Path

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.services.replan_llm_extractor import ReplanLLMKeywordExtractor, ReplanKeywordPlan


# Test cases: claim -> expected behavior
TEST_CASES = [
    # --- Specific claims ---
    {
        "claim": "Tôi biết Faster R-CNN và CNN feature extraction",
        "expected": {
            "primary_keywords": ["Faster R-CNN"],
            "specificity": "specific",
            "guardrail_flags": [],
        },
        "description": "Specific claim về object detection"
    },

    # --- Guardrail: skip_all ---
    {
        "claim": "Tôi biết hết rồi, skip tất cả đi",
        "expected": {
            "guardrail_flags": ["skip_all"],
        },
        "description": "Guardrail: user muốn skip toàn bộ"
    },

    {
        "claim": "I already mastered everything, just skip it all",
        "expected": {
            "guardrail_flags": ["skip_all"],
        },
        "description": "Guardrail: skip all (English)"
    },

    # --- Guardrail: too_short ---
    {
        "claim": "CNN",
        "expected": {
            "guardrail_flags": ["too_short"],
        },
        "description": "Guardrail: claim quá ngắn"
    },

    # --- Broad claim ---
    {
        "claim": "Tôi biết object detection cơ bản",
        "expected": {
            "specificity": "broad",
            "guardrail_flags": [],
        },
        "description": "Broad claim nhưng hợp lệ"
    },

    # --- Uncertain keywords ---
    {
        "claim": "Tôi biết Faster R-CNN nhưng YOLO chưa chắc",
        "expected": {
            "primary_keywords": ["Faster R-CNN"],
            "uncertain_keywords": ["YOLO"],
            "specificity": "specific",
        },
        "description": "Có uncertain keyword"
    },

    # --- Multiple topics ---
    {
        "claim": "Tôi đã biết CNN, R-CNN, và Faster R-CNN",
        "expected": {
            "primary_keywords": ["CNN", "R-CNN", "Faster R-CNN"],
            "specificity": "specific",
        },
        "description": "Multiple related topics"
    },

    # --- Vietnamese ---
    {
        "claim": "Tôi đã nắm rõ bài về Convolutional Neural Network",
        "expected": {
            "primary_keywords": ["Convolutional Neural Network", "CNN"],
            "specificity": "specific",
        },
        "description": "Vietnamese claim với thuật ngữ tiếng Anh"
    },

    # --- Do not expand ---
    {
        "claim": "Tôi biết specifically Faster R-CNN, không phải CNN thường",
        "expected": {
            "primary_keywords": ["Faster R-CNN"],
            "do_not_expand_to": ["CNN"],
            "specificity": "specific",
        },
        "description": "User muốn specific topic, không expand"
    },
]


def format_plan(plan: ReplanKeywordPlan) -> dict:
    """Format plan cho display."""
    return {
        "primary_keywords": [k.text for k in plan.primary_keywords],
        "secondary_keywords": [k.text for k in plan.secondary_keywords],
        "uncertain_keywords": [k.text for k in plan.negative_or_uncertain_keywords],
        "search_queries": plan.search_queries,
        "do_not_expand_to": plan.do_not_expand_to,
        "specificity": plan.specificity,
        "guardrail_flags": plan.guardrail_flags,
    }


def check_match(result: dict, expected: dict) -> tuple[bool, list[str]]:
    """Kiểm tra kết quả khớp expected."""
    issues = []

    for key, expected_value in expected.items():
        result_value = result.get(key)

        if key == "guardrail_flags":
            # Guardrail flags phải chứa ít nhất 1 expected flag
            if expected_value:
                if not any(flag in result_value for flag in expected_value):
                    issues.append(f"Missing guardrail flags: {expected_value}, got: {result_value}")

        elif key == "specificity":
            if result_value != expected_value:
                issues.append(f"Specificity mismatch: expected {expected_value}, got {result_value}")

        elif key == "primary_keywords":
            # Phải chứa ít nhất 1 expected keyword
            if expected_value:
                if not any(kw in result_value for kw in expected_value):
                    issues.append(f"Missing expected keywords: {expected_value}, got: {result_value}")

        elif isinstance(expected_value, list):
            # Check subset
            for item in expected_value:
                if item not in result_value:
                    issues.append(f"Missing {key}: {item}")

    return len(issues) == 0, issues


def print_result(test_case: dict, result: dict, match: bool, issues: list[str]):
    """Print kết quả test."""
    status = "✅ PASS" if match else "❌ FAIL"
    print(f"\n{status} | {test_case['description']}")
    print(f"  Claim: \"{test_case['claim']}\"")
    print(f"  Expected: {json.dumps(test_case['expected'], ensure_ascii=False)}")
    print(f"  Got: {json.dumps(result, ensure_ascii=False)}")
    if issues:
        for issue in issues:
            print(f"  ⚠️  {issue}")


async def main():
    print("=" * 70)
    print("REPLAN LLM EXTRACTION QUALITY TEST")
    print("=" * 70)
    print(f"Model: gpt-5.4-mini (thinking mode: medium)")
    print(f"Test cases: {len(TEST_CASES)}")
    print("=" * 70)

    extractor = ReplanLLMKeywordExtractor()

    results = {
        "pass": 0,
        "fail": 0,
        "details": []
    }

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/{len(TEST_CASES)}] Testing: {test_case['description']}")
        print(f"  Claim: \"{test_case['claim']}\"")

        try:
            plan = await extractor.extract(test_case['claim'])
            result = format_plan(plan)
            match, issues = check_match(result, test_case['expected'])

            print_result(test_case, result, match, issues)

            if match:
                results['pass'] += 1
            else:
                results['fail'] += 1

            results['details'].append({
                'claim': test_case['claim'],
                'description': test_case['description'],
                'expected': test_case['expected'],
                'result': result,
                'match': match,
                'issues': issues
            })

        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            results['fail'] += 1

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Pass: {results['pass']}/{len(TEST_CASES)} ({results['pass']*100//len(TEST_CASES)}%)")
    print(f"Fail: {results['fail']}/{len(TEST_CASES)} ({results['fail']*100//len(TEST_CASES)}%)")

    if results['fail'] > 0:
        print("\nFailed cases:")
        for detail in results['details']:
            if not detail['match']:
                print(f"  - {detail['description']}")
                for issue in detail['issues']:
                    print(f"    {issue}")

    # Save full results to file
    output_file = Path("test_replan_llm_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nFull results saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
