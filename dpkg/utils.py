import datetime

DATE_FMT = '%Y-%m-%d'


def parse_date(date):
    """Function to parse a date string into a date object."""
    return datetime.datetime.strptime(date, DATE_FMT).date()


def get_date(prompt, default=None):
    """Function to get a date via prompt."""
    if default:
        act_prompt = '%s [%s]: ' % (prompt, default.strftime(DATE_FMT))
    else:
        act_prompt = '%s: ' % prompt

    d = input(act_prompt)
    if default and not d:
        return default
    elif not d:
        d = get_date(prompt, default)

    try:
        return datetime.datetime.strptime(d, DATE_FMT).date()
    except ValueError as e:
        print(e)
        return get_date(prompt, default)
