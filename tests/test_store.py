import pytest

from app.store.doc_store import DocStore


def test_save_get_roundtrip(store, claim) -> None:
    store.save("claims", claim)
    assert store.get("claims", claim.claim_id) == claim


def test_get_missing_returns_none(store) -> None:
    assert store.get("claims", "nope") is None


def test_get_returns_latest_version(store, claim) -> None:
    store.save("claims", claim)

    updated = claim.model_copy(update={"verdict": "supported"})
    store.save("claims", updated)

    fetched = store.get("claims", claim.claim_id)

    assert fetched is not None
    assert fetched.verdict == "supported"


def test_all_preserves_order(store, claim) -> None:
    store.save("claims", claim)
    store.save("claims", claim.model_copy(update={"claim_id": "c_0002"}))
    assert [c.claim_id for c in store.all("claims")] == ["c_0001", "c_0002"]


def test_query_filters(store, claim) -> None:
    store.save("claims", claim)
    store.save("claims", claim.model_copy(update={"claim_id": "c_0002", "paper_id": "p_0002"}))
    assert [c.claim_id for c in store.query("claims", paper_id="p_0001")] == ["c_0001"]


def test_unknown_entity_raises_key_error(store) -> None:
    with pytest.raises(KeyError):
        store.get("bogus", "x")


def test_save_creates_one_line_per_doc(store, tmp_path, claim) -> None:
    store.save("claims", claim)
    store.save("claims", claim.model_copy(update={"claim_id": "c_0002"}))
    lines = (tmp_path / "claims.jsonl").read_text().strip().splitlines()
    assert len(lines) == 2


def test_uses_config_default_base_dir() -> None:
    assert DocStore().base_dir.name == "out"
