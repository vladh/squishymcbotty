def remove_prefix(string, prefix):
    if not string.startswith(prefix):
        return string
    return string[len(prefix):]
