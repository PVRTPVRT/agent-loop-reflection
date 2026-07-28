from hypothesis import given, settings
from hypothesis import strategies as st

from agentloop.evaluation_v2_models import EvaluationDataset
from agentloop.oracles import oracle_decode_frames_by_chunk
from agentloop.routing_suites import RoutingSuiteRegistry


def encode_frames(frames: list[bytes]) -> bytes:
    return b"".join(len(frame).to_bytes(4, "big") + frame for frame in frames)


@st.composite
def encoded_chunkings(draw):
    frames = draw(
        st.lists(
            st.binary(min_size=0, max_size=32),
            min_size=0,
            max_size=8,
        )
    )
    stream = encode_frames(frames)
    if not stream:
        chunks = [""] if draw(st.booleans()) else []
    else:
        widths = draw(
            st.lists(
                st.integers(min_value=1, max_value=len(stream)),
                min_size=1,
                max_size=12,
            )
        )
        chunks = []
        cursor = 0
        width_index = 0
        while cursor < len(stream):
            width = widths[width_index % len(widths)]
            chunks.append(stream[cursor : cursor + width].hex())
            cursor += width
            width_index += 1
        if draw(st.booleans()):
            position = draw(st.integers(min_value=0, max_value=len(chunks)))
            chunks.insert(position, "")
    return frames, stream, chunks


@given(encoded_chunkings())
@settings(max_examples=100, deadline=None, derandomize=True)
def test_decoder_is_invariant_to_valid_chunking(example) -> None:
    frames, stream, chunks = example
    max_frame_size = max((len(frame) for frame in frames), default=0)

    chunked = oracle_decode_frames_by_chunk(chunks, max_frame_size)
    contiguous = oracle_decode_frames_by_chunk([stream.hex()], max_frame_size)

    assert len(chunked) == len(chunks)
    assert [payload for group in chunked for payload in group] == [
        frame.hex() for frame in frames
    ]
    assert [payload for group in contiguous for payload in group] == [
        frame.hex() for frame in frames
    ]


@given(
    st.lists(
        st.binary(min_size=0, max_size=32),
        min_size=1,
        max_size=8,
    )
)
@settings(max_examples=50, deadline=None, derandomize=True)
def test_decoder_rejects_any_truncated_encoded_stream(frames) -> None:
    stream = encode_frames(frames)
    max_frame_size = max(len(frame) for frame in frames)

    try:
        oracle_decode_frames_by_chunk([stream[:-1].hex()], max_frame_size)
    except ValueError:
        pass
    else:
        raise AssertionError("truncated encoded stream must raise ValueError")


def test_frame_decoder_assets_share_task_identity() -> None:
    dataset = EvaluationDataset.load(
        "benchmarks/datasets/coding-v3-frame-decoder-pilot.json"
    )
    routing = RoutingSuiteRegistry.load(
        "benchmarks/routing/coding-v3-frame-decoder-routing.json"
    )

    assert dataset.tasks[0].task_id == "frame-decoder-001"
    assert routing.require("frame-decoder-001").function_name == (
        "decode_frames_by_chunk"
    )
