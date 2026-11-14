class User:
    def __init__(self, name):
        self.name = name

    def greet(self):
        return "hi " + self.name


class Admin(User):
    pass
