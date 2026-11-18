import json

import pytest

from ssz_z import PRESETS, SSZError, get_type
from ssz_z.beacon_api import load_proposal_json, load_proposal_ssz


@pytest.mark.parametrize("preset", PRESETS)
@pytest.mark.parametrize("fork", ["electra", "fulu"])
@pytest.mark.parametrize("blinded", [False, True])
def test_metadata_selects_proposal_codec(fork, preset, blinded):
    name = "BlindedBeaconBlock" if blinded else "BeaconBlockContents"
    codec = get_type(name, fork=fork, preset=preset)
    value = codec.default()
    metadata = {
        "version": fork,
        "execution_payload_blinded": blinded,
        "execution_payload_value": "12",
        "consensus_block_value": "34",
        "extra": {"nested": ["é"]},
    }
    # Metadata after data and non-ASCII text exercise native byte ranges.
    text = json.dumps(
        {"extra": metadata["extra"], "data": codec.to_json(value), **metadata}, ensure_ascii=False
    )
    response = load_proposal_json(text, preset=preset)
    assert response.value.codec == codec
    assert response.value.to_ssz() == codec.serialize(value)
    assert response.proposal.slot == 0
    assert response.metadata["execution_payload_value"] == 12
    assert response.metadata["extra"]["nested"] == ("é",)
    with pytest.raises(TypeError):
        response.metadata["version"] = "gloas"
    with pytest.raises(TypeError):
        response.metadata["extra"]["nested"] = []
    headers = {
        "Eth-Consensus-Version": fork,
        "ETH-Execution-Payload-Blinded": str(blinded).lower(),
        "Eth-Execution-Payload-Value": "12",
        "Eth-Consensus-Block-Value": "34",
    }
    binary = load_proposal_ssz(codec.serialize(value), headers=headers, preset=preset)
    assert binary.value.to_ssz() == response.value.to_ssz()
    assert binary.metadata["consensus_block_value"] == 34
    assert load_proposal_json(text, headers=headers, preset=preset).value.codec == codec


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"version": "unknown", "execution_payload_blinded": False},
        {"version": "fulu"},
        {"version": "fulu", "execution_payload_blinded": "false"},
        {"version": "fulu", "execution_payload_blinded": False, "execution_payload_value": "-1"},
        {"version": "fulu", "execution_payload_blinded": False, "consensus_block_value": True},
    ],
)
def test_invalid_proposal_metadata(metadata):
    with pytest.raises(SSZError):
        load_proposal_json(json.dumps({"data": {}, **metadata}), preset="minimal")


@pytest.mark.parametrize(
    "fork,flag", [("fulu", "execution_payload_blinded"), ("gloas", "execution_payload_included")]
)
@pytest.mark.parametrize(
    "token", ["0", "1", "0.0", "1.0", '"true"', '"false"', "True", "False", "null"]
)
@pytest.mark.parametrize("header", ["true", "false"])
def test_headers_cannot_repair_invalid_json_booleans(fork, flag, token, header):
    text = f'{{"version":"{fork}","{flag}":{token},"data":{{}}}}'
    with pytest.raises(SSZError):
        load_proposal_json(
            text, preset="minimal", headers={"eth-" + flag.replace("_", "-"): header}
        )


@pytest.mark.parametrize("value", ["True", "False", "TRUE", "FALSE", "1", "0", " true", "false "])
def test_boolean_headers_require_lowercase_literals(value):
    with pytest.raises(SSZError, match="Invalid.*header"):
        load_proposal_ssz(
            b"",
            headers={"eth-consensus-version": "fulu", "eth-execution-payload-blinded": value},
            preset="minimal",
        )


def test_response_rejects_duplicate_missing_and_conflicting_metadata():
    codec = get_type("BeaconBlockContents", fork="fulu", preset="minimal")
    data = codec.dumps(codec.default())
    good = '{"version":"fulu","execution_payload_blinded":false,"data":' + data + "}"
    for text in (
        good[:-1] + ',"ver\\u0073ion":"electra"}',
        good[:-1] + ',"data":' + data + "}",
        good + " null",
        '{"version":"fulu","execution_payload_blinded":false}',
    ):
        with pytest.raises(SSZError):
            load_proposal_json(text, preset="minimal")
    with pytest.raises(SSZError, match="Conflicting"):
        load_proposal_json(good, preset="minimal", headers={"eth-consensus-version": "electra"})
    with pytest.raises(SSZError):
        load_proposal_ssz(b"", headers={"eth-consensus-version": "fulu"}, preset="minimal")


def test_blob_data_is_not_materialized_by_python_metadata_parser(monkeypatch):
    from ssz_z import beacon_api

    codec = get_type("BeaconBlockContents", fork="fulu", preset="minimal")
    value = codec.default()
    value["blobs"] = [bytes(131072)]
    text = json.dumps(
        {"data": codec.to_json(value), "version": "fulu", "execution_payload_blinded": False}
    )
    original = beacon_api._parse_json

    def metadata_only(raw):
        assert len(raw) < 300
        return original(raw)

    monkeypatch.setattr(beacon_api, "_parse_json", metadata_only)
    assert load_proposal_json(text, preset="minimal").value.to_ssz() == codec.serialize(value)
