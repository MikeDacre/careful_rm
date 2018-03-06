#######################################################################
#              careful_rm aliases for sh, bash, and zsh               #
#######################################################################

# Get PATH to the python script
SOURCE="$0"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"

CAREFUL_RM="${DIR}/careful_rm.py"

# Only use our careful_rm if it exists, if not, try for a version on the
# PATH, failing that, fall back to rm -I
if [ -x "${CAREFUL_RM}" ]; then
    alias rm="${CAREFUL_RM}"
    alias careful_rm="${CAREFUL_RM}"
elif hash careful_rm.py 2>/dev/null; then
    alias rm="$(command -v careful_rm.py)"
elif hash careful_rm 2>/dev/null; then
    alias rm="$(command -v careful_rm)"
else
    alias rm="rm -I"
fi
