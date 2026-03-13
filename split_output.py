"""Read check_mappings_output.txt and write parts to numbered files."""
with open("check_mappings_output.txt", "r", encoding="utf-8") as f:
    content = f.read()

lines = content.split("\n")
chunk_size = 40
for i in range(0, len(lines), chunk_size):
    part_num = i // chunk_size + 1
    with open(f"check_part{part_num}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines[i:i+chunk_size]))
print(f"Total lines: {len(lines)}, wrote {(len(lines) + chunk_size - 1) // chunk_size} parts")
