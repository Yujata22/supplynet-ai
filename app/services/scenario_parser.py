from __future__ import annotations

import re

from app.models.scenario import ScenarioRequest


class ScenarioParser:
    """Parse supported natural-language supply-network disruptions."""

    REGION_ALIASES = {
        "pacific northwest": "REG_PNW",
        "pnw": "REG_PNW",
        "west": "REG_WEST",
        "southwest": "REG_SW",
        "midwest": "REG_MW",
        "south": "REG_SOUTH",
        "southeast": "REG_SE",
        "mid-atlantic": "REG_MA",
        "mid atlantic": "REG_MA",
        "northeast": "REG_NE",
    }

    DC_ALIASES = {
        "los angeles": "DC_LA",
        "la": "DC_LA",
        "dallas": "DC_DAL",
        "chicago": "DC_CHI",
        "new york": "DC_NY",
        "ny": "DC_NY",
    }

    @staticmethod
    def _extract_percentage(
        text: str,
    ) -> float | None:
        """
        Extract a percentage and return it as a decimal.

        Example:
        "increase demand by 20%" -> 0.20
        """

        match = re.search(
            r"(\d+(?:\.\d+)?)\s*%",
            text,
        )

        if not match:
            return None

        return float(
            match.group(1)
        ) / 100

    @staticmethod
    def _extract_week(
        text: str,
    ) -> int:
        """
        Extract planning week.

        Defaults to week 1 when no week is explicitly provided.
        """

        match = re.search(
            r"\bweek\s*(\d+)\b",
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            return 1

        return int(
            match.group(1)
        )

    def _extract_region(
        self,
        text: str,
    ) -> str | None:
        """
        Extract customer region safely.

        Longer region aliases are checked first so:
        - "southwest" is matched before "south"
        - "southeast" is matched before "south"

        Word boundaries prevent partial-word matches.
        """

        for alias, region_id in sorted(
            self.REGION_ALIASES.items(),
            key=lambda item: len(
                item[0]
            ),
            reverse=True,
        ):
            pattern = (
                r"\b"
                + re.escape(alias)
                + r"\b"
            )

            if re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            ):
                return region_id

        # Support explicit IDs such as REG_WEST.
        region_match = re.search(
            r"\bREG_[A-Z]+\b",
            text.upper(),
        )

        if region_match:
            return region_match.group(0)

        return None

    def _extract_dc(
        self,
        text: str,
    ) -> str | None:
        """
        Extract distribution center safely.

        Word boundaries prevent aliases such as "la"
        from matching inside "Dallas".
        """

        for alias, dc_id in sorted(
            self.DC_ALIASES.items(),
            key=lambda item: len(
                item[0]
            ),
            reverse=True,
        ):
            pattern = (
                r"\b"
                + re.escape(alias)
                + r"\b"
            )

            if re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            ):
                return dc_id

        # Support explicit IDs such as DC_DAL.
        dc_match = re.search(
            r"\bDC_[A-Z]+\b",
            text.upper(),
        )

        if dc_match:
            return dc_match.group(0)

        return None

    @staticmethod
    def _extract_supplier(
        text: str,
    ) -> str | None:
        """
        Extract supplier ID.

        Example:
        SUP_001
        """

        match = re.search(
            r"\bSUP_\d+\b",
            text.upper(),
        )

        if match:
            return match.group(0)

        return None

    def parse(
        self,
        query: str,
    ) -> ScenarioRequest:
        """
        Convert a supported natural-language disruption
        into a validated ScenarioRequest.
        """

        text = query.strip().lower()

        if not text:
            raise ValueError(
                "Scenario query cannot be empty."
            )

        percentage = (
            self._extract_percentage(
                text
            )
        )

        week = self._extract_week(
            text
        )

        supplier_id = (
            self._extract_supplier(
                text
            )
        )

        dc_id = self._extract_dc(
            text
        )

        region_id = (
            self._extract_region(
                text
            )
        )

        # --------------------------------------------------
        # DEMAND SURGE
        # --------------------------------------------------

        if (
            "demand" in text
            and any(
                word in text
                for word in [
                    "increase",
                    "increased",
                    "surge",
                    "up",
                    "rise",
                    "higher",
                    "grow",
                    "growth",
                ]
            )
        ):
            if region_id is None:
                raise ValueError(
                    "Could not identify customer region."
                )

            if percentage is None:
                raise ValueError(
                    "Demand surge requires a percentage."
                )

            return ScenarioRequest(
                scenario_type=(
                    "demand_surge"
                ),
                region_id=region_id,
                week=week,
                percentage=percentage,
            )

        # --------------------------------------------------
        # DC CAPACITY REDUCTION
        # --------------------------------------------------

        if (
            "capacity" in text
            and dc_id is not None
            and any(
                word in text
                for word in [
                    "reduce",
                    "reduced",
                    "reduction",
                    "down",
                    "decrease",
                    "decreased",
                    "cut",
                    "lower",
                ]
            )
        ):
            if percentage is None:
                raise ValueError(
                    "DC capacity reduction requires a percentage."
                )

            return ScenarioRequest(
                scenario_type=(
                    "dc_capacity_reduction"
                ),
                dc_id=dc_id,
                week=week,
                percentage=percentage,
            )

        # --------------------------------------------------
        # SUPPLIER OUTAGE
        # --------------------------------------------------

        if (
            supplier_id is not None
            and any(
                phrase in text
                for phrase in [
                    "supplier outage",
                    "supplier down",
                    "supplier unavailable",
                    "supplier offline",
                    "shut down",
                    "shutdown",
                    "outage",
                    "unavailable",
                    "offline",
                ]
            )
        ):
            return ScenarioRequest(
                scenario_type=(
                    "supplier_outage"
                ),
                supplier_id=(
                    supplier_id
                ),
                week=week,
            )

        # --------------------------------------------------
        # SUPPLIER CAPACITY REDUCTION
        # --------------------------------------------------

        if (
            supplier_id is not None
            and "capacity" in text
            and percentage is not None
            and any(
                word in text
                for word in [
                    "reduce",
                    "reduced",
                    "reduction",
                    "down",
                    "decrease",
                    "decreased",
                    "cut",
                    "lower",
                ]
            )
        ):
            return ScenarioRequest(
                scenario_type=(
                    "supplier_capacity_reduction"
                ),
                supplier_id=(
                    supplier_id
                ),
                week=week,
                percentage=percentage,
            )

        # --------------------------------------------------
        # INBOUND COST INCREASE
        # --------------------------------------------------

        if (
            supplier_id is not None
            and dc_id is not None
            and any(
                phrase in text
                for phrase in [
                    "cost",
                    "freight",
                    "transportation",
                    "rate",
                ]
            )
            and percentage is not None
            and any(
                word in text
                for word in [
                    "increase",
                    "increased",
                    "higher",
                    "rise",
                    "up",
                ]
            )
        ):
            return ScenarioRequest(
                scenario_type=(
                    "inbound_cost_increase"
                ),
                supplier_id=(
                    supplier_id
                ),
                dc_id=dc_id,
                week=week,
                percentage=percentage,
            )

        # --------------------------------------------------
        # DISABLE INBOUND LANE
        # --------------------------------------------------

        if (
            supplier_id is not None
            and dc_id is not None
            and "lane" in text
            and any(
                word in text
                for word in [
                    "disable",
                    "disabled",
                    "close",
                    "closed",
                    "unavailable",
                    "outage",
                    "block",
                    "blocked",
                ]
            )
        ):
            return ScenarioRequest(
                scenario_type=(
                    "disable_inbound_lane"
                ),
                supplier_id=(
                    supplier_id
                ),
                dc_id=dc_id,
                week=week,
            )

        # --------------------------------------------------
        # DISABLE OUTBOUND LANE
        # --------------------------------------------------

        if (
            dc_id is not None
            and region_id is not None
            and "lane" in text
            and any(
                word in text
                for word in [
                    "disable",
                    "disabled",
                    "close",
                    "closed",
                    "unavailable",
                    "outage",
                    "block",
                    "blocked",
                ]
            )
        ):
            return ScenarioRequest(
                scenario_type=(
                    "disable_outbound_lane"
                ),
                dc_id=dc_id,
                region_id=(
                    region_id
                ),
                week=week,
            )

        raise ValueError(
            "Unsupported or incomplete scenario request."
        )