"""Run the six-material studio checks serially; the bridge has one request slot."""
from capture_batch7 import main as capture
from verify_batch7_reload import main as reload_proof
from verify_batch7_controls import main as controls


if __name__ == '__main__':
    capture()
    reload_proof()
    controls()
