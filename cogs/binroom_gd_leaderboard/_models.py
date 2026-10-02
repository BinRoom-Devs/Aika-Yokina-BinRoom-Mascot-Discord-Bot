class GDPlayer:
    __slots__ = (
        "accountID",
        "color1",
        "color2",
        "creatorPoints",
        "demons",
        "diamonds",
        "glow",
        "icon",
        "moons",
        "playerID",
        "secretCoins",
        "stars",
        "userCoins",
        "username"
    )
    
    def __init__(self, data: dict):
        self.username = data.get("username", "Tidak Diketahui")
        self.accountID = int(data.get("accountID", 0))
        self.playerID = int(data.get("playerID", 0))
        self.stars = int(data.get("stars", 0))
        self.moons = int(data.get("moons", 0))
        self.diamonds = int(data.get("diamonds", 0))
        self.secretCoins = int(data.get("coins", 0))
        self.userCoins = int(data.get("userCoins", 0))
        self.demons = int(data.get("demons", 0))
        self.creatorPoints = int(data.get("cp", 0))
        self.icon = int(data.get("icon", 1))
        self.color1 = int(data.get("col1", 0))
        self.color2 = int(data.get("col2", 0))
        self.glow = 1 if data.get("glow") else 0
    
    def get_icon_url(self) -> str:
        if self.glow:
            return f"https://gdicon.oat.zone/icon.png?type=cube&value={self.icon}&color1={self.color1}&color2={self.color2}&glow={self.glow}"
        return f"https://gdicon.oat.zone/icon.png?type=cube&value={self.icon}&color1={self.color1}&color2={self.color2}"