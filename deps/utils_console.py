import json


def prettyPrintDict(myDict):
    pretty_dict = json.dumps(myDict, indent=2, default=str)
    print(pretty_dict)
