import pprint
from io import StringIO


def pretty_dict(d):
    # Create a string buffer and pretty print the dict to it
    output = StringIO()
    pprint.pprint(d, stream=output)
    # Get the string value and return it without the last newline
    return output.getvalue().rstrip()
