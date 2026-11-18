import json

import pytest

from ssz_z import PRESETS, SSZError, get_type, list_types
from ssz_z.beacon_api import BlockValue, GloasProposal, load_proposal_json, load_proposal_ssz


def proposal_values(preset, included, *, self_build=True):
    def codec(name):
        return get_type(name, fork="gloas", preset=preset)

    block = codec("BeaconBlock").default()
    block["slot"] = 42
    block["parent_root"] = b"\x11" * 32
    builder_index = (1 << 64) - 1 if self_build else 12
    block["body"]["signed_execution_payload_bid"]["message"]["builder_index"] = builder_index
    envelope = codec("ExecutionPayloadEnvelope").default()
    envelope.update(
        builder_index=builder_index,
        beacon_block_root=codec("BeaconBlock").hash_tree_root(block),
        parent_beacon_block_root=block["parent_root"],
    )
    envelope["payload"]["slot_number"] = block["slot"]
    contents = {
        "block": block,
        "execution_payload_envelope": envelope,
        "kzg_proofs": [b"\x22" * 48] * 128,
        "blobs": [b"\x33" * 131072],
    }
    name = "BeaconBlockContents" if included else "BeaconBlock"
    return codec, block, envelope, contents, codec(name).load_obj(contents if included else block)


@pytest.mark.parametrize("preset", PRESETS)
@pytest.mark.parametrize("included", [False, True])
def test_gloas_block_and_payload_publications_are_separate(preset, included):
    codec, block, envelope, contents, value = proposal_values(preset, included)
    metadata = {"version": "gloas", "execution_payload_included": included}
    response = load_proposal_json(
        json.dumps({"data": value.to_json_value(), **metadata}), preset=preset
    )
    proposal = response.proposal
    assert isinstance(proposal, GloasProposal)
    assert proposal.block.slot == 42
    assert proposal.is_self_build
    assert proposal.payload_included == included
    headers = {
        "Eth-Consensus-Version": "gloas",
        "Eth-Execution-Payload-Included": str(included).lower(),
        "Eth-Builder-Url": "https://builder.example",
    }
    binary = load_proposal_ssz(value.to_ssz(), headers=headers, preset=preset)
    assert binary.value.to_ssz() == response.value.to_ssz()
    assert binary.metadata["builder_url"] == "https://builder.example"
    block_signature, payload_signature = b"\x44" * 96, b"\x55" * 96
    signed_block = proposal.sign_block(block_signature)
    assert signed_block.codec == codec("SignedBeaconBlock")
    assert signed_block.to_ssz() == codec("SignedBeaconBlock").serialize(
        {"message": block, "signature": block_signature}
    )
    assert "SignedBeaconBlockContents" not in list_types(fork="gloas", preset=preset)
    if included:
        with pytest.raises(ValueError, match="GloasProposal"):
            BlockValue(value)
        signed_payload = proposal.sign_payload(payload_signature)
        expected = {
            "signed_execution_payload_envelope": {
                "message": envelope,
                "signature": payload_signature,
            },
            "kzg_proofs": contents["kzg_proofs"],
            "blobs": contents["blobs"],
        }
        assert signed_payload.codec == codec("SignedExecutionPayloadEnvelopeContents")
        assert signed_payload.codec.schema["fields"]["kzg_proofs"]["limit"] == 33554432
        assert signed_payload.codec.schema["fields"]["blobs"]["limit"] == 4096
    else:
        with pytest.raises(ValueError, match="Fetch"):
            proposal.sign_payload(payload_signature)
        signed_payload = proposal.sign_payload(
            payload_signature, envelope=codec("ExecutionPayloadEnvelope").load_obj(envelope)
        )
        expected = {"message": envelope, "signature": payload_signature}
        assert signed_payload.codec == codec("SignedExecutionPayloadEnvelope")
    assert signed_payload.to_ssz() == signed_payload.codec.serialize(expected)
    assert signed_payload.hash_tree_root() == signed_payload.codec.hash_tree_root(expected)
    assert response.value.to_ssz() == value.to_ssz()


@pytest.mark.parametrize("included", [False, True])
def test_builder_bid_does_not_reveal_a_payload(included):
    _, _, _, _, value = proposal_values("minimal", included, self_build=False)
    proposal = GloasProposal(value)
    assert not proposal.is_self_build
    assert proposal.sign_block(bytes(96)).codec.name == "SignedBeaconBlock"
    with pytest.raises(ValueError, match="builder must reveal"):
        proposal.sign_payload(bytes(96))


@pytest.mark.parametrize(
    "field", ["beacon_block_root", "parent_beacon_block_root", "builder_index", "slot_number"]
)
@pytest.mark.parametrize("included", [False, True])
def test_payload_must_belong_to_its_proposal(field, included):
    codec, _, envelope, contents, value = proposal_values("minimal", included)
    if field == "slot_number":
        envelope["payload"][field] += 1
    elif field == "builder_index":
        envelope[field] = 99
    else:
        envelope[field] = b"\x77" * 32
    if included:
        proposal = GloasProposal(codec("BeaconBlockContents").load_obj(contents))
        kwargs = {}
    else:
        proposal = GloasProposal(value)
        kwargs = {"envelope": codec("ExecutionPayloadEnvelope").load_obj(envelope)}
    with pytest.raises(SSZError, match="does not match"):
        proposal.sign_payload(bytes(96), **kwargs)


@pytest.mark.parametrize(
    "metadata",
    [
        {"version": "gloas"},
        {"version": "gloas", "execution_payload_included": "true"},
        {
            "version": "gloas",
            "execution_payload_included": False,
            "execution_payload_blinded": True,
        },
    ],
)
def test_gloas_requires_its_own_response_metadata(metadata):
    with pytest.raises(SSZError):
        load_proposal_json(json.dumps({"data": {}, **metadata}), preset="minimal")
