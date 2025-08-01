from pydantic import BaseModel

class BookingData(BaseModel):
    first_name: str
    middle_name: str
    last_name: str
    gender: str
    citizenship: str
    phone_number: str
    email: str | None
    travel_type: str
    direction: str
    number_of_travelers: int
    ferry: str
    class_: str
    other_travelers: str | None
    payment_method: str
    payment_number: str