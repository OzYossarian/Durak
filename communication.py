import threading


class OverwritableSlot:
    def __init__(self):
        self.value = None
        self.slotEmpty = MultiReleaseSempahore(down=False)
        self.slotFull = MultiReleaseSempahore(down=True)

    def send(self, value):
        self.slotEmpty.acquire()
        self.value = value
        self.slotFull.release()
        self.slotEmpty.release()

    def receive(self):
        self.slotFull.acquire()
        result = self.value
        return result


class MultiReleaseSempahore():
    def __init__(self, down):
        self.semaphore = threading.BoundedSemaphore(value=1)
        # Set the semaphore to the initial value
        if down:
            self.semaphore.acquire()

    def release(self):
        try:
            self.semaphore.release()
        except ValueError:
            # This is fine.
            pass

    def acquire(self):
        self.semaphore.acquire()






