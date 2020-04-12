import threading


class OverwritableSlot:
    def __init__(self):
        self.value = None
        self.slotEmpty = threading.Lock()
        self.slotFull = threading.Lock()
        # Initially set slotFull to false
        self.slotFull.acquire()

    def send(self, value):
        self.slotEmpty.acquire()
        self.value = value
        self.slotFull.release()
        self.slotEmpty.release()

    def receive(self):
        self.slotFull.acquire()
        result = self.value
        return result

