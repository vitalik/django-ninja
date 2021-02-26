weapons = ["Ninjato", "Shuriken", "Katana", "Kama", "Kunai", "Naginata", "Yari"]


@api.get("/weapons")
def list_weapons(request, limit: int = 10, offset: int = 0):
    return weapons[offset: offset + limit]
