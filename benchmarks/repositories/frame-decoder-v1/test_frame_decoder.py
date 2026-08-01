import unittest

from frame_decoder import decode_frames_by_chunk


class FrameDecoderTests(unittest.TestCase):
    def test_header_payload_and_multiple_frames_cross_chunks(self) -> None:
        chunks = [
            "00",
            "00",
            "00",
            "03",
            "61",
            "62",
            "63",
            "00000000",
            "00000002ff00",
        ]
        self.assertEqual(
            decode_frames_by_chunk(chunks, 3),
            [[], [], [], [], [], [], ["616263"], [""], ["ff00"]],
        )

    def test_empty_chunks_preserve_alignment(self) -> None:
        self.assertEqual(
            decode_frames_by_chunk(["", "00000001", "", "41", ""], 1),
            [[], [], [], ["41"], []],
        )

    def test_uppercase_payload_is_normalized(self) -> None:
        self.assertEqual(
            decode_frames_by_chunk(["00000002AB", "CD"], 2),
            [[], ["abcd"]],
        )

    def test_invalid_chunks_are_rejected(self) -> None:
        for chunks in (["0"], ["00000001GG"]):
            with self.subTest(chunks=chunks), self.assertRaises(ValueError):
                decode_frames_by_chunk(chunks, 4)

    def test_incomplete_input_is_rejected(self) -> None:
        for chunks in (["0000"], ["000000036162"]):
            with self.subTest(chunks=chunks), self.assertRaises(ValueError):
                decode_frames_by_chunk(chunks, 4)

    def test_invalid_maximum_is_rejected(self) -> None:
        for maximum in (-1, True):
            with self.subTest(maximum=maximum), self.assertRaises(ValueError):
                decode_frames_by_chunk([], maximum)

    def test_declared_length_over_maximum_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            decode_frames_by_chunk(["00000003"], 2)


if __name__ == "__main__":
    unittest.main()