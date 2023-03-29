import datetime
from ninja import Schema, Path


class PathDate(Schema):
    year: int
    month: int
    day: int

    def value(self):
        return datetime.date(self.year, self.month, self.day)


@api.get("/events/{year}/{month}/{day}")
def events(request, date: PathDate = Path(...)):
    return {"date": date.value()}
