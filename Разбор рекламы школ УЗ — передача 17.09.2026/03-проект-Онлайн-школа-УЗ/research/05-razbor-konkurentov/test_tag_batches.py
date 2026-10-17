"""Отбор креативов для разметки: размеченные раньше сохраняются и в новые порции не попадают.

Запуск из этой папки:  python3 -m pytest test_tag_batches.py -q -p no:cacheprovider
"""
import tag_batches as tb


def creative(cid: str, rank: str = "", days: str = "5") -> dict:
    return {"representative_id": cid, "best_top30_rank": rank, "max_days_running": days, "collation_max": "1",
            "ads": "1", "relaunches": "1"}


def test_tagged_creatives_count_toward_cap_and_are_not_rebatched():
    items = [creative("a", rank="1"), creative("b", rank="2"), creative("c", days="40"), creative("d"), creative("e")]
    already, chosen, skipped = tb.select("s", items, cap=3, tagged={"b"})
    assert [c["representative_id"] for c, _ in already] == ["b"]
    assert [c["representative_id"] for c, _ in chosen] == ["a", "c"]
    assert {c["representative_id"] for c, _ in skipped} == {"d", "e"}


def test_random_fill_is_stable_per_school():
    items = [creative(str(i)) for i in range(10)]
    first = [c["representative_id"] for c, _ in tb.select("school-x", items, cap=4, tagged=set())[1]]
    again = [c["representative_id"] for c, _ in tb.select("school-x", list(reversed(items)), cap=4, tagged=set())[1]]
    assert first == again and len(first) == 4


def test_transcript_excerpt_keeps_start_and_end():
    text = "A" * 2000 + "MIDDLE" + "Z" * 1000
    excerpt = tb.transcript_excerpt(text)
    assert excerpt.startswith("A" * 100) and excerpt.endswith("Z" * 100) and "[…]" in excerpt and "MIDDLE" not in excerpt
