"""Remove every question marked "verbal": false (math, logic, data) and the images only they use.

    python3 tools/drop_nonverbal.py          # show what would be removed
    python3 tools/drop_nonverbal.py --apply  # remove it
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
apply = "--apply" in sys.argv

kept_images, dropped_images, total = set(), set(), 0
for name in json.load(open(os.path.join(DATA, "index.json"))):
    path = os.path.join(DATA, name + ".json")
    qs = json.load(open(path))
    keep = [q for q in qs if q.get("verbal", True)]
    drop = [q for q in qs if not q.get("verbal", True)]
    for q, bucket in [(q, kept_images) for q in keep] + [(q, dropped_images) for q in drop]:
        bucket.update([q["image"]] if isinstance(q.get("image"), str) else q.get("image", []))
    if drop:
        print(f"{name}: removing {len(drop)} of {len(qs)} questions")
        total += len(drop)
        if apply:
            with open(path, "w") as f:
                json.dump(keep, f, ensure_ascii=False, separators=(",", ":"))

orphans = sorted(dropped_images - kept_images)
print(f"{total} questions, {len(orphans)} images")
if apply:
    for rel in orphans:
        if os.path.exists(os.path.join(ROOT, rel)):
            os.remove(os.path.join(ROOT, rel))
    print("done")
else:
    print("dry run; add --apply to remove them")
