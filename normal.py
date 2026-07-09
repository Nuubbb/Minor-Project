import subprocess, os

DEST = "extra_normal/NonViolence"     # labelled non-violent (0) by the training script
os.makedirs(DEST, exist_ok=True)

# LOTS of close-contact non-violent clips -> teach the model "close contact != fight"
queries = [
    "two people hugging each other",
    "friends hugging reunion emotional",
    "people greeting with hug",
    "family members hugging",
    "couple hugging goodbye airport",
    "group of friends hugging",
    "people patting each other back friendly",
    "two people talking close conversation",
    "friends laughing talking together",
    "people shaking hands meeting",
    "colleagues handshake greeting office",
    "people high five celebration",
    "friends embracing happy",
    "people dancing together party",
    "team celebrating group hug",
]

for i, q in enumerate(queries):
    # up to 5 short clips per query -> ~75 clips total
    subprocess.run(["yt-dlp", "-f", "mp4", "--max-filesize", "40M",
                    "-o", f"{DEST}/q{i}_%(autonumber)s.%(ext)s",
                    f"ytsearch5:{q}"])

vids = [f for f in os.listdir(DEST) if f.lower().endswith((".mp4", ".avi", ".mkv", ".webm"))]
print(f"\n>>> downloaded {len(vids)} non-violent close-contact clips <<<")