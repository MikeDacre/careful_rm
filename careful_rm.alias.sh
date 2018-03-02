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

alias rm="${CAREFUL_RM}"
