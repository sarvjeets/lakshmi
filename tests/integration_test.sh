#!/bin/bash

# There are a number of unit-tests for lakshmi. This files add some
# integration tests for lak to make sure all commands are running without
# errors. It doesn't check for correctness -- that is left to unittest.
# What it does check is if commands are executing without errors. For example,
# it can catch issues with packaging files incorrectly.

export EDITOR=touch

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
BIN='lak'
TMP_DIR='/tmp/lakshmi_integration_test'

cleanup () {
    test -f $TMP_DIR/lakrc && mv $TMP_DIR/lakrc ~/.lakrc
    test -d $TMP_DIR && rm -r $TMP_DIR
}
trap cleanup EXIT

# Setup from arguments
if [ "$#" -eq 1 ]; then
    CACHE=$1
elif [ "$#" -eq 0 ]; then
    CACHE='~/.lakshmicache'
else
    echo Usage: $0 '<path_to_lak>'; exit 2
fi

# Make temp directory and backup lakrc
mkdir -p $TMP_DIR
if [ -s ~/.lakrc ]; then
    cp ~/.lakrc $TMP_DIR/lakrc
fi

# Create new lakrc for testing
cat << HERE > ~/.lakrc
portfolio: $TMP_DIR/portfolio.yaml
cache: $CACHE
HERE

echo "Testing binary: `which lak`"
testcmd "lak init"
testcmd "lak add account"
testcmd "lak add asset -t account -p ManualAsset"
testcmd "lak add asset -t account -p TickerAsset"
testcmd "lak add asset -t account -p VanguardFund"
testcmd "lak add asset -t account -p IBonds"
testcmd "lak add asset -t account -p EEBonds"
testcmd "lak list al"
testcmd "lak list aa"
testcmd "lak list aa --no-compact"
testcmd "lak list aa -c US,Intl,Bonds"
testcmd "lak list assets -s -q"
testcmd "lak list total"
testcmd "lak list whatifs"
testcmd "lak info account -t account"
testcmd "lak info asset -a ITOT"
testcmd "lak info asset -a EE"
testcmd "lak whatif account -t account 10"
testcmd "lak whatif account -t account -10"
testcmd "lak whatif asset -a ITOT 10"
testcmd "lak whatif asset -a ITOT -10"
testcmd "lak analyze tlh"
testcmd "lak analyze rebalance"
testcmd "lak edit account -t account"
testcmd "lak edit asset -a ITOT"
testcmd "lak delete asset -a ITOT --yes"
testcmd "lak delete account -t account --yes"

