#!/usr/bin/env python3

import subprocess
from pathlib import Path
from typing import List

from font_fredoka_one import FredokaOne
from inky import InkyPHAT_SSD1608
from inky import auto as auto_inky
from PIL import Image, ImageDraw, ImageFont

CELSIUS = "°C"
USAGE_BAR_HEIGHT = 34
USAGE_BAR_POSITION = (59, 74)
PERSISTENCE_PATH = Path(__file__).parent.joinpath("persist.txt")


def get_base_image() -> Image.Image:
    script_dir = Path(__file__).parent
    base_image_path = script_dir.joinpath("Inky.png")
    if not base_image_path.exists():
        raise IOError("Base image file not found!")
    return Image.open(base_image_path)


def get_num_ssh_connections() -> int:
    result = subprocess.run(
        ["bash", "-c", "ss -nat | rg '^ESTAB.*:22\\b' | wc -l"], stdout=subprocess.PIPE
    )
    if result.returncode != 0:
        print(
            "Failed to get number of SSH connection(s): process exited with %d"
            % result.returncode
        )
        return 0
    return int(result.stdout.decode("utf-8"))


def get_temperature() -> int:
    result = subprocess.run(
        ["bash", "-c", "vcgencmd measure_temp | sed 's|[^0-9\.]||g'"],
        stdout=subprocess.PIPE,
    )
    if result.returncode != 0:
        print("Failed to get temperature: process exited with %d" % result.returncode)
        return 0
    temp = float(result.stdout.decode("utf-8").strip())
    return int(temp)


def get_otg_usage() -> int:
    result = subprocess.run(
        ["bash", "-c", "df --output=pcent /otg | tail -n1"],
        stdout=subprocess.PIPE,
    )
    if result.returncode != 0:
        print("Failed to get OTG usage: process exited with %d" % result.returncode)
        return 0
    percent = int(result.stdout.decode("utf-8").strip().rstrip("%"))
    return int(percent)


def restore() -> List[str]:
    try:
        with open(PERSISTENCE_PATH, "r") as f:
            return [l.strip() for l in f.readlines()]
    except Exception as _:
        return []


def persist(num_ssh: int, temperature: int, otg_usage: int):
    try:
        with open(PERSISTENCE_PATH, "w") as f:
            f.writelines(str(l) + "\n" for l in [num_ssh, temperature, otg_usage])
    except Exception as e:
        print("Failed to persist: %s", e)


def needs_refresh(num_ssh: int, temperature: int, otg_usage: int) -> bool:
    restored = restore()
    if len(restored) == 0:
        return True
    current = [str(l) for l in [num_ssh, temperature, otg_usage]]
    return current != restored


def main():
    num_ssh = get_num_ssh_connections()
    temperature = get_temperature()
    otg_usage = get_otg_usage()
    if not needs_refresh(num_ssh, temperature, otg_usage):
        print("No need to refresh")
        return

    img = get_base_image()
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FredokaOne, 30)

    inky = auto_inky()  # type: InkyPHAT_SSD1608
    inky.set_border(inky.BLACK)

    draw.text((63, 15), str(num_ssh), inky.BLACK, font)

    draw.text((166, 15), str(temperature) + CELSIUS, inky.BLACK, font)

    colour = inky.BLACK
    x, y = USAGE_BAR_POSITION
    for i in range(otg_usage):
        if i % 5 == 0:
            colour = inky.YELLOW if colour == inky.BLACK else inky.BLACK
        if i == otg_usage - 1:
            colour = inky.BLACK
        draw.line([x + i, y, x + i, y + USAGE_BAR_HEIGHT - 1], colour, 1)
    draw.text((166, 72), "%d%%" % otg_usage, inky.BLACK, font)

    inky.set_image(img)
    inky.show()

    persist(num_ssh, temperature, otg_usage)


if __name__ == "__main__":
    main()
