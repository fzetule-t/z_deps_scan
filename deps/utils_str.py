def countLeadingBlanks(str):
    return len(str) - len(str.lstrip())


def isNotBlank(s):
    return bool(s and not s.isspace())


def extractMatchingParts(line, conf_list):
    for conf in conf_list:
        if line.startswith(conf):
            return conf
    return None
