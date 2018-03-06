#######################################################################
#                         careful_rm for ZSH                          #
#                       Has some extra goodies                        #
#######################################################################

# Get the alias
OURDIR="$(dirname $0:A)"
source "${OURDIR}/careful_rm.alias.sh"

# Make a trash aliase that changes with directory
chpwd_trash() {
    if [ -x "${CAREFUL_RM}" ]; then
        TRASH=$(python ${CAREFUL_RM} --get-trash)
        if [[ "$OSTYPE" == "linux-gnu" ]]; then
            TRASH="${TRASH}/files"
        fi
        hash -d trash="${TRASH}"
    fi
}
chpwd_functions=( ${chpwd_functions} chpwd_trash )
chpwd_trash
alias trsh="cd \${TRASH}"
