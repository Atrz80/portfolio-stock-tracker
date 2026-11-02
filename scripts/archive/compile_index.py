import os

from make_index_file import html_part1
from make_part2 import html_part2
from make_part3 import html_part3

full_html = html_part1 + html_part2 + html_part3

with open("index.html", "w", encoding="utf-8") as f:
    f.write(full_html)

print("✅ index.html compiled and generated successfully.")
