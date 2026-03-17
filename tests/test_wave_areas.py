import math
import unittest

from ecg_analysis.features.wave_areas import compute_wave_areas_for_record, trapz_area


class WaveAreaTests(unittest.TestCase):
    def test_trapz_area_triangle(self):
        sig = [0.0, 1.0, 0.0]
        self.assertTrue(math.isclose(trapz_area(sig, 0, 2), 1.0))

    def test_compute_wave_areas(self):
        signal = [[0.0] for _ in range(120)]
        for i in range(20, 29):
            signal[i][0] += (i - 20) / 8
        for i in range(60, 80):
            signal[i][0] += 0.2

        beats = [
            {
                "beat_index": 0,
                "p_end": 10,
                "q_onset": 20,
                "q_offset": 22,
                "s_offset": 28,
                "t_onset": 60,
                "t_offset": 79,
            }
        ]

        out = compute_wave_areas_for_record("r1", "train", ["I"], signal, beats)
        self.assertEqual(len(out), 1)
        self.assertIn("ratio_qrs_to_t_plus_q_signed", out[0])


if __name__ == "__main__":
    unittest.main()
