class Feedback(object):
    """Result feedback class"""
    def __init__(self):
        self.human_readable = '' # human readable advice
        self.primary_error = None
        self.specific_error = None
        self.matches = {}        # possible errors

    def to_dict(self):
        return self.__dict__

    def __repr__(self):
        return self.human_readable

def check(sentence):
    result = Feedback()
    result.human_readable = "This is a piece of human readable advice."
    result.primary_error = 'DUMMY_MODEL_PRIMARY_ERROR'
    result.specific_error = 'DUMMY_MODEL_SPECIFIC_ERROR'
