"""Fixer engine - scan and auto-fix Power BI issues."""

from core.fixers.base import BaseFixer, FixerEngine
from core.fixers.report_fixers import (
    FixPieCharts,
    FixPageSize,
    FixVisualAlignment,
    FixRemoveUnusedCustomVisuals,
    FixHideVisualFilters,
)
from core.fixers.report_fixers_v2 import (
    FixDuplicateVisuals,
    FixOverlappingVisuals,
    FixEmptyPages,
    FixVisualTabOrder,
    FixLargeCardCount,
    FixSlicerSync,
)
from core.fixers.model_fixers import (
    FixBidirectionalRelationships,
    FixCalculatedColumnsToMeasures,
)
from core.fixers.model_fixers_v2 import (
    FixInactiveRelationships,
    FixAutoDateTime,
    FixCalendarTable,
    FixCalendarRelationships,
    FixTimeIntelligenceMeasures,
    FixMeasureTable,
    FixTimeIntelligenceGroup,
    FixUnitsCalcGroup,
)
from core.fixers.bpa_fixers import (
    FixDivideOperator,
    FixMeasureDescriptions,
    FixMeasureFormatStrings,
    FixColumnNaming,
    FixHideForeignKeys,
    FixSummarizeByNone,
    FixFloatingPointTypes,
)
from core.fixers.bpa_fixers_v2 import (
    FixMeasureFolders,
    FixColumnFolders,
    FixUnreferencedMeasures,
    FixExpensiveDAXPatterns,
    FixMissingRelationships,
    FixSortByColumn,
    FixDataCategoryGeo,
    FixRLSPerformance,
    FixUnusedColumns,
)

# Register all fixers (37 total)
ALL_FIXERS = [
    # ── Report fixers (11) ──────────────────────────────────────
    FixPieCharts,
    FixPageSize,
    FixVisualAlignment,
    FixRemoveUnusedCustomVisuals,
    FixHideVisualFilters,
    FixDuplicateVisuals,
    FixOverlappingVisuals,
    FixEmptyPages,
    FixVisualTabOrder,
    FixLargeCardCount,
    FixSlicerSync,
    # ── Model fixers (10) ───────────────────────────────────────
    FixBidirectionalRelationships,
    FixCalculatedColumnsToMeasures,
    FixInactiveRelationships,
    FixAutoDateTime,
    FixCalendarTable,
    FixCalendarRelationships,
    FixTimeIntelligenceMeasures,
    FixMeasureTable,
    FixTimeIntelligenceGroup,
    FixUnitsCalcGroup,
    # ── BPA fixers (16) ─────────────────────────────────────────
    FixDivideOperator,
    FixMeasureDescriptions,
    FixMeasureFormatStrings,
    FixColumnNaming,
    FixHideForeignKeys,
    FixSummarizeByNone,
    FixFloatingPointTypes,
    FixMeasureFolders,
    FixColumnFolders,
    FixUnreferencedMeasures,
    FixExpensiveDAXPatterns,
    FixMissingRelationships,
    FixSortByColumn,
    FixDataCategoryGeo,
    FixRLSPerformance,
    FixUnusedColumns,
]

__all__ = ["BaseFixer", "FixerEngine", "ALL_FIXERS"]
