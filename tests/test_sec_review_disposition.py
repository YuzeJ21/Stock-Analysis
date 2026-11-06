"""Exercise the private disposition store using synthetic SEC receipts."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import hashlib
import json

import pytest

from src import sec_research_review as review
from src import sec_review_disposition as disposition
from tests.test_multi_company_sec_review import capture as capture_other_issuer
from tests.test_sec_research_review import view


def _save_receipt(root, profile, minute):
    packet = review.capture_review(view(), profile_key=profile, saved_at=f"2026-11-02T22:{minute:02d}:00Z")
    review.save_review(packet, root)
    return packet["receipt_id"]


@pytest.fixture
def pair(tmp_path):
    after = _save_receipt(tmp_path, "research", 2)
    before = _save_receipt(tmp_path, "research", 1)
    return before, after


def _decision_files(root):
    return list((root / "outputs" / "local" / "sec-review-dispositions").glob("*/*.json"))


def test_disposition_persists_and_updates_only_its_exact_pair(tmp_path, pair):
    third = _save_receipt(tmp_path, "research", 3)
    other_pair = tuple(_save_receipt(tmp_path, "../other profile", minute) for minute in (1, 2))
    assert disposition.load_disposition(tmp_path, "research", *pair) is None

    saved = disposition.save_disposition(tmp_path, "research", *pair, "reviewed", "  Filed detail <unchanged>.  ")
    assert saved["status"] == "reviewed"
    assert saved["reason"] == "Filed detail <unchanged>."
    assert datetime.fromisoformat(saved["reviewed_at"].replace("Z", "+00:00")).utcoffset() == timedelta(0)
    assert disposition.load_disposition(tmp_path, "research", *pair) == saved
    assert disposition.load_disposition(tmp_path, "research", pair[1], third) is None
    assert disposition.load_disposition(tmp_path, "../other profile", *other_pair) is None
    with pytest.raises(ValueError):
        disposition.load_disposition(tmp_path, "../other profile", *pair)

    # An identical retry keeps the original record, even if trimming is needed again.
    assert disposition.save_disposition(tmp_path, "research", *pair, "reviewed", " Filed detail <unchanged>.") == saved
    updated = disposition.save_disposition(tmp_path, "research", *pair, "still_open", "Revisit the filing.")
    assert updated["status"] == "still_open"
    assert disposition.load_disposition(tmp_path, "research", *pair) == updated
    assert len(_decision_files(tmp_path)) == 1


def test_saves_leave_receipt_hashes_and_data_paths_untouched(tmp_path, pair):
    receipts = sorted((tmp_path / "outputs" / "local" / "sec-research-reviews").rglob("*.json"))
    original_hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in receipts}
    registry = tmp_path / "config" / "source_rights.yml"
    registry.parent.mkdir()
    registry.write_text("example registry for isolation check\n")
    reason = "é" * 500
    disposition.save_disposition(tmp_path, "research", *pair, "still_open", reason)

    assert disposition.load_disposition(tmp_path, "research", *pair)["reason"] == reason
    assert sorted((tmp_path / "outputs" / "local" / "sec-research-reviews").rglob("*.json")) == receipts
    assert {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in receipts} == original_hashes
    assert registry.read_text() == "example registry for isolation check\n"
    assert not (tmp_path / "data").exists()


def test_requires_two_distinct_full_ordered_nem_ids_from_active_profile(tmp_path, pair):
    other = capture_other_issuer(profile="research")
    review.save_review(other, tmp_path)
    before, after = pair
    bad_pairs = [
        (before, before), (after, before), (before[:12], after), ("a" * 64, after),
        ("../escape", after), (other["receipt_id"], after),
    ]
    for bad_pair in bad_pairs:
        with pytest.raises(ValueError):
            disposition.save_disposition(tmp_path, "research", *bad_pair, "reviewed", "Checked.")
    assert not _decision_files(tmp_path)


def test_resolve_pair_checks_supplied_packet_scope_and_order(tmp_path, pair):
    packets = review.list_reviews(tmp_path, "research")
    assert disposition.resolve_pair(packets, *pair) == tuple(packets)
    with pytest.raises(ValueError):
        disposition.resolve_pair(packets[::-1], *pair)
    for changed_scope in (
        {"profile_key": "other"}, {"sec_cik": "0000000001"}, {"ticker": "AMD"},
        {"saved_at": "2026-11-02T22:00:00Z"}, {"saved_at": None},
    ):
        with pytest.raises(ValueError):
            disposition.resolve_pair([packets[0], {**packets[1], **changed_scope}], *pair)
    with pytest.raises(ValueError):
        disposition.resolve_pair([packets[0], {}], *pair)


@pytest.mark.parametrize(("status", "reason"), [
    ("approved", "Checked."), ("", "Checked."), ([], "Checked."),
    ("reviewed", " \n\t "), ("still_open", "x" * 501), ("reviewed", None),
    ("reviewed", "control\x00character"),
])
def test_rejects_invalid_status_or_reason_without_writing(tmp_path, pair, status, reason):
    with pytest.raises(ValueError):
        disposition.save_disposition(tmp_path, "research", *pair, status, reason)
    assert disposition.load_disposition(tmp_path, "research", *pair) is None


def test_unreadable_record_and_mismatched_scope_fail_closed(tmp_path, pair):
    disposition.save_disposition(tmp_path, "research", *pair, "reviewed", "Checked.")
    target, = _decision_files(tmp_path)
    raw = target.read_bytes()
    record = json.loads(raw)
    for bad in (
        b'{"reason":', b'{"reason":"duplicate",' + raw[1:], b"x" * 8192,
        json.dumps({**record, "profile_key": "other"}).encode(),
        json.dumps({**record, "after_id": "a" * 64}).encode(),
        json.dumps({**record, "reviewed_at": "2026-11-02T11:00:00-05:00"}).encode(),
        json.dumps({**record, "status": "still_open"}).encode(),
    ):
        target.write_bytes(bad)
        with pytest.raises(ValueError):
            disposition.load_disposition(tmp_path, "research", *pair)
        with pytest.raises(ValueError):
            disposition.save_disposition(tmp_path, "research", *pair, "still_open", "Check again.")
        assert target.read_bytes() == bad


def test_pair_must_remain_present_in_validated_receipt_store(tmp_path, pair):
    disposition.save_disposition(tmp_path, "research", *pair, "reviewed", "Checked.")
    receipt, = (tmp_path / "outputs" / "local" / "sec-research-reviews").rglob(f"{pair[0]}.json")
    receipt.unlink()
    with pytest.raises(ValueError):
        disposition.load_disposition(tmp_path, "research", *pair)


@pytest.mark.parametrize("link_directory", [True, False])
def test_refuses_symlinked_decision_storage(tmp_path, pair, link_directory):
    disposition.save_disposition(tmp_path, "research", *pair, "reviewed", "Checked.")
    target, = _decision_files(tmp_path)
    external = tmp_path / "outside"
    redirected = target.parent if link_directory else target
    redirected.rename(external)
    redirected.symlink_to(external, target_is_directory=link_directory)
    external_record = external / target.name if link_directory else external
    original = external_record.read_bytes()
    with pytest.raises((ValueError, OSError)):
        disposition.load_disposition(tmp_path, "research", *pair)
    with pytest.raises((ValueError, OSError)):
        disposition.save_disposition(tmp_path, "research", *pair, "still_open", "Should never reach outside.")
    assert external_record.read_bytes() == original


def test_failed_replace_preserves_existing_record(tmp_path, pair, monkeypatch):
    original = disposition.save_disposition(tmp_path, "research", *pair, "reviewed", "Checked.")
    target, = _decision_files(tmp_path)

    def fail_replace(*args, **kwargs):
        raise OSError("simulated replacement failure")

    monkeypatch.setattr(disposition.os, "replace", fail_replace)
    with pytest.raises(OSError):
        disposition.save_disposition(tmp_path, "research", *pair, "still_open", "Check again.")
    assert disposition.load_disposition(tmp_path, "research", *pair) == original
    assert list(target.parent.iterdir()) == [target]


def test_concurrent_saves_keep_one_valid_latest_record(tmp_path, pair):
    def save(reason):
        return disposition.save_disposition(tmp_path, "research", *pair, "reviewed", reason)

    with ThreadPoolExecutor(max_workers=4) as executor:
        identical = list(executor.map(save, ["Same decision."] * 4))
        assert all(record == identical[0] for record in identical)
        competing = list(executor.map(save, ["One", "Two", "Three", "Four"]))
    assert disposition.load_disposition(tmp_path, "research", *pair) in competing
    latest = save("Final decision.")
    assert disposition.load_disposition(tmp_path, "research", *pair) == latest
    target, = _decision_files(tmp_path)
    assert list(target.parent.iterdir()) == [target]
