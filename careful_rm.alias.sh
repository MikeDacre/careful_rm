#######################################################################
#              careful_rm aliases for sh, bash, and zsh               #
#######################################################################

# Get PATH to the python script
SOURCE="$0"
# resolve $SOURCE until the file is no longer a symlink
while [ -h "$SOURCE" ]; do
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  # if $SOURCE was a relative symlink, we need to resolve it relative to the
  # path where the symlink file was located
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
CAREFUL_RM_DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"

CAREFUL_RM="${CAREFUL_RM_DIR}/careful_rm.py"

# Only use our careful_rm if it exists, if not, try for a version on the
# PATH, failing that, fall back to rm -I
if [ ! -x "${CAREFUL_RM}" ]; then
    if hash careful_rm.py 2>/dev/null; then
        CAREFUL_RM="$(command -v careful_rm.py)"
    elif hash careful_rm 2>/dev/null; then
        CAREFUL_RM="$(command -v careful_rm)"
    else
        CAREFUL_RM=""
    fi
fi

# Set the alias
if [ -x "${CAREFUL_RM}" ]; then
    alias rm="${CAREFUL_RM}"
    alias careful_rm="${CAREFUL_RM}"
    alias current_trash="${CAREFUL_RM} --get-trash \${PWD}"
else
    echo "careful_rm.py is not available, using regular rm"
    alias rm="rm -I"
fi

export CAREFUL_RM CAREFUL_RM_DIR
