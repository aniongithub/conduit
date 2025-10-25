__all__ = ("get_git_version")

from subprocess import Popen, PIPE

def call_git_describe(abbrev):
    try:
        p = Popen(['git', 'describe', '--abbrev=%d' % abbrev],
                  stdout=PIPE, stderr=PIPE)
        p.stderr.close()
        line = p.stdout.readlines()[0]
        return line.strip()

    except:
        return None

def is_dirty():
    try:
        p = Popen(["git", "diff-index", "--name-only", "HEAD"],
                  stdout=PIPE, stderr=PIPE)
        p.stderr.close()
        lines = p.stdout.readlines()
        return len(lines) > 0
    except:
        return False

def get_git_version(abbrev=7):
    # First try to get the current version using “git describe”.
    version = call_git_describe(abbrev)

    # If that doesn't work, dub it "0.0.0"

    if version is None:
        version = "0.0.0"
    else:
        version = version.decode('utf-8')

    # if is_dirty():
    #     version += "-dirty"

    return version

if __name__ == "__main__":
    print(get_git_version())