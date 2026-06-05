import subprocess
import tempfile


def synthesize(text: str, voice: str = "default") -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        output_path = f.name

    subprocess.run(
        ["piper", "--model", voice, "--output-file", output_path],
        input=text.encode("utf-8"),
        check=True,
    )

    return output_path
