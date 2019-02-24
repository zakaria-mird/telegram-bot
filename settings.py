import os
from decouple import config

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DEBUG = False
TOKEN = config('TOKEN')

APPLICATIONS = [
    "database",
    "pizza"
]

RESTAURANTS = [
    {
        "name": "Oshi Pokè Bowls",
        "url": "https://www.justeat.it/restaurants-oshipokebowls/menu"
    },
    {
        "name": "Pizzeria del Rondone",
        "url": "https://www.justeat.it/restaurants-pizzeriadelrondone-bologna/menu"
    }
]