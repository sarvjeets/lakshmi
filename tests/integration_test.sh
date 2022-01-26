#!/bin/bash

# There are a number of unit-tests for lakshmi. This files add some
# integration tests for lak to make sure all commands are running without
# errors. It doesn't check for correctness -- that is left to unittest.
# For example, it can catch issues with packaging files incorrectly.

# Tests if command works
testcmd () {
    GREEN='\033[0;32m'
    RED='\033[0;31m'
    NC='\033[0m'

    echo -n "Running \"$1\" : "
    if $1 > /dev/null ; then
        echo -e "${GREEN}Succeeded${NC}"
     else
        echo -e "${RED}Failed${NC}"
        exit 1
     fi
}

# Constants
TMP_DIR='/tmp/lakshmi_integration_test'

# Setup from arguments
if [ "$#" -eq 1 ]; then
    CACHE=$1
elif [ "$#" -eq 0 ]; then
    CACHE='~/.lakshmicache'
else
    echo Usage: $0 '<path_for_cache_dir>'; exit 2
fi

cleanup () {
    test -d $TMP_DIR && rm -r $TMP_DIR
}
trap cleanup EXIT

# Make temp directory
mkdir -p $TMP_DIR

# Create new lakrc for testing
cat << HERE > $TMP_DIR/lakrc
portfolio: $TMP_DIR/portfolio.yaml
cache: $CACHE
performance: $TMP_DIR/performance.yaml
HERE

export LAK_CONFIG=$TMP_DIR/lakrc

# Default values for files is OK, just touch the file to fool lak into
# believing that the user editted the file.
export EDITOR=touch

echo "Testing binary: `command -v lak`"
testcmd "lak init"
testcmd "lak add account"
testcmd "lak add asset -t account -p ManualAsset"
testcmd "lak add asset -t account -p TickerAsset"
testcmd "lak add asset -t account -p VanguardFund"
testcmd "lak add asset -t account -p IBonds"
testcmd "lak add asset -t account -p EEBonds"
testcmd "lak add checkpoint -e"
testcmd "lak list al"
testcmd "lak list aa"
testcmd "lak list aa --no-compact"
testcmd "lak list aa -c US,Intl,Bonds"
testcmd "lak list assets -s -q"
testcmd "lak list total"
testcmd "lak list whatifs"
testcmd "lak list lots"
testcmd "lak list checkpoints"
testcmd "lak list performance"
testcmd "lak info account -t account"
testcmd "lak info asset -a ITOT"
testcmd "lak info asset -a EE"
testcmd "lak info performance"
testcmd "lak whatif account -t account 10"
testcmd "lak whatif account -t account -10"
testcmd "lak whatif asset -a ITOT 10"
testcmd "lak whatif asset -a ITOT -10"
testcmd "lak analyze tlh"
testcmd "lak analyze rebalance"
testcmd "lak edit account -t account"
testcmd "lak edit asset -a ITOT"
testcmd "lak edit checkpoint --date `date +%Y/%m/%d`"
testcmd "lak delete asset -a ITOT --yes"
testcmd "lak delete account -t account --yes"
testcmd "lak delete checkpoint --yes --date `date +%Y/%m/%d`"
