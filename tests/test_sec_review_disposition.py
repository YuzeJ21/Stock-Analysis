"""Exercise the private disposition store using synthetic SEC receipts."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import hashlib
import json

import pytest

from src import sec_research_review as review
from src import sec_review_disposition as disposition
from tests.test_multi_company_sec_review import capture as capture_other_issuer, issuer_view
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


def _save_amd_receipt(root, profile, minute, *, concept=None):
    observation = issuer_view()
    if concept is not None:
        observation["approved_direct_fields"][0]["concept"] = concept
        observation["companyfacts_identity"]["payload_sha256"] = "c" * 64
    packet = review.capture_review(
        observation, profile_key=profile, saved_at=f"2026-11-02T22:{minute:02d}:00Z"
    )
    assert packet["schema_version"] == "sec-research-review-v3"
    review.save_review(packet, root)
    return packet


def test_amd_pair_saves_without_changing_existing_nem_sidecar(tmp_path, pair):
    nem = disposition.save_disposition(tmp_path, "research", *pair, "still_open", "Check NEM gap.")
    nem_file, = _decision_files(tmp_path)
    nem_bytes = nem_file.read_bytes()
    before = _save_amd_receipt(tmp_path, "research", 3)
    after = _save_amd_receipt(tmp_path, "research", 4)
    amd_ids = (before["receipt_id"], after["receipt_id"])

    assert disposition.resolve_pair(review.list_reviews(tmp_path, "research", "AMD"), *amd_ids, ticker="AMD") == (before, after)
    assert disposition.load_disposition(tmp_path, "research", *amd_ids, ticker="AMD") is None
    saved = disposition.save_disposition(
        tmp_path, "research", *amd_ids, "reviewed", "Checked both AMD receipts.", ticker="AMD"
    )
    assert saved["ticker"] == "AMD" and saved["sec_cik"] == "0000002488"
    assert disposition.load_disposition(tmp_path, "research", *amd_ids, ticker="AMD") == saved
    assert disposition.load_disposition(tmp_path, "research", *pair) == nem
    assert nem_file.read_bytes() == nem_bytes
    assert json.loads(nem_bytes)["schema_version"] == "sec-review-disposition-v1"


def test_amd_disposition_can_hold_an_incompatible_but_valid_pair(tmp_path):
    before = _save_amd_receipt(tmp_path, "research", 1)
    after = _save_amd_receipt(tmp_path, "research", 2, concept="SalesRevenueNet")
    assert review.compare_reviews(before, after)["status"] == "withheld"

    saved = disposition.save_disposition(
        tmp_path, "research", before["receipt_id"], after["receipt_id"],
        "still_open", "The revenue concepts differ.", ticker="AMD",
    )
    assert saved["status"] == "still_open"
    assert disposition.load_disposition(
        tmp_path, "research", before["receipt_id"], after["receipt_id"], ticker="AMD"
    ) == saved


@pytest.mark.parametrize("difference", ["missing_field", "different_period"])
def test_amd_review_keeps_individual_field_and_period_gaps(tmp_path, difference):
    before = _save_amd_receipt(tmp_path, "research", 1)
    observation = issuer_view()
    if difference == "missing_field":
        observation["approved_direct_fields"].pop()
    else:
        observation.update(period_end="2024-12-31", filing_date="2025-02-19",
                           accession="0000002488-25-000001")
        for row in observation["approved_direct_fields"]:
            row.update(period_start="2024-01-01", period_end="2024-12-31",
                       accession="0000002488-25-000001")
    after = review.capture_review(observation, profile_key="research", saved_at="2026-11-02T22:02:00Z")
    review.save_review(after, tmp_path)
    comparison = review.compare_reviews(before, after)
    assert comparison["gaps"]

    saved = disposition.save_disposition(
        tmp_path, "research", before["receipt_id"], after["receipt_id"],
        "still_open", "Investigate the evidence basis.", ticker="AMD",
    )
    assert saved["status"] == "still_open"


def test_duk_disposition_requires_the_parent_issuer_and_preserves_a_field_gap(tmp_path):
    parent_cik = "0001326160"
    before = capture_other_issuer("DUK", parent_cik, profile="research")
    observation = issuer_view("DUK", parent_cik)
    observation["approved_direct_fields"].pop()
    observation["companyfacts_identity"]["payload_sha256"] = "c" * 64
    after = review.capture_review(observation, profile_key="research", saved_at="2026-11-02T22:01:00Z")
    subsidiary = capture_other_issuer("DUK", "0000030371", profile="research", when="2026-11-02T22:02:00Z")
    for receipt in (before, after, subsidiary):
        review.save_review(receipt, tmp_path)

    ids = (before["receipt_id"], after["receipt_id"])
    result = review.compare_reviews(before, after)
    assert result["changes"] == []
    assert result["gaps"] == [{"field": "capital_expenditures", "reason": "direct_field_missing"}]
    saved = disposition.save_disposition(tmp_path, "research", *ids, "still_open",
                                        "Verify the parent company capex field.", ticker="DUK")
    assert saved["sec_cik"] == parent_cik
    assert disposition.load_disposition(tmp_path, "research", *ids, ticker="DUK") == saved
    assert review.compare_reviews(before, after) == result
    with pytest.raises(ValueError, match="invalid_disposition_pair_scope"):
        disposition.load_disposition(tmp_path, "research", ids[1], subsidiary["receipt_id"], ticker="DUK")


def test_amd_pair_rejects_wrong_company_missing_and_forged_receipts(tmp_path, pair):
    before = _save_amd_receipt(tmp_path, "research", 1)
    after = _save_amd_receipt(tmp_path, "research", 2)
    amd_ids = (before["receipt_id"], after["receipt_id"])
    wrong_company = capture_other_issuer("DUK", "0001326160", profile="research")
    review.save_review(wrong_company, tmp_path)
    wrong_amd_cik = capture_other_issuer("AMD", "0000009999", profile="research")
    review.save_review(wrong_amd_cik, tmp_path)

    for ticker, ids in (
        ("NEM", amd_ids), ("AMD", pair),
        ("AMD", (wrong_company["receipt_id"], after["receipt_id"])),
        ("AMD", (wrong_amd_cik["receipt_id"], after["receipt_id"])),
        ("AMD", ("a" * 64, after["receipt_id"])),
        ("AMD", amd_ids[::-1]),
        ("NVDA", amd_ids),
    ):
        with pytest.raises(ValueError):
            disposition.save_disposition(tmp_path, "research", *ids, "reviewed", "Checked.", ticker=ticker)
    with pytest.raises(ValueError):
        disposition.load_disposition(tmp_path, "other", *amd_ids, ticker="AMD")
    with pytest.raises(ValueError):
        disposition.resolve_pair([before, {**after, "sec_cik": "0000000001"}], *amd_ids, ticker="AMD")
    with pytest.raises(ValueError):
        disposition.resolve_pair([before, {**after, "form": "20-F"}], *amd_ids, ticker="AMD")


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
