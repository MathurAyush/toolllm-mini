from __future__ import annotations

from .http import APIError, Param, PublicAPI

# Factor to the base unit of each dimension (meter, kilogram, liter,
# square meter, meter per second, second).
_FACTORS = {
    "length": {
        "mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000.0,
        "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.344, "nmi": 1852.0,
    },
    "mass": {"mg": 1e-6, "g": 0.001, "kg": 1.0, "t": 1000.0, "oz": 0.028349523125, "lb": 0.45359237, "st": 6.35029318},
    "volume": {
        "ml": 0.001, "l": 1.0, "m3": 1000.0, "tsp": 0.00492892159375, "tbsp": 0.01478676478125,
        "cup": 0.2365882365, "pt": 0.473176473, "qt": 0.946352946, "gal": 3.785411784,
    },
    "area": {"m2": 1.0, "km2": 1e6, "ha": 1e4, "ft2": 0.09290304, "acre": 4046.8564224, "mi2": 2589988.110336},
    "speed": {"m/s": 1.0, "km/h": 1 / 3.6, "mph": 0.44704, "knot": 0.514444},
    "time": {"s": 1.0, "min": 60.0, "h": 3600.0, "day": 86400.0, "week": 604800.0, "year": 31557600.0},
}

_TEMPERATURES = {"c", "f", "k"}

_ALIASES = {
    "meter": "m", "meters": "m", "metre": "m", "metres": "m",
    "kilometer": "km", "kilometers": "km", "kilometre": "km", "kilometres": "km",
    "centimeter": "cm", "centimeters": "cm", "millimeter": "mm", "millimeters": "mm",
    "inch": "in", "inches": "in", "foot": "ft", "feet": "ft", "yard": "yd", "yards": "yd",
    "mile": "mi", "miles": "mi",
    "gram": "g", "grams": "g", "kilogram": "kg", "kilograms": "kg", "kilo": "kg", "kilos": "kg",
    "pound": "lb", "pounds": "lb", "lbs": "lb", "ounce": "oz", "ounces": "oz", "tonne": "t", "tonnes": "t", "stone": "st",
    "liter": "l", "liters": "l", "litre": "l", "litres": "l", "milliliter": "ml", "milliliters": "ml",
    "gallon": "gal", "gallons": "gal", "cups": "cup", "pint": "pt", "pints": "pt", "quart": "qt", "quarts": "qt",
    "teaspoon": "tsp", "teaspoons": "tsp", "tablespoon": "tbsp", "tablespoons": "tbsp",
    "hectare": "ha", "hectares": "ha", "acres": "acre", "sqm": "m2", "sqft": "ft2",
    "kph": "km/h", "kmh": "km/h", "knots": "knot", "mps": "m/s",
    "second": "s", "seconds": "s", "sec": "s", "minute": "min", "minutes": "min",
    "hour": "h", "hours": "h", "hr": "h", "days": "day", "weeks": "week", "years": "year",
    "celsius": "c", "°c": "c", "fahrenheit": "f", "°f": "f", "kelvin": "k",
}


def _unit(text: str) -> str:
    unit = text.strip().lower()
    return _ALIASES.get(unit, unit)


def _dimension(unit: str) -> str | None:
    return next((dim for dim, units in _FACTORS.items() if unit in units), None)


def _to_celsius(value: float, unit: str) -> float:
    return {"c": value, "f": (value - 32) * 5 / 9, "k": value - 273.15}[unit]


def _from_celsius(value: float, unit: str) -> float:
    return {"c": value, "f": value * 9 / 5 + 32, "k": value + 273.15}[unit]


class UnitConversionAPI(PublicAPI):
    """Offline unit converter; makes no network request."""

    name = "unit_conversion"
    category = "utility"
    description = (
        "Converts a measurement between units of length, distance, weight, volume, "
        "area, speed, time or temperature (e.g. miles to km, pounds to kg, F to C)."
    )
    params = (
        Param("value", "number", "The amount to convert, e.g. 10."),
        Param("from_unit", "string", "Unit to convert from, e.g. 'mi', 'lb', 'F', 'cup'."),
        Param("to_unit", "string", "Unit to convert to, e.g. 'km', 'kg', 'C', 'ml'."),
    )
    example_call = {"value": 10, "from_unit": "miles", "to_unit": "km"}
    example_response = {"value": 10.0, "from_unit": "mi", "to_unit": "km", "result": 16.09344}

    def fetch(self, **args):
        return None

    def parse(self, payload, value, from_unit, to_unit):
        source, target = _unit(from_unit), _unit(to_unit)
        if source in _TEMPERATURES and target in _TEMPERATURES:
            result = _from_celsius(_to_celsius(value, source), target)
        else:
            dimension = _dimension(source)
            if dimension is None or _dimension(target) is None:
                unknown = from_unit if dimension is None else to_unit
                raise APIError(f"Unknown unit '{unknown}'.")
            if _dimension(target) != dimension:
                raise APIError(f"Cannot convert {dimension} ('{from_unit}') to {_dimension(target)} ('{to_unit}').")
            result = value * _FACTORS[dimension][source] / _FACTORS[dimension][target]
        return {"value": value, "from_unit": source, "to_unit": target, "result": round(result, 6)}
