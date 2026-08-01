def decode_frames_by_chunk(chunks, max_frame_size):
    """Decode length-prefixed frames while preserving chunk alignment."""
    if (
        isinstance(max_frame_size, bool)
        or not isinstance(max_frame_size, int)
        or max_frame_size < 0
    ):
        raise ValueError("max_frame_size must be a non-negative integer")

    buffer = bytearray()
    expected_length = None
    outputs = []
    for chunk in chunks:
        if (
            not isinstance(chunk, str)
            or len(chunk) % 2
            or any(character not in "0123456789abcdefABCDEF" for character in chunk)
        ):
            raise ValueError("chunks must contain even-length hexadecimal strings")
        buffer.extend(bytes.fromhex(chunk))
        completed = []
        while True:
            if expected_length is None:
                if len(buffer) < 4:
                    break
                expected_length = int.from_bytes(buffer[:4], "big")
                del buffer[:4]
                if expected_length > max_frame_size:
                    raise ValueError("frame exceeds max_frame_size")
            if len(buffer) <= expected_length:
                break
            payload = bytes(buffer[:expected_length])
            del buffer[:expected_length]
            completed.append(payload.hex())
            expected_length = None
        outputs.append(completed)

    if expected_length is not None or buffer:
        raise ValueError("incomplete frame at end of input")
    return outputs