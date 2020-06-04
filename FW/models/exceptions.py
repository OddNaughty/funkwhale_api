class FWDBUpdateErrorNoId(Exception):
    def __init__(self):
        super().__init__("No db id was found for this object")

class FWIdAlreadySet(Exception):
    def __init__(self):
        super().__init__("Instance ID already set")