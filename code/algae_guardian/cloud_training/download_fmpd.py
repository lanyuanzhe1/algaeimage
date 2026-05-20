"""Download FMPD dataset on the cloud server.

Tries wget first (more reliable for large files), falls back to curl.
"""
from cloud_ssh import CloudServer

URLS = [
    "https://zenodo.org/records/11126643/files/FMPD.zip",
    "https://zenodo.org/api/records/11126643/files/FMPD.zip/content",
]


def download():
    with CloudServer() as s:
        result = s.run("ls -lh /data/FMPD.zip 2>/dev/null || echo NOT_FOUND")
        print(f"FMPD.zip: {result.stdout}")

        expected = 2110657505

        if "NOT_FOUND" in result.stdout:
            print(f"Downloading FMPD.zip ({expected/1e9:.1f} GB) from Zenodo...")
            success = False
            for url in URLS:
                cmd = (
                    f'rm -f /data/FMPD.zip && '
                    f'wget -O /data/FMPD.zip "{url}" --timeout=30 2>&1 && '
                    f'ls -lh /data/FMPD.zip'
                )
                r = s.run(cmd, timeout=7200)
                # Check result
                size_r = s.run("stat -c%s /data/FMPD.zip 2>/dev/null || echo 0")
                actual = int(size_r.stdout.strip())
                print(f"  Attempt with URL {url[:50]}...: got {actual} bytes")
                if actual > expected * 0.9:
                    success = True
                    print(f"  Download successful!")
                    break
                else:
                    print(f"  Too small, trying next approach...")

            if not success:
                # Last try: direct HTTP with curl and retry
                print("  Trying final approach: curl with retry...")
                r = s.run(
                    f'rm -f /data/FMPD.zip && '
                    f'curl -L --retry 5 --retry-delay 10 '
                    f'-o /data/FMPD.zip '
                    f'"{URLS[0]}" 2>&1 && '
                    f'ls -lh /data/FMPD.zip',
                    timeout=7200,
                )
                print(r.stdout[-500:])
                print(r.stderr[-500:])
        else:
            # Check existing file
            size_r = s.run("stat -c%s /data/FMPD.zip 2>/dev/null || echo 0")
            actual = int(size_r.stdout.strip())
            if actual < expected * 0.9:
                print(f"File incomplete ({actual}/{expected}), re-downloading...")
                s.run("rm -f /data/FMPD.zip")
                r = s.run(
                    f'wget -O /data/FMPD.zip "{URLS[0]}" --timeout=30 2>&1',
                    timeout=7200,
                )
            else:
                print(f"FMPD.zip already complete ({actual} bytes)")

        r = s.run("df -h /data | tail -1")
        print(f"Disk: {r.stdout}")


if __name__ == "__main__":
    download()
