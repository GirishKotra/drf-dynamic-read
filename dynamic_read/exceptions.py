class ChildNotSupported(Exception):
    """Represents a child object cannot be used with dynamic drf"""

    def __init__(self, child):
        self.child = child

    def __str__(self):
        return f"ChildNotSupported: {self.child}"
