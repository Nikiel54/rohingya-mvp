"""Quick manual test for POST /api/evaluate.

Usage:
    backend/venv/Scripts/python.exe scripts/try_evaluate.py <audio_file> <turnId>
    backend/venv/Scripts/python.exe scripts/try_evaluate.py --text "okay i will" t2
"""

import argparse
import json

import requests


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("audio_path", nargs="?", help="Path to an audio file to post")
    parser.add_argument("turn_id", help="turnId, e.g. t2 or repeat_request")
    parser.add_argument("--text", help="Send as debugTranscript instead of a real recording (requires DEBUG=1 on the server)")
    parser.add_argument("--url", default="http://localhost:8000/api/evaluate")
    args = parser.parse_args()

    data = {"turnId": args.turn_id}
    files = None

    if args.text is not None:
        data["debugTranscript"] = args.text
        # The endpoint still requires a multipart `audio` field; send an empty placeholder.
        files = {"audio": ("debug.txt", b"", "application/octet-stream")}
    else:
        if not args.audio_path:
            parser.error("audio_path is required unless --text is given")
        with open(args.audio_path, "rb") as f:
            audio_bytes = f.read()
        files = {"audio": (args.audio_path, audio_bytes, "audio/mpeg")}

    resp = requests.post(args.url, data=data, files=files)
    print(f"status: {resp.status_code}")
    try:
        print(json.dumps(resp.json(), indent=2))
    except ValueError:
        print(resp.text)


if __name__ == "__main__":
    main()
