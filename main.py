from multiprocessing import Process, Event
import time
import signal


def main():
    from frontend.app import runDash
    from backend.src.server import runBackend

    stopEvent = Event()
    processBackend = Process(target=runBackend, daemon=True)
    processFrontend = Process(target=runDash, daemon=True)

    processBackend.start()
    processFrontend.start()

    def shutdown(signum=None, frame=None):
        print("Shutting down...")
        stopEvent.set()
        for p in (processBackend, processFrontend):
            if p.is_alive():
                p.join(timeout=5)
        for p in (processBackend, processFrontend):
            if p.is_alive():
                p.terminate()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, shutdown)
    try:
        signal.signal(signal.SIGTERM, shutdown)
    except (AttributeError, OSError):
        pass

    try:
        while True:
            # if any critical process dies, shut down all
            if not processBackend.is_alive() or not processFrontend.is_alive():
                shutdown()
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
