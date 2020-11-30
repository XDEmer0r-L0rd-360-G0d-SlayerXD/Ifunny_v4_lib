import ifunny_lib as ifl
import os
import ctypes
from pprint import pformat
import time


def goto_dir(dir: str):
    """
    Not part of the demonstration, this is just a helper func for me
    """
    if not os.path.exists(dir):
        os.mkdir(dir)
    os.chdir(dir)
    return


print("With no custom control yet I'm limiting the saves to single posts for now. It will save everything except for the pics from pic comments. Also max speed is about 50 items/s")
url = input("Post Url>")
start = time.time()
ifl.BASIC_TOKEN = "Basic MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTJfTXNPSUozOVEyODphNmMzN2ZmYjY2MWUzNzEzMDEwODQxNzI0ZTVmZTA4ZjUzNGZhMThm"

post = ifl.post_from_url(url)
print("Found post.")
goto_dir("Demo_data")
goto_dir(post.id)

post.comments.load()
print("Loaded Comments")
for a in post.comments:
    a.replies.load()
print("Loaded Replies")
post.repubs.load()
print("Loaded Repubs")
post.smiles.load()
print("Loaded Smiles")

ifl.dl_from_link(post.url, "Content." + post.url.split('.')[-1])
print("Saved Meme")

with open("Post Data.txt", "w") as f:
    f.write(pformat(post.cdata))
print("Saved Post Data")

with open("Repubs.txt", "w") as f:
    f.writelines([a.name + "\n" for a in post.repubs])
print("Saved Repubs")

with open("Smiles.txt", "w") as f:
    f.writelines([a.name + "\n" for a in post.smiles])
print("Saved Smiles")

with open("Comments.txt", "w", encoding='utf-16') as f:
    for a in post.comments:
        f.write(a.creator_name + ": " + a.text + '\n')
        f.writelines(["  " * b.depth + b.creator_name + ": " + b.text + '\n' for b in a.replies])
print("Saved Comments")

ctypes.windll.user32.MessageBoxW(0, f"Done in {time.time() - start}s", "Your title", 0)
