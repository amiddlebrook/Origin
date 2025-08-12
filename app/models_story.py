from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, event, DDL, func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.schema import FetchedValue
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import TypeDecorator, TEXT

from app.database import Base
from app.core.config import settings


class TSText(TypeDecorator):
    impl = TEXT
    cache_ok = True


@compiles(TSVECTOR, 'sqlite')
def compile_tsvector_sqlite(type_, compiler, **kw):
    return "TEXT"


class SearchMixin:
    """Mixin that adds search functionality to models."""
    __ts_vector__ = None

    @declared_attr
    def search_vector(cls):
        if cls.__ts_vector__:
            return Column(TSVECTOR,
                          FetchedValue(),
                          index=True,
                          info={'searchable': True})
        return None

    def _update_search_vector(self):
        """Update the search vector with the current model's searchable fields."""
        if self.__ts_vector__ and hasattr(self, 'search_vector'):
            search_text = ' '.join(
                str(getattr(self, col, ''))
                for col in self.__ts_vector__.get('search_vector', [])
                if getattr(self, col, None)
            )
            if search_text:
                if 'sqlite' in settings.DATABASE_URL:
                    self.search_vector = search_text
                else:
                    # The to_tsvector function is specific to PostgreSQL
                    self.search_vector = func.to_tsvector('english', search_text)


def create_tsvector_trigger(
        table_name,
        tsvector_column,
        search_columns,
        function_name=None,
        trigger_name=None
):
    """Create a function and trigger for updating a tsvector column."""
    if not function_name:
        function_name = f"{table_name}_search_vector_update"
    if not trigger_name:
        trigger_name = f"update_{table_name}_search_vector"

    columns = ", ".join(f'NEW.{col}' for col in search_columns)

    return DDL("""
        CREATE OR REPLACE FUNCTION %(function_name)s() RETURNS TRIGGER AS $$
        BEGIN
            NEW.%(tsvector_column)s := to_tsvector('english', %(columns_expr)s);
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS %(trigger_name)s ON %(table_name)s;
        CREATE TRIGGER %(trigger_name)s
        BEFORE INSERT OR UPDATE ON %(table_name)s
        FOR EACH ROW EXECUTE FUNCTION %(function_name)s();
    """ % {
        'function_name': function_name,
        'trigger_name': trigger_name,
        'table_name': table_name,
        'tsvector_column': tsvector_column,
        'columns_expr': " || ' ' || ".join(f"COALESCE({col}, '')" for col in search_columns)
    })


class NameStory(SearchMixin, Base):
    __tablename__ = "name_stories"
    __ts_vector__ = {
        'search_vector': ['name', 'narrative']
    }

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    research_id = Column(Integer, ForeignKey("research.id"), nullable=True, index=True)

    # Content
    name = Column(String(255), nullable=False, index=True)
    narrative = Column(Text, nullable=True)
    sources = Column(JSON, nullable=True)
    illustration_url = Column(String(512), nullable=True)

    # Status
    status = Column(String(50), default="pending", nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="name_stories")
    research = relationship("Research", back_populates="stories")
    oral_histories = relationship("OralHistory", back_populates="story")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._update_search_vector()


class OralHistory(SearchMixin, Base):
    __tablename__ = "oral_histories"
    __ts_vector__ = {
        'search_vector': ['name', 'transcript', 'summary']
    }

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    story_id = Column(Integer, ForeignKey("name_stories.id"), nullable=True, index=True)

    # Content
    name = Column(String(255), nullable=False, index=True)
    audio_url = Column(String(512), nullable=False)
    transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)

    # Metadata
    duration_seconds = Column(Integer, nullable=True, index=True)
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True, index=True)

    # Status
    status = Column(String(50), default="pending", nullable=False, index=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Relationships
    user = relationship("User", back_populates="oral_histories")
    story = relationship("NameStory", back_populates="oral_histories")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._update_search_vector()

    def update_search_vector(self):
        """Public method to update the search vector, e.g., after transcript is generated."""
        self._update_search_vector()
