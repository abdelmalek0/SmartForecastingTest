from structs.models import Period
from structs.enums import PeriodType

frequency_mapping = {
    PeriodType.MINUTE: 'T',
    PeriodType.HOUR: 'H',
    PeriodType.DAY: 'D',
    PeriodType.WEEK: 'W',
    PeriodType.MONTH: 'M',
    PeriodType.YEAR: 'Y'
}


def period_to_pandas_freq(period: Period) -> str:
    freq = frequency_mapping.get(period.type)
    if freq is None:
        raise ValueError(f"Unknown PeriodType: {period.type}")
    return f"{int(period.value)}{freq}"