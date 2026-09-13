"""Import every model so Base.metadata knows about all tables before create_all()."""
from app.models.core import Property, User, Channel, Guest, UserRole  # noqa: F401
from app.models.booking import Reservation, Promotion, CalendarDay, ReservationStatus  # noqa: F401
from app.models.competitor import Competitor, CompetitorRate  # noqa: F401
from app.models.review import Review, ReviewTopic  # noqa: F401
from app.models.importing import ImportBatch, ImportMapping  # noqa: F401
from app.models.recommendation import Recommendation, OperationalIssue  # noqa: F401
from app.models.stubs import Expense, Campaign, GuestMessage  # noqa: F401
