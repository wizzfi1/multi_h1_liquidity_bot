class EventContext:
    """
    Tracks the lifecycle of a single trade idea:
    primary → optional flip → resolve.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.active = False
        self.direction = None
        self.flip_direction = None
        self.tp_level = None
        self.session = None

        self.primary_ticket = None
        self.flip_used = False

    def arm(self, direction: str, flip_direction: str, tp: float, session: str):
        self.active = True
        self.direction = direction
        self.flip_direction = flip_direction
        self.tp_level = tp
        self.session = session

    def primary_placed(self, ticket: int):
        self.primary_ticket = ticket

    def allow_flip(self) -> bool:
        return self.active and not self.flip_used

    def flip_placed(self):
        self.flip_used = True

    def resolve(self):
        self.reset()
