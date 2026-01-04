
import pybreaker
import time

def run():
    cb = pybreaker.CircuitBreaker(fail_max=2, reset_timeout=1)
    print(f"Initial State: {cb.current_state}")
    
    # 1. Fail
    try:
        with cb:
            print("Call 1")
            raise Exception("Boom")
    except Exception as e:
        print(f"Caught 1: {e}")
    
    print(f"cnt={cb.fail_counter} state={cb.current_state}")

    # 2. Fail
    try:
        with cb:
            print("Call 2")
            raise Exception("Boom")
    except Exception as e:
        print(f"Caught 2: {e}")
        
    print(f"cnt={cb.fail_counter} state={cb.current_state}")

    # 3. Should block
    try:
        with cb:
            print("Call 3 (Should not happen)")
    except pybreaker.CircuitBreakerError:
        print("✅ Blocked by Circuit Breaker")
    except Exception as e:
         print(f"❌ Failed to block: {e}")

    print(f"Final State: {cb.current_state}")

if __name__ == "__main__":
    run()
