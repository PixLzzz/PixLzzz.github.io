"""Search criteria and app configuration."""

CRITERIA = {
    "min_price": 500_000,
    "max_price": 750_000,
    "min_bedrooms": 2,
    "neighborhoods": [
        "Plateau-Mont-Royal",
        "Le Plateau-Mont-Royal",
        "Mile-End",
        "Mile End",
        "Plateau Mont-Royal",
        "Plateau",
        "Rosemont",
        "Rosemont-La Petite-Patrie",
        "Rosemont–La Petite-Patrie",
        "La Petite-Patrie",
        "Beaubien",
    ],
    "city": "Montreal",
}

# Backend runs on 8001 to avoid conflict with Appartio (8000)
API_PORT = 8001
API_HOST = "0.0.0.0"
