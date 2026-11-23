import sys

from media_delivery import generate_and_deliver


if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) or "A hand-drawn map of a quiet mountain lake"
    print(generate_and_deliver(prompt))

