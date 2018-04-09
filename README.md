# AnimeImageSorter

This is a port of https://github.com/master117/AnimeImageSorter to Python along with some added features.

## Running

- Install python3.6 along with requirements in `requirements.txt`
- Run `main.py`

## Options

### Directory

Enter a directory to be used, or leave blank to use the current working directory.

### Sort by

- Series: Series/Copyright to which the image belongs.
- Character: Sort by depicted character.

### File Operations

- Move: Move files.
- Copy: Copy Files.

### MD5 Option

To save bandwidth this program initially uses MD5 hashes for looking up images.
Sankaku and other booru images are by default named after their MD5 hash when downloading.

- Hard: Calculate all hashes based on file content, lower success rate and speed but no false positives.
- Soft: Use filenames as hashes, when they match the hash pattern, faster and better success rate, but may have false
  positives. 
  This is faster as hashes don't need to be calculated, but may be wrong if a file has a name that is a valid hash, but
  doesn't belong to this file, which is extremely rare.

### Multiple Option

What happens if an image has multiple series/character tags.

- Copies: Create a copy of the file per tag. Best sort, but requires the most space.
- Mixed Folders: Creates folders with combined tags as name.
- First: Uses the first tag.
- Skip: Skips these files from sorting.

### Reverse Image Search

Enables Reverse Image Search, only if booru/hash search fails.

You will need to have sauceNaoApi.txt and imgurApiKey.txt (or noLifeKey.txt) in the `keys` folder, filled with your own
matching keys.
Using SauceNao is very slow; every used image is uploaded.

- Yes: Enables Reverse Image Search on fail.
- No: Disables Reverse Image Search on fail.

### Image upload host

Both support for Imgur and NoLife are provided. Chances are, you don't have a NoLife account, so no need to worry about
that. On the off-chance you do, you will need to update your endpoint in `services/no_life.py`.
