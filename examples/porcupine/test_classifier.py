"""Tests sva_classifier. Sparse set of tests."""
import unittest
from check import check, Feedback

class TestClassifierMethods(unittest.TestCase):

    def test_check_sva(self):
        sent = "The girl run incredibly fast."
        actual_fb = check(sent)
        expected_fb = Feedback()
        self.assertEqual(actual_fb.primary_error, 'SUBJECT_VERB_AGREEMENT_ERROR')

if __name__ == '__main__':
    unittest.main()
