"""
Data model for Power BI relationships
Includes complete cardinality and cross-filter behavior
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Cardinality(Enum):
    """Relationship cardinality types"""
    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:*"
    MANY_TO_ONE = "*:1"
    MANY_TO_MANY = "*:*"

    @classmethod
    def from_parts(cls, from_card: str, to_card: str) -> 'Cardinality':
        """
        Create cardinality from from/to parts

        Args:
            from_card: 'one' or 'many'
            to_card: 'one' or 'many'

        Returns:
            Cardinality enum value
        """
        from_symbol = "1" if from_card.lower() == "one" else "*"
        to_symbol = "1" if to_card.lower() == "one" else "*"

        card_map = {
            "1:1": cls.ONE_TO_ONE,
            "1:*": cls.ONE_TO_MANY,
            "*:1": cls.MANY_TO_ONE,
            "*:*": cls.MANY_TO_MANY
        }

        return card_map.get(f"{from_symbol}:{to_symbol}", cls.MANY_TO_ONE)


class CrossFilterDirection(Enum):
    """Cross-filter direction for relationships"""
    SINGLE = "single"  # oneDirection
    BOTH = "both"      # bothDirections

    @classmethod
    def from_behavior(cls, behavior: str) -> 'CrossFilterDirection':
        """Convert from crossFilteringBehavior string"""
        if behavior.lower() in ['bothdirections', 'both']:
            return cls.BOTH
        return cls.SINGLE


@dataclass
class Relationship:
    """
    Represents a relationship between two tables in the data model
    """
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    cardinality: Cardinality
    cross_filter_direction: CrossFilterDirection
    is_active: bool = True
    security_filtering_behavior: Optional[str] = None

    def __post_init__(self):
        """Validate and normalize data"""
        # Ensure cardinality is an enum
        if isinstance(self.cardinality, str):
            # Try to parse string like "1:*"
            if self.cardinality in ["1:1", "1:*", "*:1", "*:*"]:
                card_map = {
                    "1:1": Cardinality.ONE_TO_ONE,
                    "1:*": Cardinality.ONE_TO_MANY,
                    "*:1": Cardinality.MANY_TO_ONE,
                    "*:*": Cardinality.MANY_TO_MANY
                }
                self.cardinality = card_map[self.cardinality]
            else:
                # Default to MANY_TO_ONE
                self.cardinality = Cardinality.MANY_TO_ONE

        # Ensure cross_filter_direction is an enum
        if isinstance(self.cross_filter_direction, str):
            self.cross_filter_direction = CrossFilterDirection.from_behavior(
                self.cross_filter_direction
            )

    @property
    def is_bidirectional(self) -> bool:
        """Check if relationship is bidirectional"""
        return self.cross_filter_direction == CrossFilterDirection.BOTH

    @property
    def is_many_to_many(self) -> bool:
        """Check if relationship is many-to-many"""
        return self.cardinality == Cardinality.MANY_TO_MANY

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'from_table': self.from_table,
            'from_column': self.from_column,
            'to_table': self.to_table,
            'to_column': self.to_column,
            'cardinality': self.cardinality.value,
            'cross_filter_direction': self.cross_filter_direction.value,
            'is_active': self.is_active,
            'is_bidirectional': self.is_bidirectional,
            'is_many_to_many': self.is_many_to_many,
            'security_filtering_behavior': self.security_filtering_behavior
        }

    def __str__(self) -> str:
        """Human-readable string representation"""
        direction = "⟷" if self.is_bidirectional else "→"
        return (f"{self.from_table}.{self.from_column} {direction} "
                f"{self.to_table}.{self.to_column} [{self.cardinality.value}]")
