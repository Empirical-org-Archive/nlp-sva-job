import unittest

class TestClassifierMethods(unittest.TestCase):

    def test_upper(self):
        self.assertEqual('lalala'.upper(), 'LALALA')
        

if __name__ == '__main__':
    unittest.main()
