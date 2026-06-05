import subprocess
import tempfile


def synthesize(text: str, voice: str = "default", model_name: str = "piper") -> str:
    output_path = tempfile.mktemp(suffix=".wav")

    subprocess.run(
        ["piper", "--model", voice, "--output-file", output_path],
        input=text.encode("utf-8"),
        check=True,
    )

    return output_path
