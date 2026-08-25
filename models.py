from pydantic import BaseModel, Field


class TruncatedResponseError(Exception):
    """Antwort der API war kein gueltiges JSON - meist abgeschnitten wegen Output-Limit."""


class Event(BaseModel):
    source_id: int = Field(description="Nummer der QUELLE, aus der dieses Event stammt")
    title: str = Field(description="Titel der Veranstaltung")
    date_start: str = Field(description="Startdatum im Format YYYY-MM-DD")
    date_end: str | None = Field(
        default=None,
        description="Enddatum YYYY-MM-DD, nur bei mehrtaegigen Veranstaltungen, sonst null",
    )
    location: str = Field(description="Ort oder Institution der Veranstaltung")
    description: str = Field(description="Kurze Zusammenfassung in 1-2 Saetzen")


class EventList(BaseModel):
    events: list[Event]