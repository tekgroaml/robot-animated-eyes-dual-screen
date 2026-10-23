"""Verify frame-rate-independent motion and complete blink recovery."""
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import EyeMotion, POSES, validate_config


class MotionTests(unittest.TestCase):
    def test_expression_transition_matches_across_frame_rates(self):
        results = []
        for fps in (30, 60, 120):
            motion = EyeMotion(7); motion.expression = 'angry'
            for _ in range(fps): motion.update(1/fps)
            results.append(motion.pose)
        for pose in results:
            for actual, expected in zip(pose, results[0]): self.assertAlmostEqual(actual, expected, places=10)
            self.assertAlmostEqual(pose[0], POSES['angry'].openness, places=3)

    def test_blink_closes_then_recovers_and_gaze_is_bounded(self):
        motion = EyeMotion(7); motion.blink()
        motion.update(.12)
        self.assertAlmostEqual(motion.blink_amount(), 1)
        motion.update(.20)
        self.assertEqual(motion.blink_amount(), 0)
        motion.target = [100, -100]
        for _ in range(600): motion.update(1/60)
        self.assertTrue(all(math.isfinite(x) and -1 <= x <= 1 for x in motion.gaze))

    def test_invalid_canvas_settings_are_rejected(self):
        for size, fps in ((0, 60), (480, 0), (9999, 60)):
            with self.assertRaises(ValueError): validate_config(size, fps)


if __name__ == '__main__': unittest.main()
